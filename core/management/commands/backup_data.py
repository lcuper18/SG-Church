"""
Back up the database and the uploaded files.

    python manage.py backup_data            # into settings.BACKUP_DIR
    python manage.py backup_data --keep 30  # keep the 30 newest of each kind
    python manage.py backup_data --no-upload
    python manage.py backup_data --check-remote   # test the bucket settings, no backup made
    python manage.py backup_data --list-remote    # what is stored off-site

The same job runs every night through Celery beat; run it by hand before a
risky change or to test the setup. See docs/DEPLOYMENT.md for restoring.
"""

from django.core.management.base import BaseCommand, CommandError

from core.backup import BackupError, check_remote, create_backup, list_remote


class Command(BaseCommand):
    help = "Back up the database and uploaded files, prune old ones, copy off-site if configured."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=None, help="Target directory (default: BACKUP_DIR)")
        parser.add_argument("--keep", type=int, default=None, help="How many to keep of each kind")
        parser.add_argument("--check-remote", action="store_true", help="Test the off-site bucket settings and exit")
        parser.add_argument("--list-remote", action="store_true", help="List the backups stored off-site and exit")
        parser.add_argument(
            "--no-upload", action="store_true", help="Skip the off-site copy even if configured"
        )

    def handle(self, *args, **options):
        if options["check_remote"]:
            try:
                for line in check_remote():
                    self.stdout.write(self.style.SUCCESS(f"OK  {line}"))
            except BackupError as exc:
                raise CommandError(str(exc))
            return
        if options["list_remote"]:
            try:
                rows = list_remote()
            except BackupError as exc:
                raise CommandError(str(exc))
            for key, size, when in rows:
                self.stdout.write(f"{when:%Y-%m-%d %H:%M}  {size:>12,} B  {key}")
            self.stdout.write(f"{len(rows)} file(s) off-site.")
            return
        try:
            result = create_backup(
                directory=options["dir"], keep=options["keep"], upload=not options["no_upload"]
            )
        except BackupError as exc:
            raise CommandError(str(exc))

        for path in result["files"]:
            self.stdout.write(self.style.SUCCESS(f"Created {path} ({path.stat().st_size} bytes)"))
        if result["pruned"]:
            self.stdout.write(f"Removed {len(result['pruned'])} old file(s).")
        if result["upload_error"]:
            raise CommandError(
                f"Local backup is fine, but the off-site copy failed: {result['upload_error']}"
            )
