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

# Every released section below is compared against ITS OWN tag, never against the
# newest tag's snapshot. The newest tag's file necessarily carries every earlier
# section as it stood at that later cut — including one that had already been
# folded — so comparing against it makes the working tree's bullets a SUBSET, the
# extras come out empty, and the fold is silently masked on exactly the repos that
# have released since. Measured 2026-09-26 on `bborbe/claude-supervisor`:
# `## v0.57.2` held 1 bullet in its own tag and 4 in `v0.57.3`'s snapshot, so
# master read clean while a bullet whose merge was in no `v0.57.2` was misfiled
# there. A guard that goes quiet after the next release is worse than no guard.

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

# The wording $2 replaced at commit $1, or empty when that commit ADDED the line
# outright — which is how the caller tells a rewrite from a genuine introduction.
#
# Exact index pairing comes first, because it cannot be wrong: it fires only
# when the target sits in a hunk whose removals and additions line up, which is
# what an in-place rewrite looks like. The similarity fallback covers the hunks
# where they do not — measured 2026-09-30 on `bborbe/claude-supervisor`, where
# the last of 69 false positives sat in a hunk of 7 removals against 15
# additions and so had no line at its own index to pair with.
#
# The fallback is a guess, so it is held to a high bar: only the removed line
# sharing the longest opening with the target, and only if that opening clears
# `min_prefix` characters. Both bounds matter — a loose match would pair a genuinely
# new bullet with an unrelated removal and attribute it to old work, which masks
# a real fold rather than merely mislabelling one, and that is the one direction
# this guard must never fail in.
pre_image() { # $1 = commit, $2 = exact line at $1
	local min_prefix=40
	git diff --unified=0 "$1^" "$1" -- "$CHANGELOG" 2>/dev/null |
		awk -v want="$2" -v min_prefix="$min_prefix" '
			function lcp(a, b,   i, n) {
				n = (length(a) < length(b)) ? length(a) : length(b)
				for (i = 1; i <= n; i++)
					if (substr(a, i, 1) != substr(b, i, 1)) break
				return i - 1
			}
			/^@@/ { h++; n[h] = 0; m[h] = 0; next }
			/^-/ && !/^---/ { n[h]++; minus[h, n[h]] = substr($0, 2); next }
			/^\+/ && !/^\+\+\+/ { m[h]++; plus[h, m[h]] = substr($0, 2); next }
			END {
				for (k = 1; k <= h; k++)
					for (i = 1; i <= m[k]; i++)
						if (plus[k, i] == want && i <= n[k]) {
							print minus[k, i]
							exit
						}
				for (k = 1; k <= h; k++) {
					best = 0
					best_line = ""
					for (i = 1; i <= n[k]; i++) {
						s = lcp(minus[k, i], want)
						if (s > best) {
							best = s
							best_line = minus[k, i]
						}
					}
					if (best >= min_prefix) {
						print best_line
						exit
					}
				}
			}
		'
}

# The commit that introduced $1's CONTENT, or empty when unanswerable.
#
# TWO defects make the naive `git log -S` walk answer with a commit that is not
# the bullet's merge. Both were measured 2026-09-30 on `bborbe/claude-supervisor`,
# where together they produced 69 FOLDED bullets of which every one was a false
# positive — the whole released changelog reading as folded.
#
# 1. A HEAD-ONLY WALK COLLAPSES AFTER A HISTORY REWRITE. Rewriting history
#    re-adds CHANGELOG.md wholesale at the new root, so the root is the earliest
#    change in HEAD's ancestry for EVERY bullet. `merge-base --is-ancestor <root>
#    <old-tag>` is then false for every old tag, and the file reads folded
#    throughout. There, all 69 named the same root commit. `--all` is the fix: it
#    reaches the pre-rewrite history through the tags that still point into it.
#
# 2. `-S` CANNOT SEE THROUGH A TEXT REWRITE. A bulk wording edit — the
#    vault-title scrub batches — changes a line's text without adding work, so
#    `-S` on the NEW wording finds only the rewrite. The rewrite is on master but
#    in no tag, and "no tag" is this guard's signal for FOLDED: the bullet reads
#    folded although its content shipped. Stepping over such a commit and walking
#    back to the wording it replaced re-attributes the bullet to the commit that
#    introduced its CONTENT, which is what the `--contains` test needs.
#
# A commit in NO tag is therefore only trusted when it ADDED the line. A paired
# removal+addition is a rewrite and is walked back; a pure addition is a genuine
# introduction whose work has not been released, and stays the answer so that a
# real fold is still reported as one rather than degraded to UNVERIFIABLE.
attribute() { # $1 = exact bullet line
	local bullet="$1" sha prev tries=0
	while [ "$tries" -lt 8 ]; do
		sha=$(git log --all --format=%H -m -S"$bullet" -- "$CHANGELOG" 2>/dev/null | tail -1)
		[ -n "$sha" ] || return 1

		# In some tag -> the bullet's content shipped by then, so this is the
		# commit the `--contains` test wants.
		if [ -n "$(git tag --contains "$sha" 2>/dev/null | head -1)" ]; then
			printf '%s\n' "$sha"
			return 0
		fi

		prev=$(pre_image "$sha" "$bullet")
		if [ -z "$prev" ]; then
			# Added, not rewritten: a genuine introduction, still unreleased.
			printf '%s\n' "$sha"
			return 0
		fi

		bullet="$prev"
		tries=$((tries + 1))
	done
	return 1
}

folded=0
tested=0
sections=0
stalled=0
unverifiable=0

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
	# The section's own tag is both the comparison source and the basis of the
	# verdict. A section present only in the working tree is a new release in
	# flight, not a fold — and it is skipped as unverifiable rather than
	# compared against some other release's snapshot.
	if ! git rev-parse -q --verify "refs/tags/$heading" >/dev/null 2>&1; then
		printf '  unverifiable: %s has no tag of its own — skipped\n' "$heading" >&2
		continue
	fi
	if ! git cat-file -e "$heading:$CHANGELOG" 2>/dev/null; then
		printf '  unverifiable: %s does not carry %s — skipped\n' "$heading" "$CHANGELOG" >&2
		continue
	fi

	work=$(section "$heading" <"$CHANGELOG" | grep -E '^- ' || true)
	tagged=$(git show "$heading:$CHANGELOG" | section "$heading" | grep -E '^- ' || true)

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

		# `-m` is required, not cosmetic: `git log -S` skips merge commits by
		# default, and a bullet introduced by a merge RESOLUTION — the fold's own
		# mechanism — is then unattributable and reported UNVERIFIABLE. Measured
		# 2026-09-26: the `three-command-review-split` bullet is verbatim in HEAD,
		# plain `-S` finds no commit for it, and `-S -m` finds the merge that
		# introduced it. Without this the guard fails on exactly the shape it
		# exists to catch.
		#
		# `tail -1` takes the EARLIEST commit that changed this line's count —
		# where the text first appeared. Deliberate: an unfold PR re-placing an
		# already-released bullet introduces the text a second time, and the
		# later commit would be misread as the feature's own merge. The first
		# appearance is the feature's branch commit, which is what the
		# `--contains` test needs. Verified against both shapes 2026-09-26.
		#
		# The walk itself lives in `attribute`, which also compensates for the
		# two attribution defects documented there.
		sha=$(attribute "$bullet" || true)
		if [ -z "$sha" ]; then
			# Unanswerable, so never a pass — but reported and stepped over
			# rather than fatal. Aborting here would hide every finding after
			# this bullet, which is the same silence in a different costume.
			unverifiable=$((unverifiable + 1))
			printf 'UNVERIFIABLE: %s\n' "$bullet" >&2
			printf '              sits under: %s\n' "$(sits_under "$bullet")" >&2
			printf '              no commit in this file'\''s history introduced this line — release unknowable\n' >&2
			continue
		fi

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

if [ "$unverifiable" -gt 0 ]; then
	printf '\nFAIL: %d bullet(s) could not be attributed to a commit, so their release is unknowable.\n' \
		"$unverifiable" >&2
	printf 'Reported rather than passed, and still a failure: an unanswered question is not a clean tree.\n' >&2
fi

# Every signature is reported before exiting — the fold names the misfiled
# bullets, the stall names the consequence, and unverifiable names what could
# not be answered at all. A reader needs all three.
if [ "$folded" -gt 0 ] || [ "$stalled" -gt 0 ] || [ "$unverifiable" -gt 0 ]; then
	exit 1
fi

echo "  changelog-fold ok: $sections released section(s), $tested candidate(s), 0 folded"
