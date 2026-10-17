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


@pytest.mark.django_db(transaction=True)  # SQLite's online backup can't run inside an open transaction
class TestOffsiteCopy:
    def test_files_are_uploaded_when_a_bucket_is_configured(self, target, settings):
        settings.BACKUP_S3_BUCKET = "respaldos"
        settings.BACKUP_S3_ENDPOINT_URL = "https://minio.example"
        settings.BACKUP_S3_PREFIX = "sg-church/"
        client = mock.Mock()
        with mock.patch("boto3.client", return_value=client) as make_client:
            result = backup.create_backup()

        assert result["upload_error"] is None
        assert make_client.call_args.kwargs["endpoint_url"] == "https://minio.example"
        bucket, key = client.upload_file.call_args.args[1:]
        assert bucket == "respaldos" and key == f"sg-church/{result['files'][0].name}"

    def test_a_failed_upload_keeps_the_local_backup_and_reports_it(self, target, settings):
        settings.BACKUP_S3_BUCKET = "respaldos"
        client = mock.Mock()
        client.upload_file.side_effect = RuntimeError("bucket unreachable")
        with mock.patch("boto3.client", return_value=client):
            result = backup.create_backup()

        assert "bucket unreachable" in result["upload_error"]
        assert result["files"][0].exists()

    def test_nothing_is_uploaded_without_a_bucket(self, target):
        with mock.patch("boto3.client") as make_client:
            backup.create_backup()
        make_client.assert_not_called()


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
