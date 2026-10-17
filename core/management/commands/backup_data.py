"""
Back up the database and the uploaded files.

    python manage.py backup_data            # into settings.BACKUP_DIR
    python manage.py backup_data --keep 30  # keep the 30 newest of each kind
    python manage.py backup_data --no-upload

The same job runs every night through Celery beat; run it by hand before a
risky change or to test the setup. See docs/DEPLOYMENT.md for restoring.
"""

from django.core.management.base import BaseCommand, CommandError

from core.backup import BackupError, create_backup


class Command(BaseCommand):
    help = "Back up the database and uploaded files, prune old ones, copy off-site if configured."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=None, help="Target directory (default: BACKUP_DIR)")
        parser.add_argument("--keep", type=int, default=None, help="How many to keep of each kind")
        parser.add_argument(
            "--no-upload", action="store_true", help="Skip the off-site copy even if configured"
        )

    def handle(self, *args, **options):
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
