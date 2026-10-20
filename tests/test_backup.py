"""
Backups: the database and the uploaded files are dumped, old ones pruned,
failures leave nothing half-written, and the nightly job is scheduled.
"""

import gzip
import io
import sqlite3
import tarfile
from unittest import mock

import pytest
from django.core.management import call_command

from core import backup
from members.models import Member


@pytest.fixture
def target(tmp_path, settings):
    settings.BACKUP_DIR = str(tmp_path / "backups")
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.BACKUP_S3_BUCKET = ""
    return tmp_path / "backups"


@pytest.fixture
def stamps(monkeypatch):
    """Distinct, increasing timestamps so several backups can coexist."""
    counter = iter(range(1, 100))
    monkeypatch.setattr(backup, "_stamp", lambda: f"20260101-0000{next(counter):02d}")


def _restore_sqlite(path):
    raw = gzip.decompress(path.read_bytes())
    scratch = path.parent / "restored.sqlite3"
    scratch.write_bytes(raw)
    return sqlite3.connect(scratch)


@pytest.mark.django_db(transaction=True)  # SQLite's online backup can't run inside an open transaction
class TestCreateBackup:
    def test_database_dump_is_a_restorable_copy(self, target, admin_user):
        Member.objects.create(tenant=admin_user.tenant, first_name="Respaldada", last_name="Ana")

        result = backup.create_backup()

        (db_file,) = result["files"]
        assert db_file.parent == target and db_file.name.startswith("db-")
        restored = _restore_sqlite(db_file)
        names = [row[0] for row in restored.execute("SELECT first_name FROM members")]
        assert "Respaldada" in names

    def test_uploaded_files_are_archived_only_when_there_are_any(self, target, tmp_path, settings):
        assert len(backup.create_backup()["files"]) == 1  # no media yet

        media = tmp_path / "media" / "members"
        media.mkdir(parents=True)
        (media / "foto.txt").write_text("hola")
        result = backup.create_backup()

        archive = next(f for f in result["files"] if f.name.startswith("media-"))
        with tarfile.open(archive) as tar:
            assert "media/members/foto.txt" in tar.getnames()

    def test_only_the_newest_are_kept(self, target, stamps, tmp_path):
        (tmp_path / "media").mkdir()
        (tmp_path / "media" / "a.txt").write_text("x")
        for _ in range(5):
            backup.create_backup(keep=2)

        names = sorted(p.name for p in target.iterdir())
        assert len(names) == 4  # 2 db + 2 media
        assert [n for n in names if n.startswith("db-")][-1].startswith("db-20260101-000005")
        assert not any("000001" in n or "000002" in n or "000003" in n for n in names)

    def test_failed_dump_leaves_no_partial_file(self, target, monkeypatch):
        def broken(path):
            path.write_bytes(b"half")
            raise RuntimeError("disk full")

        monkeypatch.setattr(backup, "_dump_sqlite", broken)

        with pytest.raises(RuntimeError):
            backup.create_backup()

        assert list(target.iterdir()) == []

    def test_postgres_falls_back_to_json_when_pg_dump_fails(self, target, monkeypatch):
        fake_connection = mock.Mock(vendor="postgresql")
        monkeypatch.setattr(backup, "connection", fake_connection)
        monkeypatch.setattr(backup.shutil, "which", lambda name: "/usr/bin/pg_dump")
        monkeypatch.setattr(
            backup, "_dump_postgres", mock.Mock(side_effect=backup.BackupError("version mismatch"))
        )
        monkeypatch.setattr(
            backup, "_dump_json", lambda path: path.write_bytes(gzip.compress(b"[]"))
        )
        target.mkdir(parents=True)

        path = backup._dump_database(target, "20260101-000000")

        assert path.name == "db-20260101-000000.json.gz"
        assert [p.name for p in target.iterdir()] == [path.name]

    def test_json_dump_is_valid_fixture_data(self, tmp_path, admin_user):
        path = tmp_path / "dump.json.gz"
        backup._dump_json(path)
        import json

        data = json.loads(gzip.decompress(path.read_bytes()))
        assert any(row["model"] == "members.user" for row in data)


class FakeS3:
    """Just enough of a boto3 S3 client, backed by a dict."""

    def __init__(self):
        self.objects = {}  # key -> bytes
        self.fail_on = {}  # method name -> exception

    def _maybe_fail(self, name):
        if name in self.fail_on:
            raise self.fail_on[name]

    def head_bucket(self, Bucket):
        self._maybe_fail("head_bucket")

    def upload_file(self, path, bucket, key):
        self._maybe_fail("upload_file")
        with open(path, "rb") as handle:
            self.objects[key] = handle.read()

    def put_object(self, Bucket, Key, Body):
        self._maybe_fail("put_object")
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        import io

        return {"Body": io.BytesIO(self.objects[Key])}

    def delete_object(self, Bucket, Key):
        self._maybe_fail("delete_object")
        self.objects.pop(Key, None)

    def get_paginator(self, name):
        import datetime

        outer = self

        class Paginator:
            def paginate(self, Bucket, Prefix=""):
                yield {
                    "Contents": [
                        {"Key": k, "Size": len(v), "LastModified": datetime.datetime(2026, 1, 1)}
                        for k, v in sorted(outer.objects.items())
                        if k.startswith(Prefix)
                    ]
                }

        return Paginator()


@pytest.fixture
def bucket(settings):
    settings.BACKUP_S3_BUCKET = "respaldos"
    settings.BACKUP_S3_ENDPOINT_URL = "https://minio.example"
    settings.BACKUP_S3_PREFIX = "sg-church/"
    settings.BACKUP_REMOTE_KEEP = 2
    fake = FakeS3()
    with mock.patch("boto3.client", return_value=fake) as make_client:
        fake.make_client = make_client
        yield fake


@pytest.mark.django_db(transaction=True)  # SQLite's online backup can't run inside an open transaction
class TestOffsiteCopy:
    def test_files_are_uploaded_when_a_bucket_is_configured(self, target, bucket):
        result = backup.create_backup()

        assert result["upload_error"] is None
        assert bucket.make_client.call_args.kwargs["endpoint_url"] == "https://minio.example"
        assert list(bucket.objects) == [f"sg-church/{result['files'][0].name}"]

    def test_a_failed_upload_keeps_the_local_backup_and_reports_it(self, target, bucket):
        bucket.fail_on["upload_file"] = RuntimeError("bucket unreachable")
        result = backup.create_backup()

        assert "bucket unreachable" in result["upload_error"]
        assert result["files"][0].exists()

    def test_nothing_is_uploaded_without_a_bucket(self, target):
        with mock.patch("boto3.client") as make_client:
            backup.create_backup()
        make_client.assert_not_called()

    def test_old_copies_in_the_bucket_are_trimmed(self, target, stamps, bucket):
        for _ in range(4):
            backup.create_backup()
        names = sorted(key.rsplit("/", 1)[-1] for key in bucket.objects)
        assert len(names) == 2 and names[-1].startswith("db-20260101-000004")

    def test_trimming_leaves_other_things_in_the_bucket_alone(self, target, stamps, bucket):
        bucket.objects["sg-church/notas.txt"] = b"x"
        bucket.objects["otro/db-20200101-000000.sql.gz"] = b"x"
        for _ in range(4):
            backup.create_backup()
        assert "sg-church/notas.txt" in bucket.objects and "otro/db-20200101-000000.sql.gz" in bucket.objects

    def test_a_trimming_failure_is_reported_but_the_backup_is_there(self, target, stamps, bucket):
        for _ in range(3):
            backup.create_backup()
        bucket.fail_on["delete_object"] = RuntimeError("no delete permission")
        result = backup.create_backup()
        assert "no delete permission" in result["upload_error"]
        assert len(bucket.objects) >= 3


class TestCheckRemote:
    def test_a_working_bucket_passes_every_step(self, bucket):
        steps = backup.check_remote()
        assert any("write" in s for s in steps) and any("read" in s for s in steps)
        assert any("delete" in s for s in steps)
        assert not [k for k in bucket.objects if ".check-" in k]  # the probe is removed

    def test_no_bucket_says_so(self, settings):
        settings.BACKUP_S3_BUCKET = ""
        with pytest.raises(backup.BackupError, match="BACKUP_S3_BUCKET"):
            backup.check_remote()

    @pytest.mark.parametrize("step", ["head_bucket", "put_object", "delete_object"])
    def test_each_failure_names_what_worked_and_what_broke(self, bucket, step):
        bucket.fail_on[step] = RuntimeError("AccessDenied")
        with pytest.raises(backup.BackupError, match="AccessDenied"):
            backup.check_remote()

    def test_command_reports_ok_lines(self, bucket, capsys):
        call_command("backup_data", "--check-remote")
        assert "OK  Can write" in capsys.readouterr().out

    def test_command_fails_with_the_reason(self, bucket):
        from django.core.management.base import CommandError

        bucket.fail_on["put_object"] = RuntimeError("AccessDenied")
        with pytest.raises(CommandError, match="AccessDenied"):
            call_command("backup_data", "--check-remote")

    def test_list_remote_shows_the_stored_backups(self, bucket, capsys):
        bucket.objects["sg-church/db-20260101-000001.sql.gz"] = b"abc"
        call_command("backup_data", "--list-remote")
        out = capsys.readouterr().out
        assert "db-20260101-000001.sql.gz" in out and "1 file(s) off-site" in out


class TestAlerts:
    def test_a_failed_nightly_backup_emails_the_person_in_charge(self, settings, mailoutbox):
        from core import tasks

        settings.BACKUP_ALERT_EMAIL = "yo@iglesia.org, otro@iglesia.org"
        with mock.patch("core.backup.create_backup", side_effect=RuntimeError("disk full")):
            with pytest.raises(RuntimeError):
                tasks.run_backup()
        assert mailoutbox[0].to == ["yo@iglesia.org", "otro@iglesia.org"]
        assert "FALLÓ" in mailoutbox[0].subject and "disk full" in mailoutbox[0].body

    def test_a_failed_off_site_copy_also_emails(self, settings, mailoutbox):
        from core import tasks

        settings.BACKUP_ALERT_EMAIL = "yo@iglesia.org"
        result = {"files": [], "pruned": [], "upload_error": "bucket unreachable"}
        with mock.patch("core.backup.create_backup", return_value=result):
            tasks.run_backup()
        assert "fuera del servidor" in mailoutbox[0].subject and "bucket unreachable" in mailoutbox[0].body

    def test_nobody_is_emailed_when_no_address_is_set(self, settings, mailoutbox):
        from core import tasks

        settings.BACKUP_ALERT_EMAIL = ""
        with mock.patch("core.backup.create_backup", side_effect=RuntimeError("x")):
            with pytest.raises(RuntimeError):
                tasks.run_backup()
        assert mailoutbox == []

    def test_a_good_backup_sends_nothing(self, settings, mailoutbox):
        from core import tasks

        settings.BACKUP_ALERT_EMAIL = "yo@iglesia.org"
        with mock.patch("core.backup.create_backup", return_value={"files": [], "pruned": [], "upload_error": None}):
            tasks.run_backup()
        assert mailoutbox == []


@pytest.mark.django_db(transaction=True)  # SQLite's online backup can't run inside an open transaction
class TestCommandAndSchedule:
    def test_command_writes_the_files_and_says_so(self, tmp_path):
        out = io.StringIO()
        call_command("backup_data", dir=str(tmp_path), keep=3, no_upload=True, stdout=out)

        assert "Created" in out.getvalue()
        assert any(p.name.startswith("db-") for p in tmp_path.iterdir())

    def test_command_fails_loudly_when_the_off_site_copy_fails(self, target, settings):
        from django.core.management.base import CommandError

        settings.BACKUP_S3_BUCKET = "respaldos"
        client = mock.Mock()
        client.upload_file.side_effect = RuntimeError("nope")
        with mock.patch("boto3.client", return_value=client):
            with pytest.raises(CommandError, match="off-site copy failed"):
                call_command("backup_data", stdout=io.StringIO())
        assert any(target.iterdir())  # the local copy is there regardless

    def test_the_celery_task_runs_a_backup(self, target):
        from core.tasks import run_backup

        run_backup()

        assert any(p.name.startswith("db-") for p in target.iterdir())

    def test_a_nightly_backup_is_scheduled_and_its_task_is_registered(self, settings):
        from sg_church.celery import app

        entry = settings.CELERY_BEAT_SCHEDULE["nightly-backup"]
        assert entry["task"] == "core.tasks.run_backup"
        app.loader.import_default_modules()
        assert entry["task"] in app.tasks


def test_dump_drops_sql_an_older_server_cannot_restore():
    """PostgreSQL 17's pg_dump writes `SET transaction_timeout`, which a 16
    server rejects when the dump is restored."""
    source = io.BytesIO(
        b"SET statement_timeout = 0;\nSET transaction_timeout = 0;\nCREATE TABLE t ();\n"
    )
    out = io.BytesIO()

    backup._copy_portable(source, out)

    assert out.getvalue() == b"SET statement_timeout = 0;\nCREATE TABLE t ();\n"
