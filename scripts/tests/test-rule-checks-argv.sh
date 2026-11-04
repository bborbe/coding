#!/usr/bin/env bash
# Fixture tests for the bounded, argv-free finding construction and aggregate
# in scripts/rule-checks.sh.
#
# Each case builds a throwaway fixture in a temp dir, so this runs without
# history, tags or network and can sit in `precommit`. The pre-fix baseline is
# derived at test time from the base ref, never committed, so a fabricated
# golden cannot pass.
#
# Exits 1 on any failure so CI catches a regression that puts a payload back
# into an argument list.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
RULES="$REPO/scripts/rule-checks.sh"
RUNNER="$REPO/scripts/ast-grep-runner.sh"
# Pinned pre-fix revision for the baseline. A moving ref (origin/master)
# inverts this baseline once the fix merges — origin/master then IS the fixed
# script, so "the pre-fix script exits 126" becomes "the fixed script exits
# 126", which it does not, and master CI goes red. A tag stays pre-fix
# forever; when it cannot be resolved the baseline is skipped, never failed.
PREFIX_REF="v0.65.4"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

passed=0
failed=0
skipped=0

ok() { printf 'ok   %s\n' "$1"; passed=$((passed + 1)); }
no() {
	printf 'FAIL %s\n' "$1"
	printf '     %s\n' "$2"
	failed=$((failed + 1))
}
skip() {
	printf 'skip %s\n' "$1"
	printf '     %s\n' "$2"
	skipped=$((skipped + 1))
}

expect_eq() { # $1 name, $2 want, $3 got
	if [ "$3" = "$2" ]; then
		ok "$1"
	else
		no "$1" "want '$2', got '$3'"
	fi
}

expect_rc() { # $1 name, $2 want, $3 got
	if [ "$3" = "$2" ]; then
		ok "$1 (rc=$3)"
	else
		no "$1" "want rc=$2, got rc=$3"
	fi
}

# seven_keys_ok <json-file> -> 0 when every emitted finding has exactly the
# seven documented keys with string matched_text/message.
seven_keys_ok() {
	jq -e '
		[.findings_by_owner[][] | select(
			(keys | sort) != ["column","file","line","matched_text","message","rule_id","rule_level"]
			or (.matched_text | type) != "string"
			or (.message | type) != "string"
		)] | length == 0
	' "$1" >/dev/null 2>&1
}

# --- build the ordinary large fixture: 200 findings whose aggregate is huge ---
mkdir -p "$TMP/rc/src"
PAD=$(printf 'a%.0s' $(seq 1 880))
for i in $(seq 1 200); do
	printf 'x = %s/%s\n' '~' "$PAD" >"$TMP/rc/src/f$(printf '%03d' "$i").txt"
done
FILES=("$TMP"/rc/src/*.txt)

# --- case A: the fixed script completes and emits every finding ---
bash "$RULES" "$TMP/rc" "${FILES[@]}" >"$TMP/rc/out.json" 2>"$TMP/rc/err"
expect_rc "large run: fixed script exits 0" 0 "$?"

count=$(jq -r '.stats.findings_count // 0' "$TMP/rc/out.json" 2>/dev/null || echo 0)
if [ "${count:-0}" -ge 200 ]; then
	ok "large run: findings_count >= 200 (got ${count:-0})"
else
	no "large run: findings_count >= 200" "got '${count:-0}'; stderr: $(head -2 "$TMP/rc/err" | tr '\n' ' ')"
fi

map_bytes=$(jq -c '.findings_by_owner' "$TMP/rc/out.json" 2>/dev/null | wc -c | tr -d ' ')
if [ "${map_bytes:-0}" -gt 131072 ]; then
	ok "large run: combined findings map exceeds 131072 bytes (got ${map_bytes:-0})"
else
	no "large run: combined findings map exceeds 131072 bytes" "got '${map_bytes:-0}'"
fi

if seven_keys_ok "$TMP/rc/out.json"; then
	ok "large run: every finding has exactly the seven documented keys and string types"
else
	no "large run: every finding has exactly the seven documented keys and string types" \
		"unexpected keys or non-string text/message"
fi

# --- case B: the pre-fix script dies on the same fixture ---
# The pre-fix failure is `MAX_ARG_STRLEN`, a Linux kernel constant (131072
# bytes per argument). Darwin's limit is ARG_MAX (1 MiB), where the pre-fix
# script completes normally, so asserting rc=126 there would fail for a reason
# that has nothing to do with this fix. Assert it where the kernel enforces it
# and skip loudly elsewhere — a skip is never counted as a pass.
if [ "$(uname -s)" != "Linux" ]; then
	skip "pre-fix baseline" \
		"MAX_ARG_STRLEN is a Linux constant; $(uname -s) allows larger arguments, so the pre-fix script cannot fail on this host"
elif ! git -C "$REPO" rev-parse --verify "$PREFIX_REF^{commit}" >/dev/null 2>&1; then
	skip "pre-fix baseline" \
		"pinned pre-fix ref $PREFIX_REF is not resolvable in $REPO (shallow clone? run: git fetch --tags)"
else
	mkdir -p "$TMP/prefix"
	git -C "$REPO" show "$PREFIX_REF:scripts/rule-checks.sh" >"$TMP/prefix/rule-checks.sh"

	bash "$TMP/prefix/rule-checks.sh" "$TMP/rc" "${FILES[@]}" >"$TMP/prefix/out.json" 2>"$TMP/prefix/err"
	prefix_rc=$?
	prefix_out_bytes=$(wc -c <"$TMP/prefix/out.json" | tr -d ' ')

	expect_rc "pre-fix baseline: exits 126 on the same fixture" 126 "$prefix_rc"
	expect_eq "pre-fix baseline: stdout is empty" 0 "$prefix_out_bytes"
fi

# --- case C: no payload reaches an argument list ---
arg_hits=$(grep -cE -- '--arg(json)? (matched_text|message)' "$RUNNER" "$RULES" 2>/dev/null | awk -F: '{s+=$NF} END{print s+0}')
expect_eq "no payload via --arg: count is 0" 0 "$arg_hits"

fbo_hits=$(grep -c -- '--argjson findings_by_owner' "$RULES" 2>/dev/null || true)
expect_eq "aggregate not passed via --argjson: count is 0" 0 "$fbo_hits"

# --- case D: the grouping key is stripped from the emitted finding ---
sample_keys=$(jq -c '[.findings_by_owner[][]][0] | keys | sort' "$TMP/rc/out.json" 2>/dev/null || true)
expect_eq "emitted finding keys" \
	'["column","file","line","matched_text","message","rule_id","rule_level"]' "$sample_keys"

printf '\n%d passed, %d failed, %d skipped\n' "$passed" "$failed" "$skipped"
[ "$failed" -eq 0 ]
