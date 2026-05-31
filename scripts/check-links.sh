#!/usr/bin/env bash
#
# Validates that markdown links in README.md and llms.txt point to files that
# exist within the repository. Prints "BROKEN: <file> -> <link>" for each broken
# link and exits non-zero if any are found. Exits 0 with "All links OK" when
# all links are valid.
#
# Files checked: README.md, llms.txt
#
# Repo root is computed from the script's own location via
# `dirname "$0"` — the script is invoked from the Makefile `check-links`
# target (`@bash scripts/check-links.sh`).

set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

EXIT=0
for file in README.md llms.txt; do
	while read -r link; do
		target=${link%%#*}
		[ -z "$target" ] && continue
		if [ ! -e "$target" ]; then
			echo "BROKEN: $file -> $link"
			EXIT=1
		fi
	done < <(grep -oP '\]\(\K[^)]+' "$file" 2>/dev/null | grep -v '^http' | grep -v '^mailto:')
done
if [ "$EXIT" -eq 1 ]; then exit 1; fi
echo "All links OK"
