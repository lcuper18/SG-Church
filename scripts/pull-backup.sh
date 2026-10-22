#!/usr/bin/env bash
# Copy the newest SG Church backups from the server to this computer (a copy outside the server,
# for when there is no off-site bucket yet). Run it by hand or from cron/launchd.
#
#   scripts/pull-backup.sh              # download what is new, keep the last 14 of each kind
#   scripts/pull-backup.sh --now        # make a fresh backup on the server first
#   scripts/pull-backup.sh --list       # only show what the server has
#   scripts/pull-backup.sh --keep 30    # keep more copies here
#
# Settings (environment variables, all optional):
#   SG_SERVER           ssh target of the server            (default root@148.230.92.233)
#   SG_CONTAINER_MATCH  regex of the container to read from (default sg-church-demo.*celery)
#   SG_BACKUP_DEST      where to put the files              (default ~/Backups/sg-church)
#
# Needs: ssh access to the server (use a key, not a password) and Docker running there.
# The backups hold your members' personal data: keep the destination on an encrypted disk (FileVault).
set -euo pipefail

SERVER="${SG_SERVER:-root@148.230.92.233}"
MATCH="${SG_CONTAINER_MATCH:-sg-church-demo.*celery}"
DEST="${SG_BACKUP_DEST:-$HOME/Backups/sg-church}"
KEEP=14
NOW=0
LIST=0
STALE_HOURS=30

while [ $# -gt 0 ]; do
    case "$1" in
        --now) NOW=1 ;;
        --list) LIST=1 ;;
        --keep) KEEP="${2:?--keep needs a number}"; shift ;;
        -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $1 (try --help)" >&2; exit 2 ;;
    esac
    shift
done
case "$KEEP" in ''|*[!0-9]*) echo "--keep must be a number" >&2; exit 2 ;; esac

remote() { ssh -o BatchMode=yes -o ConnectTimeout=15 "$SERVER" "$@"; }

CONTAINER="$(remote "docker ps --format '{{.Names}}' | grep -E '$MATCH' | head -1" || true)"
if [ -z "$CONTAINER" ]; then
    echo "No running container matches '$MATCH' on $SERVER." >&2
    exit 1
fi

if [ "$NOW" = 1 ]; then
    echo "Making a backup on the server..."
    remote "docker exec $CONTAINER python manage.py backup_data --no-upload" | sed 's/^/  /'
fi

# Only names that look like backups are ever used; anything else the server prints is ignored.
FILES="$(remote "docker exec $CONTAINER ls -1 /app/backups" | grep -E '^(db|media)-[0-9]{8}-[0-9]{6}\.[A-Za-z0-9.]+$' | sort || true)"
if [ -z "$FILES" ]; then
    echo "The server has no backups yet. Try: $0 --now" >&2
    exit 1
fi

if [ "$LIST" = 1 ]; then
    echo "$FILES"
    exit 0
fi

mkdir -p "$DEST"
chmod 700 "$DEST"

fetched=0
for name in $FILES; do
    [ -s "$DEST/$name" ] && continue
    expected="$(remote "docker exec $CONTAINER stat -c %s /app/backups/$name" | tr -d '[:space:]')"
    remote "docker exec $CONTAINER cat /app/backups/$name" > "$DEST/$name.part"
    got="$(wc -c < "$DEST/$name.part" | tr -d '[:space:]')"
    if [ "$got" != "$expected" ]; then
        rm -f "$DEST/$name.part"
        echo "FAILED $name: got $got bytes, expected $expected" >&2
        exit 1
    fi
    case "$name" in
        *.gz) gzip -t "$DEST/$name.part" || { rm -f "$DEST/$name.part"; echo "FAILED $name: not a valid gzip file" >&2; exit 1; } ;;
    esac
    mv "$DEST/$name.part" "$DEST/$name"
    chmod 600 "$DEST/$name"
    echo "Downloaded $name ($got bytes)"
    fetched=$((fetched + 1))
done

# Keep only the newest $KEEP of each kind here.
for kind in db media; do
    { ls -1 "$DEST" | grep -E "^$kind-[0-9]{8}-[0-9]{6}\." || true; } | sort -r | tail -n +"$((KEEP + 1))" | while read -r old; do
        rm -f "$DEST/$old"
        echo "Removed old copy $old"
    done
done

# Warn if the newest database backup on the server is old (the nightly job may not be running).
latest="$(echo "$FILES" | grep '^db-' | tail -1 || true)"
stamp="${latest#db-}"; stamp="${stamp%%.*}"
if age_epoch="$(date -u -d "${stamp:0:8} ${stamp:9:2}:${stamp:11:2}:${stamp:13:2}" +%s 2>/dev/null)" \
   || age_epoch="$(date -j -u -f '%Y%m%d-%H%M%S' "$stamp" +%s 2>/dev/null)"; then
    hours=$(( ( $(date -u +%s) - age_epoch ) / 3600 ))
    if [ "$hours" -ge "$STALE_HOURS" ]; then
        echo "WARNING: the newest database backup on the server is $hours hours old. Is the nightly backup running?" >&2
    fi
fi

echo "Done: $fetched new file(s). $(ls -1 "$DEST" | grep -cE '^(db|media)-' || true) file(s) in $DEST"
echo "Restore: see 'Restaurar' in docs/DEPLOYMENT.md"
