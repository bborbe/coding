#!/usr/bin/env bash
# Fixture tests for scripts/check-changelog-unreleased-fold.sh.
#
# Each case builds a throwaway repository in a temp dir, so this runs without
# history, tags or network — which is why it can sit in `precommit` while the
# guard target itself cannot (that one needs a real base ref).
#
# The cases cover the four verdict branches plus the escape regression: a bullet
# carrying a literal backslash sequence must still be found in the merged
# changelog. That one is the reason this file exists — `awk -v` unescapes its
# value, so a bullet containing `\n` compared unequal and the guard reported a
# false MISSING (bborbe/coding#184 review).
#
# Exits 1 on any failure so CI catches verdict drift.

set -uo pipefail

SCRIPT=$(cd "$(dirname "$0")/.." && pwd)/check-changelog-unreleased-fold.sh
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

passed=0
failed=0

ok() { printf 'ok   %s\n' "$1"; passed=$((passed + 1)); }
no() {
	printf 'FAIL %s\n' "$1"
	printf '     %s\n' "$2"
	failed=$((failed + 1))
}

repo() { # $1 = name -> creates $TMP/$1 on branch master, prints its path
	git init -q -b master "$TMP/$1"
	git -C "$TMP/$1" config user.email test@example.com
	git -C "$TMP/$1" config user.name Test
	printf '%s\n' "$TMP/$1"
}

changelog() { # $1 = repo, stdin = body after the preamble
	{
		printf '# Changelog\n\n'
		cat
	} >"$1/CHANGELOG.md"
}

commit() { # $1 = repo, $2 = message
	git -C "$1" add -A
	git -C "$1" commit -q -m "$2"
}

# run <repo> <base-ref> -> prints the guard's combined output, returns its exit
run() {
	CHANGELOG_ROOT="$1" CHANGELOG_BASE_REF="$2" CHANGELOG_HEAD_REF=HEAD \
		bash "$SCRIPT" 2>&1
}

expect_rc() { # $1 = case, $2 = want rc, $3 = got rc, $4 = output
	if [ "$3" = "$2" ]; then
		ok "$1 (rc=$3)"
	else
		no "$1" "want rc=$2, got rc=$3; output: $(printf '%s' "$4" | head -3 | tr '\n' ' ')"
	fi
}

expect_contains() { # $1 = case, $2 = needle, $3 = output
	case "$3" in
	*"$2"*) ok "$1" ;;
	*) no "$1" "output does not contain '$2': $(printf '%s' "$3" | head -3 | tr '\n' ' ')" ;;
	esac
}

# --- case 1: out of scope — the branch's top heading is not `## Unreleased` ---
r=$(repo out-of-scope)
changelog "$r" <<'EOF'
## v1.0.0

- feat: released work
EOF
commit "$r" "release v1.0.0"
out=$(run "$r" master)
expect_rc "out-of-scope passes" 0 "$?" "$out"
expect_contains "out-of-scope names the top section" "topmost section is '## v1.0.0'" "$out"

# --- case 2: the fold — the branch's Unreleased was renamed on the base side ---
r=$(repo fold)
changelog "$r" <<'EOF'
## v1.0.0

- feat: released work
EOF
commit "$r" "release v1.0.0"
changelog "$r" <<'EOF'
## Unreleased

- feat: pending one

## v1.0.0

- feat: released work
EOF
commit "$r" "add pending work"
git -C "$r" branch branch
changelog "$r" <<'EOF'
## v1.1.0

- feat: pending one

## v1.0.0

- feat: released work
EOF
commit "$r" "release v1.1.0"
git -C "$r" switch -q branch
changelog "$r" <<'EOF'
## Unreleased

- feat: pending one
- feat: pending two

## v1.0.0

- feat: released work
EOF
commit "$r" "add pending two"
out=$(run "$r" master)
expect_rc "fold fails" 1 "$?" "$out"
expect_contains "fold names the released section" "would land under: ## v1.1.0" "$out"

# --- case 3: a fresh Unreleased above the release — legitimate, must pass ---
# The branch is cut AFTER the cut, so its `## Unreleased` is a new heading rather
# than the one master renamed. A heading comparison would fail this case; the
# computed merge must not.
r=$(repo fresh-unreleased)
changelog "$r" <<'EOF'
## v1.0.0

- feat: released work
EOF
commit "$r" "release v1.0.0"
changelog "$r" <<'EOF'
## Unreleased

- feat: pending one

## v1.0.0

- feat: released work
EOF
commit "$r" "add pending work"
changelog "$r" <<'EOF'
## v1.1.0

- feat: pending one

## v1.0.0

- feat: released work
EOF
commit "$r" "release v1.1.0"
git -C "$r" branch branch
git -C "$r" switch -q branch
changelog "$r" <<'EOF'
## Unreleased

- feat: legitimately pending

## v1.1.0

- feat: pending one

## v1.0.0

- feat: released work
EOF
commit "$r" "add pending work"
out=$(run "$r" master)
expect_rc "fresh Unreleased passes" 0 "$?" "$out"
expect_contains "fresh Unreleased reports pending" "land under ## Unreleased" "$out"

# --- case 4: escape regression — a backslash in the bullet must still match ---
# `awk -v` unescapes its value, so `\n` in a bullet became a real newline and the
# exact-line compare failed, reporting a false MISSING. This case is why the file
# exists; it must PASS, and it must never print MISSING.
r=$(repo backslash)
changelog "$r" <<'EOF'
## v1.0.0

- feat: released work
EOF
commit "$r" "release v1.0.0"
changelog "$r" <<'EOF'
## Unreleased

- feat: pending one

## v1.0.0

- feat: released work
EOF
commit "$r" "add pending work"
changelog "$r" <<'EOF'
## v1.1.0

- feat: pending one

## v1.0.0

- feat: released work
EOF
commit "$r" "release v1.1.0"
git -C "$r" branch branch
git -C "$r" switch -q branch
changelog "$r" <<'EOF'
## Unreleased

- fix: replace `tr '\n' '\0'` in the writer

## v1.1.0

- feat: pending one

## v1.0.0

- feat: released work
EOF
commit "$r" "add pending work"
out=$(run "$r" master)
expect_rc "backslash bullet passes" 0 "$?" "$out"
case "$out" in
*MISSING*) no "backslash bullet is found in the merged changelog" "reported MISSING" ;;
*) ok "backslash bullet is found in the merged changelog" ;;
esac

# --- case 5: an unpredictable merge fails closed ---
# Master renames the heading while the branch rewrites a bullet in the same
# hunk, so the merge conflicts and the fold cannot be predicted.
r=$(repo conflict)
changelog "$r" <<'EOF'
## v1.0.0

- feat: released work
EOF
commit "$r" "release v1.0.0"
changelog "$r" <<'EOF'
## Unreleased

- feat: pending one

## v1.0.0

- feat: released work
EOF
commit "$r" "add pending work"
git -C "$r" branch branch
changelog "$r" <<'EOF'
## v1.1.0

- feat: pending one, reworded on master

## v1.0.0

- feat: released work
EOF
commit "$r" "release v1.1.0"
git -C "$r" switch -q branch
changelog "$r" <<'EOF'
## Unreleased

- feat: pending one, reworded on the branch

## v1.0.0

- feat: released work
EOF
commit "$r" "reword on the branch"
out=$(run "$r" master)
expect_rc "conflict fails closed" 1 "$?" "$out"
expect_contains "conflict says the merge cannot be predicted" "cannot be predicted" "$out"

printf '\n%d passed, %d failed\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
