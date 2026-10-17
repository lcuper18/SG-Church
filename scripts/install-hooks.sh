#!/usr/bin/env bash
# Point git at the versioned hooks. Run once per clone.
set -euo pipefail
cd "$(dirname "$0")/.."
git config core.hooksPath scripts/git-hooks
chmod +x scripts/check.sh scripts/git-hooks/*
echo "Git hooks installed: 'git push' now runs scripts/check.sh first."
