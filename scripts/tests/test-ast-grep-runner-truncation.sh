#!/usr/bin/env bash
# Fixture tests for the bounded, argv-free finding construction in
# scripts/ast-grep-runner.sh and its shared helper scripts/lib/truncate-utf8.sh.
#
# Each case builds a throwaway fixture in a temp dir, so this runs without
# history, tags or network and can sit in `precommit`. The pre-fix baseline in
# case B is derived at test time from the base ref, never committed, so a
# fabricated golden cannot pass.
#
# Exits 1 on any failure so CI catches truncation drift.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
RUNNER="$REPO/scripts/ast-grep-runner.sh"
HELPER="$REPO/scripts/lib/truncate-utf8.sh"
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

expect_rc() { # $1 name, $2 want, $3 got
	if [ "$3" = "$2" ]; then
		ok "$1 (rc=$3)"
	else
		no "$1" "want rc=$2, got rc=$3"
	fi
}

expect_eq() { # $1 name, $2 want, $3 got
	if [ "$3" = "$2" ]; then
		ok "$1"
	else
		no "$1" "want '$2', got '$3'"
	fi
}

expect_contains() { # $1 name, $2 needle, $3 haystack
	case "$3" in
	*"$2"*) ok "$1" ;;
	*) no "$1" "value does not contain '$2'" ;;
	esac
}

expect_not_contains() { # $1 name, $2 needle, $3 haystack
	case "$3" in
	*"$2"*) no "$1" "value unexpectedly contains '$2'" ;;
	*) ok "$1" ;;
	esac
}

repeat_a() { python3 -c 'import sys; sys.stdout.write("a" * int(sys.argv[1]))' "$1"; }
bytes_of() { wc -c < "$1" | tr -d ' '; }

# finding_by_rule <json-file> <rule-id> -> compact sorted finding, or empty
finding_by_rule() {
	jq -cS --arg rid "$2" '[.findings_by_owner[][] | select(.rule_id==$rid)][0]' "$1"
}

# --- case A: a 131072-byte match is bounded, marked, and the run survives ---
mkdir -p "$TMP/ac1/pkg/order"
payload_len=$((131072 - 18 - 2))
{
	printf 'package order\n\nfunc load() error {\n\treturn fmt.Errorf("%%s", "'
	repeat_a "$payload_len"
	printf '")\n}\n'
} >"$TMP/ac1/pkg/order/big.go"

bash "$RUNNER" "$TMP/ac1" >"$TMP/ac1/out.json" 2>"$TMP/ac1/err"
expect_rc "big match: runner exits 0" 0 "$?"

count=$(jq -r '.stats.findings_count // 0' "$TMP/ac1/out.json" 2>/dev/null || echo 0)
if [ "${count:-0}" -ge 1 ]; then
	ok "big match: findings_count >= 1 (got ${count:-0})"
else
	no "big match: findings_count >= 1" "got '${count:-0}'; stderr: $(head -2 "$TMP/ac1/err" | tr '\n' ' ')"
fi

big=$(finding_by_rule "$TMP/ac1/out.json" 'go-errors/no-fmt-errorf')
big_text=$(printf '%s' "$big" | jq -r '.matched_text // ""' 2>/dev/null || true)
expect_contains "big match: matched_text carries the marker naming 131072" \
	'…[truncated, original 131072 bytes]' "$big_text"

big_prefix=$(printf '%s' "$big_text" | python3 -c '
import sys
marker = "…[truncated, original 131072 bytes]"
text = sys.stdin.buffer.read().decode("utf-8")
print(len(text[:-len(marker)].encode("utf-8")) if text.endswith(marker) else -1)
')
if [ "${big_prefix:--1}" -ge 0 ] && [ "${big_prefix:--1}" -le 8192 ]; then
	ok "big match: cut content is at most 8192 bytes (got $big_prefix)"
else
	no "big match: cut content is at most 8192 bytes" "got '$big_prefix'"
fi

# --- case B: an ordinary small match is byte-identical to the pre-fix output ---
mkdir -p "$TMP/ac4/pkg/order"
printf 'package order\n\nfunc load() error {\n\treturn fmt.Errorf("boom")\n}\n' \
	>"$TMP/ac4/pkg/order/small.go"

if ! git -C "$REPO" rev-parse --verify origin/master >/dev/null 2>&1; then
	no "small match: base ref resolvable" "origin/master is not resolvable in $REPO"
else
	mkdir -p "$TMP/prefix/scripts"
	git -C "$REPO" show origin/master:scripts/ast-grep-runner.sh >"$TMP/prefix/scripts/ast-grep-runner.sh"
	ln -s "$REPO/rules" "$TMP/prefix/rules"

	bash "$RUNNER" "$TMP/ac4" >"$TMP/ac4/fixed.json" 2>"$TMP/ac4/fixed.err"
	fixed_rc=$?
	bash "$TMP/prefix/scripts/ast-grep-runner.sh" "$TMP/ac4" >"$TMP/ac4/prefix.json" 2>"$TMP/ac4/prefix.err"
	prefix_rc=$?

	if [ "$fixed_rc" -eq 0 ] && [ "$prefix_rc" -eq 0 ]; then
		fixed_finding=$(finding_by_rule "$TMP/ac4/fixed.json" 'go-errors/no-fmt-errorf')
		prefix_finding=$(finding_by_rule "$TMP/ac4/prefix.json" 'go-errors/no-fmt-errorf')
		if [ -n "$fixed_finding" ]; then
			expect_eq "small match: finding is byte-identical to pre-fix output" \
				"$prefix_finding" "$fixed_finding"
		else
			no "small match: finding is byte-identical to pre-fix output" "no finding emitted"
		fi
		fixed_text=$(printf '%s' "$fixed_finding" | jq -r '.matched_text // ""' 2>/dev/null || true)
		expect_not_contains "small match: no truncation marker" "truncated" "$fixed_text"
	else
		no "small match: both runners exit 0" "fixed rc=$fixed_rc, pre-fix rc=$prefix_rc"
	fi
fi

# --- case C: an interpolated message over 1024 bytes is bounded ---
mkdir -p "$TMP/ac5/mirror/scripts/lib" "$TMP/ac5/mirror/rules/test" "$TMP/ac5/src"
cp "$REPO/scripts/ast-grep-runner.sh" "$TMP/ac5/mirror/scripts/"
cp "$HELPER" "$TMP/ac5/mirror/scripts/lib/"
cat >"$TMP/ac5/mirror/rules/index.json" <<'JSON'
[{"id":"test/big-message","owner":"test-owner","level":"MUST","enforcement":"`rules/test/big-message.yml`"}]
JSON
cat >"$TMP/ac5/mirror/rules/test/big-message.yml" <<'YAML'
id: test/big-message
language: go
severity: error
message: "offending call: $CALL"
rule:
  all:
    - kind: call_expression
    - pattern: $CALL
YAML
{
	printf 'package order\n\nfunc load() error {\n\treturn bigCall("'
	repeat_a 2000
	printf '")\n}\n'
} >"$TMP/ac5/src/msg.go"

bash "$TMP/ac5/mirror/scripts/ast-grep-runner.sh" "$TMP/ac5/src" >"$TMP/ac5/out.json" 2>"$TMP/ac5/err"
expect_rc "big message: runner exits 0" 0 "$?"

msg_finding=$(finding_by_rule "$TMP/ac5/out.json" 'test/big-message')
msg=$(printf '%s' "$msg_finding" | jq -r '.message // ""' 2>/dev/null || true)
msg_text=$(printf '%s' "$msg_finding" | jq -r '.matched_text // ""' 2>/dev/null || true)

expect_contains "big message: message carries the marker" '…[truncated, original ' "$msg"
expect_contains "big message: marker closes with a byte count" ' bytes]' "$msg"

msg_stats=$(printf '%s' "$msg" | python3 -c '
import sys
marker = "…[truncated, original "
tail = " bytes]"
text = sys.stdin.buffer.read().decode("utf-8")
if not text.endswith(tail) or marker not in text:
    print("-1 -1")
else:
    i = text.rfind(marker)
    n = text[i + len(marker):-len(tail)]
    print("%d %s" % (len(text[:i].encode("utf-8")), n if n.isdigit() else "-1"))
')
msg_prefix=${msg_stats% *}
msg_orig=${msg_stats#* }

if [ "${msg_prefix:--1}" -ge 0 ] && [ "${msg_prefix:--1}" -le 1024 ]; then
	ok "big message: cut content is at most 1024 bytes (got $msg_prefix)"
else
	no "big message: cut content is at most 1024 bytes" "got '$msg_prefix'"
fi
if [ "${msg_orig:--1}" -gt 1024 ] 2>/dev/null; then
	ok "big message: marker names an original length over 1024 (got $msg_orig)"
else
	no "big message: marker names an original length over 1024" "got '$msg_orig'"
fi
expect_not_contains "big message: matched_text is under its own bound" "truncated" "$msg_text"

# --- case D: the helper's boundary cases ---
# shellcheck disable=SC1090,SC1091  # helper path is resolved at runtime
. "$HELPER"
mkdir -p "$TMP/acd"

repeat_a 8192 >"$TMP/acd/in8192"
truncate_utf8_file 8192 "$TMP/acd/in8192" "$TMP/acd/out8192"
expect_eq "boundary: 8192-byte input passes through unchanged" 8192 "$(bytes_of "$TMP/acd/out8192")"
expect_not_contains "boundary: 8192-byte input carries no marker" "truncated" "$(cat "$TMP/acd/out8192")"

repeat_a 8193 >"$TMP/acd/in8193"
truncate_utf8_file 8192 "$TMP/acd/in8193" "$TMP/acd/out8193"
expect_contains "boundary: 8193-byte input is marked" '…[truncated, original 8193 bytes]' "$(cat "$TMP/acd/out8193")"
marker_8193='…[truncated, original 8193 bytes]'
marker_8193_bytes=$(printf '%s' "$marker_8193" | wc -c | tr -d ' ')
expect_eq "boundary: 8193-byte input keeps an 8192-byte prefix" 8192 \
	"$(( $(bytes_of "$TMP/acd/out8193") - marker_8193_bytes ))"

{
	repeat_a 8191
	printf 'é'
} >"$TMP/acd/split"
truncate_utf8_file 8192 "$TMP/acd/split" "$TMP/acd/split.out"
if python3 -c 'import sys; open(sys.argv[1], encoding="utf-8").read()' "$TMP/acd/split.out" 2>/dev/null; then
	ok "split rune: output is valid UTF-8"
else
	no "split rune: output is valid UTF-8" "decoding failed"
fi
expect_contains "split rune: marker names the original 8193 bytes" \
	'…[truncated, original 8193 bytes]' "$(cat "$TMP/acd/split.out")"
marker_split_bytes=$(printf '%s' '…[truncated, original 8193 bytes]' | wc -c | tr -d ' ')
expect_eq "split rune: cut backs off to the previous rune (8191 bytes)" 8191 \
	"$(( $(bytes_of "$TMP/acd/split.out") - marker_split_bytes ))"

repeat_a 100000 >"$TMP/acd/in100k"
truncate_utf8_file 8192 "$TMP/acd/in100k" "$TMP/acd/out100k"
marker_100k='…[truncated, original 100000 bytes]'
marker_100k_bytes=$(printf '%s' "$marker_100k" | wc -c | tr -d ' ')
if [ "$(bytes_of "$TMP/acd/out100k")" -le $((8192 + marker_100k_bytes)) ]; then
	ok "boundary: 100000-byte input is bounded to the cut plus the marker"
else
	no "boundary: 100000-byte input is bounded to the cut plus the marker" \
		"got $(bytes_of "$TMP/acd/out100k") bytes"
fi

# --- case E: two matches in one scan stream do not corrupt each other ---
mkdir -p "$TMP/ace/pkg/order"
{
	printf 'package order\n\nfunc load() error {\n\treturn fmt.Errorf("%%s", "'
	repeat_a "$payload_len"
	printf '")\n}\n'
} >"$TMP/ace/pkg/order/big.go"
printf 'package order\n\nfunc load2() error {\n\treturn fmt.Errorf("boom")\n}\n' \
	>"$TMP/ace/pkg/order/small.go"

bash "$RUNNER" "$TMP/ace" >"$TMP/ace/out.json" 2>"$TMP/ace/err"
expect_rc "two matches: runner exits 0" 0 "$?"

ace_count=$(jq -r '.stats.findings_count // 0' "$TMP/ace/out.json" 2>/dev/null || echo 0)
expect_eq "two matches: both findings are emitted" 2 "$ace_count"
ace_big=$(jq -r '[.findings_by_owner[][] | select(.rule_id=="go-errors/no-fmt-errorf" and (.matched_text | contains("truncated")))] | length' "$TMP/ace/out.json" 2>/dev/null || echo 0)
ace_small=$(jq -r '[.findings_by_owner[][] | select(.rule_id=="go-errors/no-fmt-errorf" and (.matched_text | contains("truncated") | not))] | length' "$TMP/ace/out.json" 2>/dev/null || echo 0)
expect_eq "two matches: the oversized one is marked" 1 "$ace_big"
expect_eq "two matches: the small one is untouched" 1 "$ace_small"

printf '\n%d passed, %d failed\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
