"""
Backups of the database and the uploaded files.

A backup is only worth something if it is recent, restorable and not stored
solely on the machine that may die, so this module:

- dumps the database with the right tool for the engine (``pg_dump`` for
  PostgreSQL, SQLite's online backup API, or ``dumpdata`` as a fallback),
- archives the uploaded media,
- prunes old files (``keep`` newest of each kind),
- optionally copies the new files to any S3-compatible bucket (MinIO, AWS...).

Used by ``manage.py backup_data`` and by the daily Celery beat task.
"""

import gzip
import logging
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)

KINDS = ("db", "media")


class BackupError(Exception):
    """The database dump failed; nothing usable was produced."""


def _stamp():
    return timezone.now().strftime("%Y%m%d-%H%M%S")


# SQL a newer pg_dump adds that an older server cannot restore: the client in the
# image can be newer than the database it dumps (PostgreSQL 17 vs a 16 server).
_UNPORTABLE_PREFIXES = (b"SET transaction_timeout",)


def _copy_portable(source, out):
    for line in source:
        if not line.startswith(_UNPORTABLE_PREFIXES):
            out.write(line)


def _dump_postgres(target):
    db = settings.DATABASES["default"]
    command = [
        "pg_dump", "--no-owner", "--clean", "--if-exists",
        "-h", db.get("HOST") or "localhost",
        "-p", str(db.get("PORT") or 5432),
        "-U", db.get("USER") or "",
        db["NAME"],
    ]
    env = {**os.environ, "PGPASSWORD": db.get("PASSWORD") or ""}
    with gzip.open(target, "wb") as out:
        process = subprocess.Popen(
            command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        _copy_portable(process.stdout, out)
        error = process.stderr.read().decode(errors="replace")
        if process.wait() != 0:
            raise BackupError(f"pg_dump failed: {error.strip()}")


def _dump_sqlite(target):
    connection.ensure_connection()
    with tempfile.TemporaryDirectory() as scratch:
        snapshot = Path(scratch) / "snapshot.sqlite3"
        copy = sqlite3.connect(snapshot)
        try:
            connection.connection.backup(copy)  # consistent even while in use
        finally:
            copy.close()
        with open(snapshot, "rb") as source, gzip.open(target, "wb") as out:
            shutil.copyfileobj(source, out)


def _dump_json(target):
    with gzip.open(target, "wt", encoding="utf-8") as out:
        call_command(
            "dumpdata", "--natural-foreign", "--natural-primary",
            "--exclude=contenttypes", "--exclude=auth.permission",
            "--exclude=sessions", stdout=out,
        )


def _dump_database(directory, stamp):
    vendor = connection.vendor
    if vendor == "postgresql" and shutil.which("pg_dump"):
        target, dump = directory / f"db-{stamp}.sql.gz", _dump_postgres
    elif vendor == "sqlite":
        target, dump = directory / f"db-{stamp}.sqlite3.gz", _dump_sqlite
    else:
        target, dump = directory / f"db-{stamp}.json.gz", _dump_json
    try:
        dump(target)
    except Exception:
        target.unlink(missing_ok=True)  # never leave a half-written "backup"
        if dump is not _dump_postgres:
            raise
        # e.g. a pg_dump older than the server: a portable dump beats none.
        logger.warning("pg_dump failed; falling back to a JSON dump", exc_info=True)
        target = directory / f"db-{stamp}.json.gz"
        try:
            _dump_json(target)
        except Exception:
            target.unlink(missing_ok=True)
            raise
    return target


def _archive_media(directory, stamp):
    root = Path(settings.MEDIA_ROOT)
    if not root.is_dir() or not any(root.rglob("*")):
        return None
    target = directory / f"media-{stamp}.tar.gz"
    with tarfile.open(target, "w:gz") as archive:
        archive.add(root, arcname="media")
    return target


def _prune(directory, keep):
    removed = []
    for kind in KINDS:
        files = sorted(directory.glob(f"{kind}-*"), reverse=True)
        for old in files[keep:]:
            old.unlink(missing_ok=True)
            removed.append(old)
    return removed


def _remote():
    """(boto3 client, bucket, key prefix), or None when no bucket is configured."""
    bucket = getattr(settings, "BACKUP_S3_BUCKET", "")
    if not bucket:
        return None
    import boto3
    from botocore.config import Config

    # Recent boto3 adds integrity checksums that several S3-compatible services
    # (Backblaze B2, MinIO, older R2) reject; ask for them only when required.
    try:
        config = Config(request_checksum_calculation="when_required", response_checksum_validation="when_required")
    except TypeError:  # an older botocore does not have the option (nor the problem)
        config = None
    client = boto3.client(
        "s3",
        endpoint_url=settings.BACKUP_S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        region_name=settings.AWS_S3_REGION_NAME or None,
        config=config,
    )
    return client, bucket, settings.BACKUP_S3_PREFIX.strip("/")


def _key(prefix, name):
    return f"{prefix}/{name}" if prefix else name


def _remote_backups(client, bucket, prefix):
    """[(key, size, last_modified)] of the backup files in the bucket, newest first."""
    found = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/" if prefix else ""):
        for item in page.get("Contents", []):
            name = item["Key"].rsplit("/", 1)[-1]
            if name.startswith(tuple(f"{kind}-" for kind in KINDS)):
                found.append((item["Key"], item["Size"], item["LastModified"]))
    return sorted(found, key=lambda row: row[0].rsplit("/", 1)[-1], reverse=True)


def _prune_remote(client, bucket, prefix, keep):
    """Delete the oldest copies in the bucket, keeping `keep` of each kind. Returns the keys removed."""
    removed = []
    rows = _remote_backups(client, bucket, prefix)
    for kind in KINDS:
        mine = [row for row in rows if row[0].rsplit("/", 1)[-1].startswith(f"{kind}-")]
        for key, _size, _when in mine[keep:]:
            client.delete_object(Bucket=bucket, Key=key)
            removed.append(key)
    return removed


def _upload(paths):
    """Copy files to the configured bucket and trim old copies there. Returns an
    error message or None; the local backup stands either way."""
    try:
        remote = _remote()
        if remote is None:
            return None
        client, bucket, prefix = remote
        for path in paths:
            client.upload_file(str(path), bucket, _key(prefix, path.name))
        _prune_remote(client, bucket, prefix, getattr(settings, "BACKUP_REMOTE_KEEP", 30))
    except Exception as exc:  # noqa: BLE001 - report, don't lose the local copy
        logger.exception("Off-site backup upload failed")
        return str(exc)
    return None


def check_remote():
    """Prove the off-site setup works without making a backup: write, read back and delete
    a tiny file in the bucket. Returns a list of human-readable lines; raises BackupError
    with the reason when something is wrong."""
    try:
        remote = _remote()
    except Exception as exc:  # noqa: BLE001
        raise BackupError(f"Could not set up the bucket client: {exc}")
    if remote is None:
        raise BackupError("BACKUP_S3_BUCKET is not set: backups stay on this server only.")
    client, bucket, prefix = remote
    probe = _key(prefix, f".check-{_stamp()}")
    payload = b"sg-church backup check"
    steps = []
    try:
        client.head_bucket(Bucket=bucket)
        steps.append(f"Bucket '{bucket}' reachable")
        client.put_object(Bucket=bucket, Key=probe, Body=payload)
        steps.append("Can write")
        if client.get_object(Bucket=bucket, Key=probe)["Body"].read() != payload:
            raise BackupError("What was read back is not what was written.")
        steps.append("Can read")
        client.delete_object(Bucket=bucket, Key=probe)
        steps.append("Can delete (old copies can be trimmed)")
        existing = _remote_backups(client, bucket, prefix)
        steps.append(f"{len(existing)} backup file(s) already in the bucket")
    except BackupError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise BackupError(f"{'; '.join(steps) or 'Nothing worked'}. Then failed: {exc}")
    return steps


def list_remote():
    """[(key, size, last_modified)] of the backups in the bucket, newest first."""
    remote = _remote()
    if remote is None:
        raise BackupError("BACKUP_S3_BUCKET is not set.")
    return _remote_backups(*remote)


def create_backup(directory=None, keep=None, upload=True):
    """Make a backup now. Returns {"files": [...], "pruned": [...],
    "upload_error": str | None}."""
    directory = Path(directory or settings.BACKUP_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    keep = settings.BACKUP_KEEP if keep is None else keep
    stamp = _stamp()

    files = [_dump_database(directory, stamp)]
    media = _archive_media(directory, stamp)
    if media:
        files.append(media)

    pruned = _prune(directory, keep)
    upload_error = _upload(files) if upload else None
    logger.info("Backup written: %s", ", ".join(f.name for f in files))
    return {"files": files, "pruned": pruned, "upload_error": upload_error}
