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


def _upload(paths):
    """Copy files to the configured bucket. Returns an error message or None;
    the local backup stands either way."""
    bucket = getattr(settings, "BACKUP_S3_BUCKET", "")
    if not bucket:
        return None
    try:
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=settings.BACKUP_S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            region_name=settings.AWS_S3_REGION_NAME or None,
        )
        prefix = settings.BACKUP_S3_PREFIX.strip("/")
        for path in paths:
            key = f"{prefix}/{path.name}" if prefix else path.name
            client.upload_file(str(path), bucket, key)
    except Exception as exc:  # noqa: BLE001 - report, don't lose the local copy
        logger.exception("Off-site backup upload failed")
        return str(exc)
    return None


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
