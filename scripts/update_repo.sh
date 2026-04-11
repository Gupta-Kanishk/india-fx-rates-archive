#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
cd "${REPO_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required but not installed or not available in PATH."
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "Error: git is required but not installed or not available in PATH."
  exit 1
fi

python3 scripts/download_fx_rates.py

git add banks

if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi

commit_message="Update FX rates: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-main}"

git commit -m "$commit_message"
git push "$GIT_REMOTE" "$GIT_BRANCH"
