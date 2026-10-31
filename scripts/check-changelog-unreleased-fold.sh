#!/usr/bin/env bash
#
# Changelog unreleased-fold PRE-CHECK.
#
# The sibling `check-changelog-fold.sh` runs on a push to master, i.e. AFTER the
# merge landed, and reports what that merge did. By then master is already red
# and the failure mail is already in the operator's inbox — on
# `bborbe/claude-supervisor` that was 91 consecutive runs before it was repaired
# on 2026-10-31, and the repair PR itself was folded by its own merge.
#
# This guard asks the same question BEFORE the merge, by computing the merge:
#
#   a release cut renames the top `## Unreleased` to `## vX.Y.Z` on master. A PR
#   branch cut before that cut still carries `## Unreleased`. GitHub's merge
#   resolution matches the BULLET LIST rather than the heading, so the branch's
#   new bullets are spliced into the already-released section — cleanly, with no
#   conflict and no warning. The changelog then claims work the tag does not
#   contain, and the post-merge guard fails master.
#
# THE VERDICT IS THE MERGE ITSELF, not a heading heuristic. `git merge-tree
# --write-tree` computes the merge of the base branch into the PR head without
# touching any working tree, and the check reads where each of the PR's new
# `## Unreleased` bullets lands in the RESULT. A bullet that lands under a
# released heading is the fold, named exactly, before it can happen.
#
# A heading comparison alone would be wrong in the common, legitimate case: a
# branch cut AFTER the release adds a fresh `## Unreleased` above `## vX.Y.Z`,
# and that merges cleanly and correctly. `merge-tree` sees the difference because
# the bullet lands under `## Unreleased` in the result; a `head top is
# ## Unreleased while base top is ## vX.Y.Z` test does not.
#
# SCOPE — the probe runs only when all three hold:
#   1. the working tree's topmost heading is `## Unreleased`   (the branch has
#      pending work at the top)
#   2. the base branch's topmost heading is a released `## vX.Y.Z`  (a cut
#      happened on the base side)
#   3. the branch carries at least one `## Unreleased` bullet the base does not
#      have anywhere in its changelog  (there is something to fold)
# Outside that shape the merge cannot fold anything, and the check passes
# without computing a merge at all — so an ordinary PR never pays for this and
# never goes red on an unrelated conflict.
#
# An unanswerable question is a failure, never a pass: an unresolvable base ref
# or a merge that conflicts in the changelog is reported as FAIL, because a
# silent pass there is indistinguishable from a real one.
#
# Exit codes: 0 clean (or out of scope), 1 fold predicted or the question
# unanswerable.
#
# Run from the repo root (`CHANGELOG_BASE_REF` defaults to `origin/master`), or
# from the reusable workflow .github/workflows/changelog-unreleased-fold-guard.yml,
# which a consuming repo calls from its own `pull_request` job.

set -euo pipefail

# ROOT defaults to the repo the script lives in (the local / Makefile case).
# CHANGELOG_ROOT overrides it for the reusable workflow, which runs this script
# from a sibling checkout of coding while the CHANGELOG under test belongs to
# the calling repo.
ROOT=${CHANGELOG_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
cd "$ROOT"

CHANGELOG=${CHANGELOG_PATH:-CHANGELOG.md}
BASE_REF=${CHANGELOG_BASE_REF:-origin/master}
HEAD_REF=${CHANGELOG_HEAD_REF:-HEAD}

die() {
	printf 'FAIL: %s\n' "$*" >&2
	exit 1
}

# A repo without a CHANGELOG.md has no released section to fold into. Reported
# as a skip, never an "ok" — a wrong root directory lands here too.
[ -f "$CHANGELOG" ] || {
	echo "  changelog-unreleased-fold skipped: no $CHANGELOG at $ROOT"
	exit 0
}

command -v git >/dev/null 2>&1 || die "git not available — cannot predict the fold"
git rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository — cannot predict the fold"

git rev-parse --verify --quiet "$BASE_REF^{commit}" >/dev/null ||
	die "base ref '$BASE_REF' does not resolve to a commit.
     Fetch it first, or set CHANGELOG_BASE_REF. An unresolvable base is an
     unanswered question, not a clean tree."
git rev-parse --verify --quiet "$HEAD_REF^{commit}" >/dev/null ||
	die "head ref '$HEAD_REF' does not resolve to a commit."

# The helpers below read from a HERESTRING, never from a pipe, and that is
# load-bearing rather than style. Each one stops at its first answer, so with
# `set -o pipefail` an upstream `printf` in a pipeline is left with unread input,
# takes SIGPIPE, and the whole assignment fails with exit 141 — a script that
# reports nothing and exits on a changelog large enough to fill the pipe buffer.
# Measured 2026-10-31 on `bborbe/claude-supervisor`: three of four probe branches
# died with rc=141 before printing a single line.

# Topmost `## ` heading of the changelog supplied on stdin.
top_heading() {
	awk '/^## / { print; exit }'
}

# Bullets under `## Unreleased`, stopping at the next `## ` heading.
unreleased_bullets() {
	awk '
		$0 == "## Unreleased" { inside = 1; next }
		inside && /^## / { exit }
		inside && /^- / { print }
	'
}

# Which section does $1 sit under, in the changelog supplied on stdin?
sits_under() {
	awk -v want="$1" '
		/^## / { sec = $0 }
		$0 == want { print sec; exit }
	'
}

# Both sides are read from COMMITS, never from the working tree: the merge that
# is being predicted is a merge of commits, and mixing an uncommitted file into
# it would let the bullets and the merge disagree about what the branch is.
head_changelog=$(git show "$HEAD_REF:$CHANGELOG" 2>/dev/null) ||
	die "'$HEAD_REF' does not carry $CHANGELOG — cannot tell what the branch has pending.
     An unanswered question is not a clean tree."

head_top=$(top_heading <<<"$head_changelog")
if [ "$head_top" != "## Unreleased" ]; then
	echo "  changelog-unreleased-fold ok: topmost section is '${head_top:-none}' — no pending section at the top to fold"
	exit 0
fi

base_changelog=$(git show "$BASE_REF:$CHANGELOG" 2>/dev/null) ||
	die "'$BASE_REF' does not carry $CHANGELOG — cannot tell what the base has released.
     An unanswered question is not a clean tree."

base_top=$(top_heading <<<"$base_changelog")
if ! grep -qE '^## v[0-9]+\.[0-9]+\.[0-9]+$' <<<"$base_top"; then
	echo "  changelog-unreleased-fold ok: base topmost section is '${base_top:-none}' — no release cut on the base side, so a merge unions the two sections"
	exit 0
fi

head_bullets=$(unreleased_bullets <<<"$head_changelog")
new_bullets=$(
	while IFS= read -r bullet; do
		[ -n "$bullet" ] || continue
		# Here-string, not a pipe: `grep -q` exits on the first match, so an
		# upstream `printf` would SIGPIPE and pipefail would report the pipeline
		# as failed even though the bullet WAS found — printing it a second time.
		grep -qxF -- "$bullet" <<<"$base_changelog" || printf '%s\n' "$bullet"
	done <<<"$head_bullets"
)
if [ -z "$new_bullets" ]; then
	echo "  changelog-unreleased-fold ok: the branch adds no bullet the base lacks — nothing a merge could fold"
	exit 0
fi

# Compute the merge the way the forge would, without touching any working tree.
#
# stdout and stderr are captured SEPARATELY, and the tree is read from stdout
# alone: `merge-tree` writes the tree OID first on stdout but its progress lines
# ("Auto-merging …", "CONFLICT …") on stderr, so a combined `2>&1` would let a
# stray stderr line become `head -1` and be mistaken for the tree.
merge_err=$(mktemp)
trap 'rm -f "$merge_err"' EXIT
merge_out=$(git merge-tree --write-tree "$BASE_REF" "$HEAD_REF" 2>"$merge_err") && merge_rc=0 || merge_rc=$?
merged_tree=$(head -1 <<<"$merge_out")
if [ "$merge_rc" -ne 0 ]; then
	printf 'FAIL: merging %s into %s conflicts, so the fold cannot be predicted.\n' "$BASE_REF" "$HEAD_REF" >&2
	printf '      Merge %s into the branch first, then re-run.\n\n' "$BASE_REF" >&2
	# `merge-tree` writes the conflicted-stage entries and its progress lines to
	# stdout, below the tree OID; stderr is normally empty. Print both so the
	# reader sees which path conflicted.
	sed -n '1,20p' "$merge_err" | sed 's/^/      /' >&2
	printf '%s\n' "$merge_out" | sed -n '2,20p' | sed 's/^/      /' >&2
	rm -f "$merge_err"
	exit 1
fi
rm -f "$merge_err"
git cat-file -e "${merged_tree}^{tree}" 2>/dev/null ||
	die "'git merge-tree' returned no usable tree (got '$merged_tree') — the fold cannot be predicted"

merged_changelog=$(git show "$merged_tree:$CHANGELOG" 2>/dev/null) || merged_changelog=""

folded=0
missing=0
while IFS= read -r bullet; do
	[ -n "$bullet" ] || continue
	landed=$(sits_under "$bullet" <<<"$merged_changelog")
	case "$landed" in
	"## Unreleased")
		printf '  pending: %s\n' "$bullet"
		;;
	"")
		missing=$((missing + 1))
		printf 'MISSING: %s\n' "$bullet" >&2
		printf '         absent from the merged changelog — the merge would drop it\n' >&2
		;;
	*)
		folded=$((folded + 1))
		printf 'FOLDED: %s\n' "$bullet" >&2
		printf '        would land under: %s\n' "$landed" >&2
		printf '        %s is already released, and this branch was cut before that cut —\n' "$landed" >&2
		printf '        the merge splices the bullet into the released section, which then\n' >&2
		printf '        claims work its tag does not contain.\n' >&2
		;;
	esac
done <<<"$new_bullets"

if [ "$folded" -gt 0 ]; then
	printf '\nFAIL: %d bullet(s) would fold into a released section when %s is merged.\n' \
		"$folded" "$BASE_REF" >&2
	cat >&2 <<EOF
The bullets above are still pending work: no tag contains them, so they belong
under \`## Unreleased\`, not in a released section. Repair the branch:

  git fetch origin
  git merge $BASE_REF

The merge will put them in the wrong place — that is the fold this check exists
to catch. Restore a \`## Unreleased\` heading above the topmost released heading
and move the bullets into it, then push. Do NOT move them into the released
section: the release predates them, and the post-merge guard would fail master.
EOF
fi

if [ "$missing" -gt 0 ]; then
	printf '\nFAIL: %d bullet(s) would disappear from the merged changelog.\n' "$missing" >&2
	printf 'Reported rather than passed: a dropped entry is released work vanishing silently.\n' >&2
fi

if [ "$folded" -gt 0 ] || [ "$missing" -gt 0 ]; then
	exit 1
fi

echo "  changelog-unreleased-fold ok: $(printf '%s\n' "$new_bullets" | grep -c .) new bullet(s) land under ## Unreleased after merging $BASE_REF"
