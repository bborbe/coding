#!/usr/bin/env bash
#
# Changelog fold guard.
#
# A release cut renames `## Unreleased` to `## vX.Y.Z`. A PR whose branch was
# cut before that still carries `## Unreleased`; GitHub's merge resolution then
# matches the *bullet list* rather than the heading, and splices the PR's bullets
# into the already-released section. The merge is clean, nothing warns, and the
# changelog now claims work the tag does not contain.
#
# THE PRE-FILTER SET — placement-based, and never decisive:
#   1. the released section in the working tree byte-differs from the tag's
#   2. the `awk` "sits under" assertion — which section a bullet sits under
#   3. `git diff <tag> HEAD -- CHANGELOG.md | grep -E '^[-+]## '`
# Any one of them selects which bullets to test. None of them decides, and the
# 2026-09-25 incident is why: a bullet re-placed into a released section by an
# unfold PR reads as an extra under every one of the three, while its code
# genuinely shipped in that tag. Acting on placement moved two shipped features
# into the next release and duplicated both.
#
# THE AUTHORITATIVE VERDICT, per bullet, is `git tag --contains <merge-sha>`:
#   no tag  -> the bullet's merge is in no release  -> FOLDED
#   has tag -> the code shipped in that release     -> shipped
#
# An unanswerable question is a failure, never a pass: a shallow clone has no
# tags, and a silent pass there is indistinguishable from a real one. That is
# the default state of actions/checkout, so it is checked explicitly.
#
# Exit codes: 0 clean, 1 fold found or the question unanswerable.
#
# Run from repo root (Makefile target `check-changelog-fold`), or from the
# reusable workflow .github/workflows/changelog-fold-guard.yml, which a
# consuming repo calls from its own post-merge job on master push.

set -euo pipefail

# ROOT defaults to the repo the script lives in (the Makefile target case).
# CHANGELOG_ROOT overrides it for the reusable workflow, which runs this script
# from a sibling checkout of coding while the CHANGELOG under test belongs to
# the calling repo.
ROOT=${CHANGELOG_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
cd "$ROOT"

CHANGELOG=${CHANGELOG_PATH:-CHANGELOG.md}

die() {
	printf 'FAIL: %s\n' "$*" >&2
	exit 1
}

# A repo without a CHANGELOG.md has no released section to fold into. Reported
# as a skip, never an "ok": a wrong root directory lands here too, and an "ok"
# would make that indistinguishable from a real pass.
[ -f "$CHANGELOG" ] || {
	echo "  changelog-fold skipped: no $CHANGELOG at $ROOT"
	exit 0
}

command -v git >/dev/null 2>&1 || die "git not available — cannot check the fold"
git rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository — cannot check the fold"

if [ "$(git rev-parse --is-shallow-repository 2>/dev/null || echo false)" = "true" ]; then
	die "shallow clone — tags are unavailable, so the fold cannot be checked.
     This is an unanswerable question, not a clean tree.
     Set actions/checkout with fetch-depth: 0 and fetch-tags: true."
fi

TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)
if [ -z "$TAG" ]; then
	echo "  changelog-fold ok: no tags — nothing released, so no released section exists to fold into"
	exit 0
fi

TAGFILE=$(mktemp)
trap 'rm -f "$TAGFILE"' EXIT
git show "$TAG:$CHANGELOG" >"$TAGFILE" 2>/dev/null ||
	die "cannot read $CHANGELOG at $TAG — the tag does not carry the file"

# Body of `## <heading>` on stdin, stopping at the next `## ` heading.
section() { # $1 = heading text without the leading "## "
	awk -v want="$1" '
		$0 == "## " want { inside = 1; next }
		inside && /^## / { exit }
		inside { print }
	'
}

# Which section does $1 sit under? The `awk` "sits under" assertion.
sits_under() { # $1 = exact bullet line
	awk -v want="$1" '
		/^## / { sec = $0 }
		$0 == want { print sec; exit }
	' "$CHANGELOG"
}

folded=0
tested=0
sections=0
stalled=0

# --- the stall signature ---------------------------------------------------
# The fold consumes `## Unreleased`, and a repo with unreleased work but no
# section to cut it from has silently stopped releasing: the watcher logs
# `no-release-files` and the change can never ship. That is the same defect one
# step later, and it is the failure `unreleased_not_found` is a symptom of — so
# it is checked here rather than left to the releaser to discover.
if ! grep -qxF "## Unreleased" "$CHANGELOG"; then
	unreleased=$(git diff --name-only "$TAG" HEAD 2>/dev/null | grep -vxF "$CHANGELOG" || true)
	if [ -n "$unreleased" ]; then
		stalled=1
		count=$(printf '%s\n' "$unreleased" | grep -c . || true)
		printf 'STALLED: no `## Unreleased` section, but %s file(s) differ from %s:\n' \
			"$count" "$TAG" >&2
		printf '%s\n' "$unreleased" | head -5 | sed 's/^/         /' >&2
		printf '         the release watcher has nothing to cut, so this work can never ship\n' >&2
	fi
fi

while IFS= read -r heading; do
	# A section present only in the working tree is a new release in flight,
	# not a fold — the tag has nothing to compare it against.
	grep -qxF "## $heading" "$TAGFILE" || continue

	# The section's own tag is what decides the verdict. Without it the section
	# is unverifiable — reported, never silently passed.
	if ! git rev-parse -q --verify "refs/tags/$heading" >/dev/null 2>&1; then
		printf '  unverifiable: %s has no tag of its own — skipped\n' "$heading" >&2
		continue
	fi

	work=$(section "$heading" <"$CHANGELOG" | grep -E '^- ' || true)
	tagged=$(section "$heading" <"$TAGFILE" | grep -E '^- ' || true)

	sections=$((sections + 1))

	# Pre-filter 1: byte-identical section -> nothing to test.
	[ "$work" = "$tagged" ] && continue

	# The extras are the fold candidates. Each is still only a candidate:
	# the tag decides.
	while IFS= read -r bullet; do
		[ -n "$bullet" ] || continue
		# `--` is required: a bullet begins with "- ", which grep would
		# otherwise read as an option cluster.
		printf '%s\n' "$tagged" | grep -qxF -- "$bullet" && continue
		tested=$((tested + 1))

		# `tail -1` takes the EARLIEST commit that changed this line's count —
		# where the text first appeared. Deliberate: an unfold PR re-placing an
		# already-released bullet introduces the text a second time, and the
		# later commit would be misread as the feature's own merge. The first
		# appearance is the feature's branch commit, which is what the
		# `--contains` test needs. Verified against both shapes 2026-09-26.
		sha=$(git log --format=%H -S"$bullet" -- "$CHANGELOG" 2>/dev/null | tail -1)
		[ -n "$sha" ] ||
			die "cannot find the commit that introduced this bullet, so its release is unknowable:
     $bullet"

		# The authoritative test: is this bullet's merge an ancestor of THIS
		# section's own tag? Asking `git tag --contains` for *any* tag is the
		# trap — it answers v0.18.4 for a bullet misfiled under `## v0.18.3`,
		# which reads as "shipped" while the bullet still claims a release that
		# does not contain it. Caught by the real v0.18.3 replay 2026-09-26.
		if git merge-base --is-ancestor "$sha" "$heading" 2>/dev/null; then
			printf '  shipped: %s\n' "$bullet"
			printf '           merge %s is in %s\n' "$(git rev-parse --short "$sha")" "$heading"
		else
			folded=$((folded + 1))
			printf 'FOLDED: %s\n' "$bullet" >&2
			printf '        sits under: %s\n' "$(sits_under "$bullet")" >&2
			printf '        merge %s is NOT in %s — the section claims work that release does not contain\n' \
				"$(git rev-parse --short "$sha")" "$heading" >&2
		fi
	done <<<"$work"
done < <(grep -E '^## v[0-9]+\.[0-9]+\.[0-9]+$' "$CHANGELOG" | sed 's/^## //')

if [ "$folded" -gt 0 ]; then
	printf '\nFAIL: %d folded bullet(s) across %d released section(s) at %s.\n' \
		"$folded" "$sections" "$TAG" >&2
	cat >&2 <<'EOF'
Restore a `## Unreleased` section above the top released heading and move the
folded bullets into it. Do not move a bullet whose merge IS in that section's
own tag — that one shipped, and moving it duplicates the entry in the next
release.
EOF
fi

if [ "$stalled" -gt 0 ]; then
	printf '\nFAIL: the releaser is stalled at %s — unreleased work with no `## Unreleased` section.\n' \
		"$TAG" >&2
	printf 'Add a `## Unreleased` heading above the top released section and move the\n' >&2
	printf 'unreleased entries into it. An empty one is not enough — the releaser rejects\n' >&2
	printf 'a section with no bullets.\n' >&2
fi

# Both signatures are reported before exiting: the fold names the misfiled
# bullets, the stall names the consequence, and a reader needs both.
if [ "$folded" -gt 0 ] || [ "$stalled" -gt 0 ]; then
	exit 1
fi

echo "  changelog-fold ok: $sections released section(s) at $TAG, $tested candidate(s), 0 folded"
