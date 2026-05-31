#!/usr/bin/env bash
#
# Scan an external directory against this repo's ast-grep rule base.
#
# Loads all rules from rules/ via sgconfig.yml in the repo root and runs
# ast-grep against the given target. Any extra arguments are passed through
# to ast-grep (e.g. --json=stream, --report-style short, --filter severity=error).
#
# Exit semantics: ast-grep exits non-zero if any `error`-severity rule matches.
# `warning` and `info` matches exit 0 by default.
#
# Usage:
#   scripts/scan.sh <target-dir> [ast-grep flags...]
#   scripts/scan.sh ~/Documents/workspaces/run
#   scripts/scan.sh ~/Documents/workspaces/run --json=stream
#
# Requires: ast-grep on PATH.

set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/scan.sh <target-dir> [ast-grep flags...]" >&2
  exit 2
fi

target=$1
shift

if [ ! -d "$target" ]; then
  echo "error: target not found or not a directory: $target" >&2
  exit 1
fi

exec ast-grep scan -c "$ROOT/sgconfig.yml" "$@" "$target"
