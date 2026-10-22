"""
scripts/pull-backup.sh, exercised against a fake `ssh` that runs the remote commands locally
on a directory standing in for the server's /app/backups.
"""

import gzip
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "pull-backup.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


@pytest.fixture
def world(tmp_path):
    """A fake server: `ssh` runs the command locally, `docker` serves files from `remote_dir`."""
    remote_dir = tmp_path / "remote"
    remote_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "ssh").write_text(
        '#!/bin/bash\nwhile [[ "$1" == -* ]]; do if [ "$1" = "-o" ]; then shift 2; else shift; fi; done\n'
        'shift\nexec bash -c "$*"\n'
    )
    (bin_dir / "docker").write_text(
        f"""#!/bin/bash
R="{remote_dir}"
case "$1" in
  ps) echo "sg-church-demo-x-celery-1"; echo "other-thing-1" ;;
  exec)
    shift 2   # drop 'exec <container>'
    case "$1" in
      ls) ls -1 "$R"; echo "../../etc/passwd; rm -rf" ;;
      cat) cat "$R/$(basename "$2")" ;;
      stat) wc -c < "$R/$(basename "$4")" ;;
      python) echo "backup made"; : > "$R/.touched" ;;
    esac ;;
esac
"""
    )
    for tool in ("ssh", "docker"):
        (bin_dir / tool).chmod((bin_dir / tool).stat().st_mode | stat.S_IEXEC)
    dest = tmp_path / "mac"
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "SG_BACKUP_DEST": str(dest), "SG_SERVER": "fake"}
    return remote_dir, dest, env


def run(env, *args):
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True)


def make_backup(remote_dir, stamp, kind="db", payload=b"datos"):
    name = f"{kind}-{stamp}.sql.gz" if kind == "db" else f"{kind}-{stamp}.tar.gz"
    (remote_dir / name).write_bytes(gzip.compress(payload))
    return name


def test_downloads_new_files_and_is_private(world):
    remote, dest, env = world
    name = make_backup(remote, "20261020-030000")
    result = run(env)
    assert result.returncode == 0, result.stderr
    assert (dest / name).read_bytes() == (remote / name).read_bytes()
    assert stat.S_IMODE(dest.stat().st_mode) == 0o700 and stat.S_IMODE((dest / name).stat().st_mode) == 0o600
    assert "Downloaded" in result.stdout


def test_a_second_run_downloads_nothing_new(world):
    remote, dest, env = world
    make_backup(remote, "20261020-030000")
    run(env)
    again = run(env)
    assert "Downloaded" not in again.stdout and "0 new file(s)" in again.stdout


def test_only_the_newest_are_kept_here(world):
    remote, dest, env = world
    for day in range(1, 6):
        make_backup(remote, f"2026102{day}-030000")
    run(env, "--keep", "2")
    assert sorted(p.name for p in dest.iterdir()) == ["db-20261024-030000.sql.gz", "db-20261025-030000.sql.gz"]


def test_a_corrupt_download_is_rejected_and_leaves_nothing(world):
    remote, dest, env = world
    (remote / "db-20261020-030000.sql.gz").write_bytes(b"not gzip at all")
    result = run(env)
    assert result.returncode == 1 and "not a valid gzip" in result.stderr
    assert list(dest.iterdir()) == []


def test_odd_file_names_from_the_server_are_ignored(world):
    remote, dest, env = world
    make_backup(remote, "20261020-030000")
    (remote / "notas.txt").write_text("x")
    result = run(env)
    assert [p.name for p in dest.iterdir()] == ["db-20261020-030000.sql.gz"]
    assert "passwd" not in result.stdout


def test_list_does_not_download(world):
    remote, dest, env = world
    make_backup(remote, "20261020-030000")
    result = run(env, "--list")
    assert "db-20261020-030000.sql.gz" in result.stdout and not dest.exists()


def test_now_asks_the_server_for_a_fresh_backup(world):
    remote, dest, env = world
    make_backup(remote, "20261020-030000")
    result = run(env, "--now")
    assert "backup made" in result.stdout and (remote / ".touched").exists()


def test_an_old_backup_triggers_a_warning(world):
    remote, dest, env = world
    make_backup(remote, "20200101-030000")
    assert "WARNING" in run(env).stderr


def test_no_server_backups_is_an_error(world):
    remote, dest, env = world
    result = run(env)
    assert result.returncode == 1 and "no backups yet" in result.stderr


def test_bad_options(world):
    _, _, env = world
    assert run(env, "--keep", "x").returncode == 2
    assert run(env, "--nope").returncode == 2
