#!/usr/bin/env python3
"""Unit tests for bench/run.py scoring: match relation, states, gap-triage, and ratio rendering."""

import collections
import copy
import dataclasses
import filecmp
import hashlib
import itertools
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import run
import testsupport


BENCH_DIR = pathlib.Path(__file__).resolve().parent


# The frozen golden fixture, NOT the live bench/golden.json.
#
# The live set is designed to change: its own scoring_note instructs promoting a
# finding several configurations agree on, and demoting one nothing reproduces.
# Pinning the live file's digest, line count and entry count made every such
# adjudication break this suite — the tests contradicted the workflow they exist
# to protect.  Scorer behaviour is pinned against this frozen copy instead, so
# the numbers below stay meaningful while bench/golden.json evolves.
GOLDEN_FIXTURE = BENCH_DIR / "testdata" / "golden-dev-1.json"


def load_golden():
    return json.loads(GOLDEN_FIXTURE.read_text(encoding="utf-8"))


def load_slice(name):
    path = BENCH_DIR / "testdata" / name
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
class TestFixtureProvenance(unittest.TestCase):
    """AC2: golden set and ledger slices match published digests and line counts."""

    def test_live_golden_set_stays_loadable_and_well_formed(self):
        """The shipped bench/golden.json must survive every adjudication.

        Deliberately asserts NO digest, entry count or version — those belong to
        the frozen fixture.  This is the only check that still looks at the live
        file: without it, pointing the rest of the suite at the fixture would
        leave a promote/demote free to corrupt the real set unnoticed.
        """
        live = BENCH_DIR / "golden.json"
        golden = run.load_golden(live)  # raises BenchError on a malformed set

        self.assertTrue(golden["entries"], "live golden set is empty")
        allowed = {"accepted", "rejected", "unreviewed"}
        for i, entry in enumerate(golden["entries"]):
            self.assertIn(entry.get("state"), allowed,
                          f"entry {i} has state {entry.get('state')!r}")
            # `path` must be PRESENT but may be null: a commit-message finding
            # ("commit c6f136a — subject is 62 chars") has no file, and since
            # 2026-08-10 path is provenance rather than identity, so a null one
            # no longer makes the entry unmatchable.  Requiring it to be truthy
            # would reject exactly those legitimate entries.
            self.assertIn("path", entry, f"entry {i} has no path key")
            self.assertTrue(entry.get("signature"),
                            f"entry {i} has an empty signature — would match "
                            f"every finding in its PR")
            for kw in entry["signature"]:
                self.assertTrue(kw.strip(), f"entry {i} has a blank keyword")

    def test_no_live_golden_entry_aliases_another(self):
        """No single finding may satisfy two golden entries.

        Adjudication on 2026-08-09 added a line-free `apt-key` entry for an issue
        the baseline already carried pinned to `ci.yml:32`.  The same issue was
        then represented twice, three findings matched both, and recall inflated
        to a spurious 1.000.  The false-positive check performed at the time only
        compared a new signature against the ledger's findings — never against the
        other entries — so nothing caught it.  This is that missing check.
        """
        golden = run.load_golden(BENCH_DIR / "golden.json")
        ledger = BENCH_DIR / "results" / "results.jsonl"
        if not ledger.exists():
            self.skipTest("no ledger to check aliasing against")

        rows = [json.loads(l) for l in
                ledger.read_text(encoding="utf-8").splitlines() if l.strip()]

        for row in rows:
            for finding in row.get("findings", []):
                matched = [e for e in golden["entries"]
                           if e["pr_id"] == row["pr_id"]
                           and run.finding_matches_entry(e, finding)]
                self.assertLessEqual(
                    len(matched), 1,
                    f"finding on {finding.get('path')} matches "
                    f"{len(matched)} golden entries "
                    f"({[e['signature'] for e in matched]}) — one issue must be "
                    f"one entry, or recall double-counts",
                )

    def test_golden_json_sha256(self):
        digest = hashlib.sha256(
            GOLDEN_FIXTURE.read_bytes()
        ).hexdigest()
        self.assertEqual(
            digest,
            "d13b0218b19ec95d77587c43ebf48886524b05d3d77acb562a97cf28529d6582",
        )

    def test_baseline_slice_sha256(self):
        digest = hashlib.sha256(
            (BENCH_DIR / "testdata" / "ledger-baseline-opus-xhigh-full.jsonl").read_bytes()
        ).hexdigest()
        self.assertEqual(
            digest,
            "af8f684b95e82577af4ac6b4a04392559ef04865ee95e7f8afdcc8f1756e86fb",
        )

    def test_four_run_slice_sha256(self):
        digest = hashlib.sha256(
            (BENCH_DIR / "testdata" / "ledger-sonnet-medium-short-4runs.jsonl").read_bytes()
        ).hexdigest()
        self.assertEqual(
            digest,
            "f25b759a09d6fbedcf3f755977492324369ce19db40933fc77d17497d8596d02",
        )

    def test_partial_slice_sha256(self):
        digest = hashlib.sha256(
            (BENCH_DIR / "testdata" / "ledger-sonnet-medium-short-partial.jsonl").read_bytes()
        ).hexdigest()
        self.assertEqual(
            digest,
            "165320f9edcd45bcbe3938685e0bc052c4adf56545c7317a87f5aff7945c24a7",
        )

    def test_probe_slice_sha256(self):
        digest = hashlib.sha256(
            (BENCH_DIR / "testdata" / "ledger-probe-configs-mixed-prs-version.jsonl").read_bytes()
        ).hexdigest()
        self.assertEqual(
            digest,
            "f19cb4e9824f078b498a82c0ce2c55a884a28ca16ac0a33c9c3bd48dd478e209",
        )

    def test_line_counts(self):
        self.assertEqual((GOLDEN_FIXTURE).read_text().count("\n"), 658)
        self.assertEqual(
            (BENCH_DIR / "testdata" / "ledger-baseline-opus-xhigh-full.jsonl").read_text().count("\n"), 5
        )
        self.assertEqual(
            (BENCH_DIR / "testdata" / "ledger-sonnet-medium-short-4runs.jsonl").read_text().count("\n"), 20
        )
        self.assertEqual(
            (BENCH_DIR / "testdata" / "ledger-sonnet-medium-short-partial.jsonl").read_text().count("\n"), 32
        )
        self.assertEqual(
            (BENCH_DIR / "testdata" / "ledger-probe-configs-mixed-prs-version.jsonl").read_text().count("\n"), 4
        )


# ----------------------------------------------------------------------
# AC3: baseline self-match is perfect
# ----------------------------------------------------------------------
class TestBaselineSelfMatchIsPerfect(unittest.TestCase):
    """AC3: baseline slice scored against real golden set is 42/42/0/0."""

    def test_full_score_result_matches_expected(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        expected = run.ScoreResult(
            entries_in_scope=42,
            accepted_in_scope=42,
            accepted_hits=42,
            misses=0,
            matched_rejected=0,
            excluded_unreviewed=0,
            findings=42,
            gap_candidates=(),
            recall="1.000",
            precision="1.000",
        )
        self.assertEqual(
            result,
            expected,
            f"baseline self-match: got {result!r}, expected {expected!r}",
        )

    def test_entries_in_scope_filters_by_pr_id(self):
        golden = load_golden()
        self.assertEqual(len(run.entries_in_scope(golden, {"tts-mcp#20"})), 1)
        self.assertEqual(
            len(run.entries_in_scope(golden, {"quant#109", "tts-mcp#20"})), 7
        )


# ----------------------------------------------------------------------
# AC7: line is never used for identity
# ----------------------------------------------------------------------
class TestLineIsNeverUsedForIdentity(unittest.TestCase):
    """AC7: setting finding line to None or +1000 does not change the score."""

    def _run_with_mutated_lines(self, mutate_fn):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        for row in rows:
            for f in row.get("findings") or []:
                mutate_fn(f)
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        return run.score_findings(entries=entries, findings=findings)

    def test_all_lines_set_to_none(self):
        result = self._run_with_mutated_lines(lambda f: f.update(line=None))
        self.assertEqual(result.entries_in_scope, 42)
        self.assertEqual(result.accepted_in_scope, 42)
        self.assertEqual(result.accepted_hits, 42)
        self.assertEqual(result.misses, 0)
        self.assertEqual(result.gap_candidates, ())
        self.assertEqual(result.recall, "1.000")
        self.assertEqual(result.precision, "1.000")

    def test_all_non_null_lines_incremented_by_1000(self):
        # node-skeleton#2/test/health.test.ts has line:null — guard against
        # f["line"] + 1000 raising TypeError
        result = self._run_with_mutated_lines(
            lambda f: f.update(line=f["line"] + 1000) if f.get("line") is not None else None
        )
        self.assertEqual(result.accepted_hits, 42)
        self.assertEqual(result.misses, 0)
        self.assertEqual(result.gap_candidates, ())
        self.assertEqual(result.recall, "1.000")

    def test_golden_line_when_seen_set_to_none_unchanged(self):
        # Mutating line_when_seen on the golden side also changes nothing
        golden = copy.deepcopy(load_golden())
        for entry in golden["entries"]:
            entry["line_when_seen"] = None
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertEqual(result.accepted_hits, 42)
        self.assertEqual(result.misses, 0)


# ----------------------------------------------------------------------
# AC8: rule_id takes priority
# ----------------------------------------------------------------------
class TestRuleIdConstrainsIdentity(unittest.TestCase):
    """AC8, amended 2026-08-10: rule_id constrains identity, never short-circuits it.

    The original name and contract were "rule_id takes priority" — a match on
    rule_id alone, ignoring path and signature.  That credited any config finding
    *some* instance of a rule with the specific instance in the golden set.  The
    tests below still hold under the amended matcher because they exercise
    agreement and disagreement, not the short-circuit; the aliasing case is
    covered in TestRuleIdConstrainsButNeverShortCircuits.
    """

    def setUp(self):
        self.golden = load_golden()
        self.rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        # Locate the github-pr-review-agent#11 CHANGELOG.md entry with rule_id
        self.changelog_entry = None
        for e in self.golden["entries"]:
            if e["pr_id"] == "github-pr-review-agent#11" and e["path"] == "CHANGELOG.md":
                self.changelog_entry = e
                break
        self.assertIsNotNone(self.changelog_entry)

    def _get_changelog_finding(self, rows):
        for row in rows:
            if row["pr_id"] != "github-pr-review-agent#11":
                continue
            for f in row.get("findings") or []:
                if f["path"] == "CHANGELOG.md":
                    return f
        self.fail("CHANGELOG.md finding not found in github-pr-review-agent#11 row")

    # Case A: rule_id disagreement → miss even if path + signature still match
    def test_case_a_mismatch_rule_id_produces_miss(self):
        rows = copy.deepcopy(self.rows)
        finding = self._get_changelog_finding(rows)
        original_rule_id = finding["rule_id"]
        finding["rule_id"] = "made-up/other-rule"
        entries = run.entries_in_scope(self.golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertEqual(result.accepted_hits, 41, "expected 41 hits when rule_id mismatches")
        self.assertEqual(result.misses, 1, "expected 1 miss when rule_id mismatches")
        self.assertFalse(
            run.finding_matches_entry(self.changelog_entry, finding),
            "matcher must return False when rule_ids disagree",
        )
        self.assertEqual(finding["path"], "CHANGELOG.md")
        self.assertIn("changelog.md:11", finding["body"].lower())

    # Case B: finding rule_id set to None → falls through to path + signature
    def test_case_b_null_finding_rule_id_falls_through(self):
        rows = copy.deepcopy(self.rows)
        finding = self._get_changelog_finding(rows)
        finding["rule_id"] = None
        entries = run.entries_in_scope(self.golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertEqual(result.accepted_hits, 42, "expected 42 hits when finding rule_id is None")
        self.assertEqual(result.misses, 0)
        self.assertTrue(
            run.finding_matches_entry(self.changelog_entry, finding),
            "entry should match when finding rule_id is None and path+signature agree",
        )

    # Case C: entry has null rule_id, finding has one → still path + signature
    def test_case_c_null_entry_rule_id_with_finding_rule_id(self):
        # node-skeleton#2 README.md entry has rule_id: null
        null_entry = None
        for e in self.golden["entries"]:
            if e["pr_id"] == "node-skeleton#2" and e["path"] == "README.md" and e["rule_id"] is None:
                null_entry = e
                break
        self.assertIsNotNone(null_entry)
        rows = copy.deepcopy(self.rows)
        # Find the matching finding and give it a rule_id
        injected_finding = None
        for row in rows:
            if row["pr_id"] != "node-skeleton#2":
                continue
            for f in row.get("findings") or []:
                if f["path"] == "README.md":
                    injected_finding = f
                    break
        self.assertIsNotNone(injected_finding)
        injected_finding["rule_id"] = "injected/rule"
        self.assertTrue(
            run.finding_matches_entry(null_entry, injected_finding),
            "entry with null rule_id matched by finding with rule_id via path+signature",
        )
        entries = run.entries_in_scope(self.golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertEqual(result.accepted_hits, 42, "injected rule_id on finding must not break match")

    # Case D: one finding can satisfy two entries (relation, not assignment)
    def test_case_d_one_finding_hits_two_entries(self):
        # Add a second entry for python-skeleton#3 / .github/workflows/ci.yml
        # whose signature also matches the apt-key finding's body
        golden = copy.deepcopy(self.golden)
        golden["entries"].append({
            "pr_id": "python-skeleton#3",
            "path": ".github/workflows/ci.yml",
            "signature": ["apt-key"],
            "rule_id": None,
            "state": "accepted",
            "line_when_seen": 32,
            "excerpt": "",
        })
        rows = self.rows
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        # Two entries (original + new) matched by one finding
        self.assertEqual(result.entries_in_scope, 43)
        self.assertEqual(result.accepted_in_scope, 43)
        self.assertEqual(result.accepted_hits, 43, "one finding must satisfy both entries")
        self.assertEqual(result.misses, 0)
        self.assertEqual(result.gap_candidates, (), "the finding that matched two entries is not a gap candidate")


# ----------------------------------------------------------------------
# AC9: signature requires every keyword, case-insensitively
# ----------------------------------------------------------------------
class TestSignatureRequiresEveryKeywordCaseInsensitively(unittest.TestCase):
    """AC9: all signature keywords must appear in body (case-insensitive)."""

    def setUp(self):
        self.golden = load_golden()
        self.rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        # node-skeleton#2 README.md entry: rule_id is null, signature ["readme.md:107"]
        self.entry = None
        for e in self.golden["entries"]:
            if e["pr_id"] == "node-skeleton#2" and e["path"] == "README.md" and e["rule_id"] is None:
                self.entry = e
                break
        self.assertIsNotNone(self.entry)
        # Baseline: 42 hits
        entries = run.entries_in_scope(self.golden, {r["pr_id"] for r in self.rows})
        findings = run.iter_findings(self.rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertEqual(result.accepted_hits, 42, "baseline must be 42 hits")

    def test_missing_keyword_becomes_miss(self):
        golden = copy.deepcopy(self.golden)
        for e in golden["entries"]:
            if e["pr_id"] == "node-skeleton#2" and e["path"] == "README.md" and e["rule_id"] is None:
                e["signature"] = e["signature"] + ["zzz-absent-keyword"]
                break
        rows = self.rows
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertEqual(result.accepted_hits, 41, "missing keyword must produce a miss")
        self.assertEqual(result.misses, 1)

    def test_case_insensitive_keyword_that_differs_only_in_case_still_hits(self):
        # README.MD (uppercase) appears in the body; entry uses readme.md (lowercase)
        golden = copy.deepcopy(self.golden)
        for e in golden["entries"]:
            if e["pr_id"] == "node-skeleton#2" and e["path"] == "README.md" and e["rule_id"] is None:
                e["signature"] = e["signature"] + ["README.MD"]
                break
        rows = self.rows
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertEqual(result.accepted_hits, 42, "uppercase variant of existing keyword must still match")


# ----------------------------------------------------------------------
# AC10: rejected entry is a precision penalty
# ----------------------------------------------------------------------
class TestRejectedEntryIsAPrecisionPenalty(unittest.TestCase):
    """AC10: a matched rejected entry counts against precision, not as gap candidate."""

    def test_rejected_tts_entry_reduces_precision(self):
        golden = copy.deepcopy(load_golden())
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        # Flip tts-mcp#20 entry to rejected
        for e in golden["entries"]:
            if e["pr_id"] == "tts-mcp#20":
                e["state"] = "rejected"
                tts_entry = e
                break
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertEqual(result.accepted_in_scope, 41)
        self.assertEqual(result.accepted_hits, 41)
        self.assertEqual(result.matched_rejected, 1)
        self.assertEqual(result.gap_candidates, (), "matched rejected entry is NOT a gap candidate")
        self.assertEqual(result.recall, "1.000")
        self.assertEqual(result.precision, "0.976")
        # Pin the mechanism: the pair still matches
        tts_finding = None
        for row in rows:
            if row["pr_id"] == "tts-mcp#20":
                for f in row.get("findings") or []:
                    tts_finding = f
        self.assertTrue(
            run.finding_matches_entry(tts_entry, tts_finding),
            "tts finding still matches its entry",
        )


# ----------------------------------------------------------------------
# AC11: unreviewed entry is excluded from both ratios
# ----------------------------------------------------------------------
class TestUnreviewedEntryIsExcludedFromBothRatios(unittest.TestCase):
    """AC11: unreviewed entries excluded from numerator/denominator, not gap candidates."""

    def test_unreviewed_tts_entry_excluded_from_ratios(self):
        golden = copy.deepcopy(load_golden())
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        for e in golden["entries"]:
            if e["pr_id"] == "tts-mcp#20":
                e["state"] = "unreviewed"
                break
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertEqual(result.accepted_in_scope, 41)
        self.assertEqual(result.accepted_hits, 41)
        self.assertEqual(result.matched_rejected, 0)
        self.assertEqual(result.excluded_unreviewed, 1)
        self.assertEqual(result.gap_candidates, ())
        self.assertEqual(result.recall, "1.000")
        self.assertEqual(result.precision, "1.000")


# ----------------------------------------------------------------------
# AC13: gap candidates are NOT precision failures
# ----------------------------------------------------------------------
class TestGapCandidatesAreNotPrecisionFailures(unittest.TestCase):
    """AC13: unmatched findings are gap-triage candidates, not precision penalties."""

    def test_run3_gap_candidates_and_precision_unchanged(self):
        # Run 3 = 3rd row per PR in the 4runs slice
        golden = load_golden()
        all_rows = load_slice("ledger-sonnet-medium-short-4runs.jsonl")
        from collections import Counter
        counter = Counter()
        run3_rows = []
        for row in all_rows:
            pr_id = row["pr_id"]
            counter[pr_id] += 1
            if counter[pr_id] == 3:
                run3_rows.append(row)
        self.assertEqual(len(run3_rows), 5, "run 3 must cover all 5 PRs")
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in run3_rows})
        findings = run.iter_findings(run3_rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertEqual(len(result.gap_candidates), 3, "run 3 must have 3 gap candidates")
        for gc in result.gap_candidates:
            self.assertIn("pr_id", gc)
            self.assertIn("path", gc)
            self.assertIn("line", gc)
            self.assertIn("body", gc)
        self.assertEqual(result.precision, "1.000", "precision unchanged by gap candidates")

    def test_apt_key_finding_is_gap_candidate_in_all_four_runs(self):
        golden = load_golden()
        all_rows = load_slice("ledger-sonnet-medium-short-4runs.jsonl")
        # Collect run lines for apt-key finding in .github/workflows/ci.yml
        apt_key_lines = []
        from collections import Counter
        counter = Counter()
        for row in all_rows:
            pr_id = row["pr_id"]
            counter[pr_id] += 1
            for f in row.get("findings") or []:
                if f["path"] == ".github/workflows/ci.yml" and "apt-key" in (f.get("body") or "").lower():
                    apt_key_lines.append((counter[pr_id], f.get("line")))
        self.assertEqual(
            len(apt_key_lines), 4,
            f"apt-key finding must appear in all 4 runs, got: {apt_key_lines}",
        )
        # Lines: 13, 29, 9, 27 — one per run
        run_lines = sorted(apt_key_lines)
        self.assertEqual([line for _, line in run_lines], [13, 29, 9, 27])


# ----------------------------------------------------------------------
# AC20: scorer does not require a path extension
# ----------------------------------------------------------------------
class TestScorerDoesNotRequireAPathExtension(unittest.TestCase):
    """AC20: extensionless path matches like any other; no dot gate inherited from harvester."""

    def test_extensionless_path_matches(self):
        golden = copy.deepcopy(load_golden())
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        golden["entries"].append({
            "pr_id": "tts-mcp#20",
            "path": "Dockerfile",
            "signature": ["healthcheck"],
            "rule_id": None,
            "state": "accepted",
            "line_when_seen": 4,
            "excerpt": "",
        })
        # Add a synthetic finding for Dockerfile with healthcheck in body
        for row in rows:
            if row["pr_id"] == "tts-mcp#20":
                row["findings"].append({
                    "path": "Dockerfile",
                    "line": 4,
                    "body": "HEALTHCHECK instruction missing",
                    "rule_id": None,
                })
                break
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        expected = run.ScoreResult(
            entries_in_scope=43,
            accepted_in_scope=43,
            accepted_hits=43,
            misses=0,
            matched_rejected=0,
            excluded_unreviewed=0,
            findings=43,
            gap_candidates=(),
            recall="1.000",
            precision="1.000",
        )
        self.assertEqual(result, expected)
        self.assertTrue(
            run.finding_matches_entry(
                {"pr_id": "tts-mcp#20", "path": "Dockerfile", "signature": ["healthcheck"], "rule_id": None, "state": "accepted"},
                {"pr_id": "tts-mcp#20", "path": "Dockerfile", "line": 4, "body": "HEALTHCHECK instruction missing", "rule_id": None},
            )
        )


# ----------------------------------------------------------------------
# Ratio rendering
# ----------------------------------------------------------------------
class TestRatioRenderingIsFrozen(unittest.TestCase):
    """format_ratio rendering is frozen at three decimals or 'n/a'."""

    def test_two_over_42_renders_0_048(self):
        self.assertEqual(run.format_ratio(2, 42), "0.048")

    def test_zero_over_42_renders_0_000(self):
        self.assertEqual(run.format_ratio(0, 42), "0.000")

    def test_zero_over_0_renders_n_a(self):
        self.assertEqual(run.format_ratio(0, 0), "n/a")
        self.assertEqual(run.format_ratio(0, 0), run.RATIO_NA)

    def test_41_over_42_renders_0_976(self):
        self.assertEqual(run.format_ratio(41, 42), "0.976")


# ----------------------------------------------------------------------
# Golden set is not mutated by scoring
# ----------------------------------------------------------------------
class TestGoldenSetIsNotMutatedByScoring(unittest.TestCase):
    """Spec Constraints: frozen input — scoring must not mutate golden.json or the ledger."""

    def test_golden_json_sha256_unchanged(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        before = hashlib.sha256((GOLDEN_FIXTURE).read_bytes()).hexdigest()
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        run.score_findings(entries=entries, findings=findings)
        after = hashlib.sha256((GOLDEN_FIXTURE).read_bytes()).hexdigest()
        self.assertEqual(before, after, "golden.json must not be mutated by scoring")

    def test_entries_list_not_mutated(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        entries_snapshot = copy.deepcopy(entries)
        findings = run.iter_findings(rows)
        run.score_findings(entries=entries, findings=findings)
        self.assertEqual(entries, entries_snapshot, "entries list must not be mutated")

    def test_findings_not_mutated(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        findings = run.iter_findings(rows)
        findings_snapshot = copy.deepcopy(findings)
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        run.score_findings(entries=entries, findings=findings)
        self.assertEqual(findings, findings_snapshot, "findings list must not be mutated")


# ----------------------------------------------------------------------
# Defensive branches: no crash on None/missing body or unknown state
# ----------------------------------------------------------------------
class TestDefensiveBranches(unittest.TestCase):
    """Requirement 8: defensive handling for None/missing body and unknown state."""

    def _find_node_skeleton_readme_finding(self, rows):
        """Find node-skeleton#2's README.md finding (rule_id null — uses body match)."""
        for row in rows:
            if row["pr_id"] == "node-skeleton#2":
                for f in row.get("findings") or []:
                    if f["path"] == "README.md":
                        return f
        self.fail("node-skeleton#2 README.md finding not found")

    def test_none_body_does_not_raise(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        finding = self._find_node_skeleton_readme_finding(rows)
        finding["body"] = None
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        # Must not raise
        result = run.score_findings(entries=entries, findings=findings)
        self.assertGreater(len(result.gap_candidates), 0, "body=None finding must become a gap candidate")

    def test_missing_body_key_does_not_raise(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        finding = self._find_node_skeleton_readme_finding(rows)
        del finding["body"]
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        self.assertGreater(len(result.gap_candidates), 0, "finding with missing body must become a gap candidate")

    def test_unknown_state_not_counted_in_accepted_rejected_or_unreviewed(self):
        golden = copy.deepcopy(load_golden())
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        # Set one entry's state to bogus
        golden["entries"][0]["state"] = "bogus"
        entries = run.entries_in_scope(golden, {r["pr_id"] for r in rows})
        findings = run.iter_findings(rows)
        result = run.score_findings(entries=entries, findings=findings)
        # Bogus state counted in entries_in_scope but none of the tallies
        self.assertEqual(result.entries_in_scope, 42)
        self.assertEqual(
            result.accepted_in_scope + result.matched_rejected + result.excluded_unreviewed,
            41,
            "bogus state counted in entries_in_scope but in none of the three tallies",
        )


# ----------------------------------------------------------------------
# AC4: per-PR breakdown for the baseline
# ----------------------------------------------------------------------
class TestBaselinePerPrBreakdown(unittest.TestCase):
    """AC4: baseline slice scored as one config produces exact per-PR table."""

    def test_per_pr_breakdown_matches_ac4_table(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        self.assertEqual(len(cfg.runs), 1)
        run_score = cfg.runs[0]

        observed = [
            (p.pr_id, p.entries_in_scope, p.hits, p.misses,
             p.findings, p.gap_candidates, p.duration_seconds)
            for p in run_score.per_pr
        ]
        expected = [
            ("tts-mcp#20",                1,  1, 0,  1, 0, 420),
            ("github-pr-review-agent#11", 13, 13, 0, 13, 0, 690),
            ("quant#109",                 6,  6, 0,  6, 0, 268),
            ("node-skeleton#2",           10, 10, 0, 10, 0, 686),
            ("python-skeleton#3",         12, 12, 0, 12, 0, 469),
        ]
        self.assertEqual(
            observed,
            expected,
            f"per-PR table mismatch. Observed:\n" +
            "\n".join(str(r) for r in observed),
        )

    def test_wall_time_uses_unrounded_sum(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        run_score = cfg.runs[0]
        self.assertEqual(
            run_score.wall_time_seconds,
            golden["baseline"]["wall_time_seconds"],
        )
        # Summing the rounded per-PR column gives 2533; using round of the
        # unrounded sum gives 2534.  This assertion pins the correct method.
        self.assertEqual(run_score.wall_time_seconds, 2534)

    def test_config_identity_pinned_by_value(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        run_score = cfg.runs[0]
        self.assertEqual(
            (cfg.config_hash, cfg.model, cfg.effort, cfg.mode,
             cfg.rules_commands_hash, cfg.prs_version, cfg.runner_versions, cfg.rows_skipped),
            ("cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b",
             "opus", "xhigh", "full",
             "ecc803331f860b845a6a1b8a103e889bce02520e8cc04ea88102de74c8d5600d",
             "dev-1", ("1",), 0),
        )
        self.assertEqual(run_score.span_start, min(r["started_at"] for r in rows))
        self.assertEqual(run_score.span_end, max(r["started_at"] for r in rows))
        self.assertNotEqual(run_score.span_start, run_score.span_end)


# ----------------------------------------------------------------------
# AC5: four-run slice chunks into exactly four runs
# ----------------------------------------------------------------------
class TestFourRunSliceChunksIntoFourRuns(unittest.TestCase):
    """AC5: four-run slice produces exactly four complete runs with exact per-run table."""

    def test_four_runs_produce_exact_ac5_table(self):
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-4runs.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        self.assertEqual(len(cfg.runs), 4)
        for r in cfg.runs:
            self.assertTrue(r.complete, f"run {r.index} should be complete")
            self.assertEqual(len(r.pr_ids), 5)

        observed = [
            (r.score.findings, r.score.accepted_hits, r.score.misses,
             r.score.matched_rejected, len(r.score.gap_candidates),
             r.score.recall, r.score.precision)
            for r in cfg.runs
        ]
        expected = [
            (3, 2, 40, 0, 1, "0.048", "1.000"),
            (2, 1, 41, 0, 1, "0.024", "1.000"),
            (5, 2, 40, 0, 3, "0.048", "1.000"),
            (6, 4, 38, 0, 2, "0.095", "1.000"),
        ]
        self.assertEqual(observed, expected)

    def test_zero_denominator_precision_renders_the_n_a_literal(self):
        """A run that matched nothing renders precision as the literal 'n/a'.

        This used to assert against run 4 of the four-run slice, which matched
        zero entries under `path:line` signatures.  The 2026-08-10 re-key gave
        it 4 hits, so it is no longer a zero-denominator case and pinning it
        here would have tested the bug rather than the formatting.  The partial
        slice still carries genuine zero-match runs; the invariant under test
        (0/0 is never rendered as 0.000) is unchanged.
        """
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-partial.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        zero_match = [r for r in cfg.runs if r.score.accepted_hits == 0]
        self.assertTrue(zero_match, "expected at least one run matching nothing")
        for r in zero_match:
            self.assertEqual(r.score.precision, run.RATIO_NA)
            self.assertEqual(r.score.precision, "n/a")


# ----------------------------------------------------------------------
# AC6: run chunking ignores timestamps
# ----------------------------------------------------------------------
class TestRunChunkingIgnoresTimestamps(unittest.TestCase):
    """AC6: chunking is a function of file order only, never of started_at."""

    def test_identical_timestamps_preserve_run_count_and_table(self):
        # In the real ledger, the boundary between run 2 and run 3 is 48 seconds
        # while gaps inside runs 1, 2 and 4 reach 140, 128 and 110 seconds.
        # No time threshold separates them and this test is what stops a
        # gap-keyed chunker from passing AC5 by coincidence.
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-4runs.jsonl")
        rows_copy = copy.deepcopy(rows)
        for r in rows_copy:
            r["started_at"] = "2026-01-01T00:00:00+00:00"

        cfg = run.score_config(rows=rows_copy, golden=golden)
        self.assertEqual(len(cfg.runs), 4)
        for r in cfg.runs:
            self.assertTrue(r.complete)
            self.assertEqual(len(r.pr_ids), 5)

        observed = [
            (r.score.findings, r.score.accepted_hits, r.score.misses,
             r.score.matched_rejected, len(r.score.gap_candidates),
             r.score.recall, r.score.precision)
            for r in cfg.runs
        ]
        expected = [
            (3, 2, 40, 0, 1, "0.048", "1.000"),
            (2, 1, 41, 0, 1, "0.024", "1.000"),
            (5, 2, 40, 0, 3, "0.048", "1.000"),
            (6, 4, 38, 0, 2, "0.095", "1.000"),
        ]
        self.assertEqual(observed, expected)

    def test_reversed_file_order_preserves_chunk_boundaries(self):
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-4runs.jsonl")
        reversed_rows = list(reversed(rows))

        cfg = run.score_config(rows=reversed_rows, golden=golden)
        self.assertEqual(len(cfg.runs), 4)

        # In the original file: run k has each PR's k-th occurrence.
        # In the reversed file: run k has each PR's (5-k+1)-th occurrence.
        # Both have 5 PRs per run.  Chunking is a function of file order alone,
        # so reversing the file does NOT change which rows belong to which run —
        # only the occurrence index within each run changes.
        original_runs = run.chunk_runs(rows)
        reversed_runs = run.chunk_runs(reversed_rows)
        for i, (orig, rev) in enumerate(zip(original_runs, reversed_runs), 1):
            self.assertEqual(len(orig), 5, f"run {i} should have 5 rows")
            self.assertEqual(len(rev), 5, f"run {i} should have 5 rows")
            self.assertEqual(
                {r["pr_id"] for r in orig},
                {r["pr_id"] for r in rev},
                f"run {i} should cover the same 5 PRs regardless of file order",
            )


# ----------------------------------------------------------------------
# AC30: partial runs are labelled and scoped down
# ----------------------------------------------------------------------
class TestPartialRunsAreLabelledAndScopedDown(unittest.TestCase):
    """AC30: partial runs are labelled and scoped to the PRs they cover."""

    def test_partial_slice_produces_eight_runs_with_correct_coverage(self):
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-partial.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        self.assertEqual(len(cfg.runs), 8)
        self.assertEqual(
            [len(r.pr_ids) for r in cfg.runs],
            [5, 5, 5, 5, 5, 3, 3, 1],
        )
        self.assertEqual(
            [r.complete for r in cfg.runs],
            [True, True, True, True, True, False, False, False],
        )

    def test_partial_runs_match_ac30_table(self):
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-partial.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)

        observed = [
            (len(r.pr_ids), r.score.entries_in_scope, r.score.findings,
             r.score.accepted_hits, r.score.misses,
             len(r.score.gap_candidates), r.score.recall, r.score.precision)
            for r in cfg.runs
        ]
        # Re-pinned 2026-08-10 with the semantic-signature golden set.  Every
        # movement is a hit gained and a gap candidate lost: these sonnet runs
        # described the same issues as the Opus baseline but anchored them at
        # different lines, so under `path:line` keys they scored zero credit.
        # Runs 4 and 5 went 0 -> 1 hit, which is why their precision is no
        # longer the `n/a` of a run that matched nothing at all.
        expected = [
            (5, 42, 6, 3, 39, 3, "0.071", "1.000"),
            (5, 42, 9, 2, 40, 7, "0.048", "1.000"),
            (5, 42, 9, 2, 40, 7, "0.048", "1.000"),
            (5, 42, 5, 1, 41, 4, "0.024", "1.000"),
            (5, 42, 1, 1, 41, 0, "0.024", "1.000"),
            (3, 24, 1, 0, 24, 1, "0.000", "n/a"),
            (3, 24, 1, 0, 24, 1, "0.000", "n/a"),
            (1,  1, 0, 0,  1, 0, "0.000", "n/a"),
        ]
        self.assertEqual(observed, expected)


# ----------------------------------------------------------------------
# AC12: all-unreviewed golden set scores without dividing
# ----------------------------------------------------------------------
class TestAllUnreviewedGoldenSetScoresWithoutDividing(unittest.TestCase):
    """AC12: scoring against an all-unreviewed golden set renders n/a for both ratios."""

    def test_all_unreviewed_produces_n_a_for_both_ratios(self):
        golden = copy.deepcopy(load_golden())
        for e in golden["entries"]:
            e["state"] = "unreviewed"
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        # No try block — a ZeroDivisionError here fails the test
        cfg = run.score_config(rows=rows, golden=golden)
        score = cfg.runs[0].score
        self.assertEqual(score.accepted_in_scope, 0)
        self.assertEqual(score.accepted_hits, 0)
        self.assertEqual(score.misses, 0)
        self.assertEqual(score.matched_rejected, 0)
        self.assertEqual(score.gap_candidates, ())
        self.assertEqual(score.excluded_unreviewed, 42)
        self.assertEqual(score.recall, run.RATIO_NA)
        self.assertEqual(score.recall, "n/a")
        self.assertEqual(score.precision, run.RATIO_NA)
        self.assertEqual(score.precision, "n/a")


# ----------------------------------------------------------------------
# Test runner_version set is collected, not sampled
# ----------------------------------------------------------------------
class TestRunnerVersionSetIsCollectedNotSampled(unittest.TestCase):
    """runner_versions is the set of distinct values, not the first row's."""

    def test_mixed_runner_versions_collected(self):
        golden = load_golden()
        rows = copy.deepcopy(load_slice("ledger-baseline-opus-xhigh-full.jsonl"))
        rows[0]["runner_version"] = "2"
        cfg = run.score_config(rows=rows, golden=golden)
        self.assertEqual(cfg.runner_versions, ("1", "2"))


# ----------------------------------------------------------------------
# Test defensive guards are reachable
# ----------------------------------------------------------------------
class TestDefensiveGuardsAreReachable(unittest.TestCase):
    """Requirement 7: defensive branches for missing duration_seconds and started_at."""

    def test_missing_duration_seconds_guards(self):
        golden = load_golden()
        rows = copy.deepcopy(load_slice("ledger-baseline-opus-xhigh-full.jsonl"))
        # Delete duration_seconds from quant#109 row
        for r in rows:
            if r["pr_id"] == "quant#109":
                del r["duration_seconds"]
                break
        cfg = run.score_config(rows=rows, golden=golden)
        run_score = cfg.runs[0]
        # Wall time: round(2533.923 - 268.299) = round(2265.624) = 2266
        self.assertEqual(run_score.wall_time_seconds, 2266)
        # The corresponding PrBreakdown has 0 duration
        quant_pr = next(p for p in run_score.per_pr if p.pr_id == "quant#109")
        self.assertEqual(quant_pr.duration_seconds, 0)

    def test_missing_started_at_on_every_row(self):
        golden = load_golden()
        rows = copy.deepcopy(load_slice("ledger-baseline-opus-xhigh-full.jsonl"))
        for r in rows:
            del r["started_at"]
        cfg = run.score_config(rows=rows, golden=golden)
        run_score = cfg.runs[0]
        self.assertEqual(run_score.span_start, "")
        self.assertEqual(run_score.span_end, "")
        # Numbers unchanged — spans are display only
        self.assertEqual(run_score.wall_time_seconds, 2534)
        observed = [
            (p.pr_id, p.entries_in_scope, p.hits, p.misses,
             p.findings, p.gap_candidates, p.duration_seconds)
            for p in run_score.per_pr
        ]
        expected = [
            ("tts-mcp#20",                1,  1, 0,  1, 0, 420),
            ("github-pr-review-agent#11", 13, 13, 0, 13, 0, 690),
            ("quant#109",                 6,  6, 0,  6, 0, 268),
            ("node-skeleton#2",           10, 10, 0, 10, 0, 686),
            ("python-skeleton#3",         12, 12, 0, 12, 0, 469),
        ]
        self.assertEqual(observed, expected)

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(run.chunk_runs([]), [])


# ----------------------------------------------------------------------
# Report rendering tests — spec 006 prompt 3
# ----------------------------------------------------------------------


def parse_table(page_text, heading):
    """Return the rows of the markdown table under `heading` as lists of cell strings."""
    lines = page_text.splitlines()
    # Find heading
    heading_idx = None
    for i, line in enumerate(lines):
        if line == heading:
            heading_idx = i
            break
    if heading_idx is None:
        raise AssertionError(f"Heading {heading!r} not found in page")
    # Collect |...| lines after heading until a non-| line
    rows = []
    for line in lines[heading_idx + 1:]:
        if not line.strip().startswith("|"):
            break
        # Split on unescaped |
        cells = re.split(r"(?<!\\)\|", line)
        cells = [c.replace("\\|", "|") for c in cells]
        cells = [c.strip() for c in cells]
        # Strip leading and trailing empty cells (from leading | and trailing |)
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        rows.append(cells)
    # Drop header and --- separator rows
    return rows[2:]


class TestReportPageLocationAndSections(unittest.TestCase):
    """AC15: page written to expected path with exact four section headings."""

    def test_filename_is_full_64_char_hash(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            ver = run.coding_plugin_version(BENCH_DIR.parent)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version=ver
            )
            self.assertEqual(
                path.name,
                "cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b.md",
            )

    def test_exact_four_headings_in_order(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            ver = run.coding_plugin_version(BENCH_DIR.parent)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version=ver
            )
            text = path.read_text()
            headings = [l for l in text.splitlines() if l.startswith("## ")]
            self.assertEqual(
                headings,
                ["## Configuration", "## Runs", "## Per-PR", "## Gap-triage candidates"],
            )


class TestConfigurationBlockPinsBothVersions(unittest.TestCase):
    """AC15: Configuration block pins both coding version lines by exact prefix."""

    def test_all_twelve_fields_present_on_own_lines(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        plugin_version = json.loads(
            (BENCH_DIR.parent / ".claude-plugin" / "plugin.json").read_text()
        )["version"]
        ver = run.coding_plugin_version(BENCH_DIR.parent)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version=ver
            )
            text = path.read_text()
            lines = text.splitlines()
            # Twelve required fields, each on its own line
            required = [
                "- model: opus",
                "- effort: xhigh",
                "- mode: full",
                f"- config_hash: cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b",
                "- rules_commands_hash: ecc803331f860b845a6a1b8a103e889bce02520e8cc04ea88102de74c8d5600d",
                "- prs_version: dev-1",
                f"- coding version: {plugin_version}",
                "- golden baseline coding version: v0.35.6",
                "- golden version: golden-dev-1",
                "- runner_version: 1",
                "- rows skipped: 0",
                "- cost: not recorded — the ledger carries no cost field.",
            ]
            for field in required:
                self.assertIn(
                    field, lines,
                    f"Configuration line {field!r} not found",
                )
            # Coding version line equals plugin.json version, not 'unavailable'
            coding_line = next(l for l in lines if l.startswith("- coding version: "))
            self.assertEqual(coding_line, f"- coding version: {plugin_version}")
            self.assertNotIn("unavailable", coding_line)
            # Golden baseline starts with 'v'
            gb_line = next(l for l in lines if l.startswith("- golden baseline coding version: "))
            self.assertTrue(
                gb_line.endswith("v0.35.6"),
                gb_line,
            )
            # Golden version equals golden["version"]
            gv_line = next(l for l in lines if l.startswith("- golden version: "))
            self.assertEqual(gv_line, "- golden version: golden-dev-1")

    def test_coding_plugin_version_returns_unavailable_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            ver = run.coding_plugin_version(root)
            self.assertEqual(ver, "unavailable")

    def test_coding_plugin_version_returns_unavailable_when_json_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            plugin_dir = root / ".claude-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "plugin.json").write_text("{not json", encoding="utf-8")
            ver = run.coding_plugin_version(root)
            self.assertEqual(ver, "unavailable")

    def test_coding_plugin_version_returns_unavailable_when_no_version_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            plugin_dir = root / ".claude-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "plugin.json").write_text('{"name":"test"}', encoding="utf-8")
            ver = run.coding_plugin_version(root)
            self.assertEqual(ver, "unavailable")

    def test_render_still_produces_full_page_when_plugin_version_unavailable(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir,
                config_score=cfg,
                golden=golden,
                coding_version="unavailable",
            )
            text = path.read_text()
            headings = [l for l in text.splitlines() if l.startswith("## ")]
            self.assertEqual(
                headings,
                ["## Configuration", "## Runs", "## Per-PR", "## Gap-triage candidates"],
            )


class TestRunnerVersionLineListsTheWholeSet(unittest.TestCase):
    """AC15: runner_version line lists the full set, not the first row's value."""

    def test_mixed_versions_listed(self):
        golden = load_golden()
        rows = copy.deepcopy(load_slice("ledger-baseline-opus-xhigh-full.jsonl"))
        rows[0]["runner_version"] = "2"
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            text = path.read_text()
            rv_line = next(l for l in text.splitlines() if l.startswith("- runner_version: "))
            self.assertIn("1", rv_line)
            self.assertIn("2", rv_line)


class TestPerPrTableIsRenderedFromTheResult(unittest.TestCase):
    """AC15: Per-PR table cells match the result object's PrBreakdown fields."""

    def test_per_pr_table_cells_match_prbreakdown(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            text = path.read_text()
        table = parse_table(text, "## Per-PR")
        self.assertEqual(len(table), 5)
        pr_ids = [row[1] for row in table]
        expected_pr_ids = [
            "tts-mcp#20",
            "github-pr-review-agent#11",
            "quant#109",
            "node-skeleton#2",
            "python-skeleton#3",
        ]
        self.assertEqual(pr_ids, expected_pr_ids)
        # Compare each cell against the result object, not just literals
        for row in table:
            pr_id = row[1]
            run_score = cfg.runs[0]
            pr_breakdown = next(p for p in run_score.per_pr if p.pr_id == pr_id)
            self.assertEqual(int(row[2]), pr_breakdown.entries_in_scope)
            self.assertEqual(int(row[3]), pr_breakdown.hits)
            self.assertEqual(int(row[4]), pr_breakdown.misses)
            self.assertEqual(int(row[5]), pr_breakdown.findings)
            self.assertEqual(int(row[6]), pr_breakdown.gap_candidates)
            self.assertEqual(int(row[7]), pr_breakdown.unattributable)
            expected_absent = (
                ", ".join(pr_breakdown.missing_sections)
                if pr_breakdown.missing_sections else "—"
            )
            self.assertEqual(row[8], expected_absent)
            self.assertEqual(int(row[9]), pr_breakdown.duration_seconds)


class TestRunsTableIsRenderedFromTheResult(unittest.TestCase):
    """AC31: Runs table read back from rendered page matches result object."""

    def test_four_run_table_cells_match_result(self):
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-4runs.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            text = path.read_text()
        table = parse_table(text, "## Runs")
        self.assertEqual(len(table), 4)
        # Compare each row against the result object
        for row, run_score in zip(table, cfg.runs):
            self.assertEqual(int(row[0]), run_score.index)
            # span: "span_start … span_end"
            self.assertEqual(row[1], f"{run_score.span_start} … {run_score.span_end}")
            self.assertEqual(
                row[2], f"{len(run_score.pr_ids)}/{run_score.expected_pr_count}"
            )
            self.assertEqual(row[3], "complete" if run_score.complete else "partial")
            r = run_score.score
            self.assertEqual(int(row[4]), r.entries_in_scope)
            self.assertEqual(int(row[5]), r.findings)
            self.assertEqual(int(row[6]), r.accepted_hits)
            self.assertEqual(int(row[7]), r.misses)
            self.assertEqual(int(row[8]), r.matched_rejected)
            self.assertEqual(int(row[9]), len(r.gap_candidates))
            self.assertEqual(row[10], r.recall)
            self.assertEqual(row[11], r.precision)
            self.assertEqual(int(row[12]), run_score.wall_time_seconds)
        # The loop above already asserts row[11] == r.precision for every run.
        # A spot-check pinning run 4 to 'n/a' used to sit here; it described a
        # run that matched nothing, which the 2026-08-10 re-key fixed.  The
        # 'n/a' literal itself is pinned in
        # TestFourRunSliceChunksIntoFourRuns.test_zero_denominator_precision_renders_the_n_a_literal.

    def test_partial_table_cells_match_result(self):
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-partial.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            text = path.read_text()
        table = parse_table(text, "## Runs")
        self.assertEqual(len(table), 8)
        complete_flags = [row[3] for row in table]
        self.assertEqual(complete_flags[:5], ["complete"] * 5)
        self.assertEqual(complete_flags[5:], ["partial"] * 3)
        # Compare entries_in_scope and span for all rows
        for row, run_score in zip(table, cfg.runs):
            self.assertEqual(int(row[4]), run_score.score.entries_in_scope)
            self.assertEqual(row[1], f"{run_score.span_start} … {run_score.span_end}")


class TestGapTriageSectionCarriesItsSentenceAndBodies(unittest.TestCase):
    """AC13/AC15: gap-triage section has sentence, run-3 candidates rendered verbatim."""

    def test_sentence_present_even_when_empty(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            text = path.read_text()
        self.assertIn("not a precision failure", text)
        self.assertIn("## Gap-triage candidates", text)

    def test_run3_gap_candidate_bodies_verbatim(self):
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-4runs.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        run3_score = cfg.runs[2]  # index 2 = run 3
        self.assertEqual(
            len(run3_score.score.gap_candidates), 3,
        )
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            text = path.read_text()
        for gc in run3_score.score.gap_candidates:
            self.assertIn(gc["body"], text, f"body not found verbatim: {gc['body'][:60]}")
            self.assertIn(gc["pr_id"], text)
            self.assertIn(gc["path"], text)
            line_str = f":{gc['line']}" if gc["line"] is not None else ""
            self.assertIn(line_str, text)


class TestBothCaveatsAppearOnEveryPage(unittest.TestCase):
    """AC15: both mandated caveat paragraphs appear on every page."""

    def _get_page(self, rows_name):
        golden = load_golden()
        rows = load_slice(rows_name)
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            return path.read_text()

    def test_not_yet_a_result_appears_on_baseline(self):
        text = self._get_page("ledger-baseline-opus-xhigh-full.jsonl")
        self.assertIn("not yet a result", text)
        # Also a real paragraph, not just a keyword
        para = next(p for p in text.split("\n\n") if "not yet a result" in p)
        self.assertIn("rejected", para)

    def test_line_reference_caveat_appears_on_baseline(self):
        """The caveat now reports the CLEARED state, and must keep doing so.

        It used to read "36 of the 42 signatures embed a line reference", which
        was the honest description of a set keyed on `path:line`.  Since the
        2026-08-10 re-key no signature carries one, so the caveat flips to the
        branch that says recall measures issue detection.  Asserting the cleared
        wording here is what turns this caveat into a regression detector: a
        future adjudication that reintroduces a `path:line` key fails this test
        rather than silently degrading recall back into line-citation matching.
        """
        text = self._get_page("ledger-baseline-opus-xhigh-full.jsonl")
        self.assertIn("No signature embeds a line reference", text)
        self.assertIn("measures issue detection", text)
        self.assertNotIn("embed a line reference, so a", text)

    def test_both_caveats_appear_on_fourrun_page(self):
        text = self._get_page("ledger-sonnet-medium-short-4runs.jsonl")
        self.assertIn("not yet a result", text)
        self.assertIn("No signature embeds a line reference", text)
        self.assertIn("measures issue detection", text)


class TestScoringIsDeterministicAndCarriesNoWallClock(unittest.TestCase):
    """AC14: re-scoring unchanged ledger produces byte-identical file."""

    def test_deterministic_across_two_directories(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            pa = run.write_report(
                reports_dir=pathlib.Path(a), config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            pb = run.write_report(
                reports_dir=pathlib.Path(b), config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            self.assertTrue(
                filecmp.cmp(pa, pb, shallow=False),
                "two writes to different directories must be byte-identical",
            )

    def test_deterministic_on_same_path_overwrite(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            p1 = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            p2 = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            self.assertTrue(
                filecmp.cmp(p1, p2, shallow=False),
                "overwrite of same path must be byte-identical",
            )

    def test_no_wall_clock_in_page(self):
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-4runs.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            text = path.read_text()
        hits = re.findall(r"(?i)generated (at|on)|generated:|report date", text)
        self.assertEqual(hits, [], f"wall-clock phrases found: {hits}")

    def test_three_decimal_recall_pinned_from_rendered_page(self):
        golden = load_golden()
        rows = load_slice("ledger-sonnet-medium-short-4runs.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            text = path.read_text()
        table = parse_table(text, "## Runs")
        run1_recall = table[0][10]
        self.assertEqual(run1_recall, "0.048")
        self.assertEqual(run1_recall, format(2 / 42, ".3f"))


class TestAllUnreviewedGoldenSetStillRenders(unittest.TestCase):
    """AC12: scoring all-unreviewed set renders n/a for both ratios without ZeroDivisionError."""

    def test_all_unreviewed_renders_n_a(self):
        golden = copy.deepcopy(load_golden())
        for e in golden["entries"]:
            e["state"] = "unreviewed"
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            path = run.write_report(
                reports_dir=out_dir, config_score=cfg, golden=golden, coding_version="0.35.7"
            )
            text = path.read_text()
        headings = [l for l in text.splitlines() if l.startswith("## ")]
        self.assertEqual(
            headings,
            ["## Configuration", "## Runs", "## Per-PR", "## Gap-triage candidates"],
        )
        table = parse_table(text, "## Runs")
        self.assertEqual(table[0][10], "n/a")  # recall
        self.assertEqual(table[0][11], "n/a")  # precision


class TestConfigHashIsGatedBeforeBecomingAFilename(unittest.TestCase):
    """AC21: bad config_hash raises BenchError before any filesystem access."""

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            marker = root / "marker.txt"
            marker.touch()
            reports = root / "a" / "b" / "reports"
            reports.mkdir(parents=True)
            golden = load_golden()
            rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
            cfg = run.score_config(rows=rows, golden=golden)
            bad = dataclasses.replace(cfg, config_hash="../../etc/passwd")
            mtime = marker.stat().st_mtime
            try:
                run.write_report(reports_dir=reports, config_score=bad, golden=golden, coding_version="0.35.7")
                self.fail("traversal not rejected")
            except run.BenchError as err:
                self.assertIn("INVALID CONFIG HASH", str(err))
            newer = [
                p for p in reports.rglob("*")
                if p.stat().st_mtime > mtime
            ]
            self.assertEqual(newer, [], "no file written after rejection")

    def test_empty_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            marker = root / "marker.txt"
            marker.touch()
            reports = root / "a" / "b" / "reports"
            reports.mkdir(parents=True)
            golden = load_golden()
            rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
            cfg = run.score_config(rows=rows, golden=golden)
            bad = dataclasses.replace(cfg, config_hash="")
            mtime = marker.stat().st_mtime
            try:
                run.write_report(reports_dir=reports, config_score=bad, golden=golden, coding_version="0.35.7")
                self.fail("empty hash not rejected")
            except run.BenchError as err:
                self.assertIn("INVALID CONFIG HASH", str(err))
            newer = [p for p in reports.rglob("*") if p.stat().st_mtime > mtime]
            self.assertEqual(newer, [])

    def test_hash_with_slash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            marker = root / "marker.txt"
            marker.touch()
            reports = root / "a" / "b" / "reports"
            reports.mkdir(parents=True)
            golden = load_golden()
            rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
            cfg = run.score_config(rows=rows, golden=golden)
            bad = dataclasses.replace(cfg, config_hash="a" * 32 + "/" + "b" * 31)
            mtime = marker.stat().st_mtime
            try:
                run.write_report(reports_dir=reports, config_score=bad, golden=golden, coding_version="0.35.7")
                self.fail("hash with slash not rejected")
            except run.BenchError as err:
                self.assertIn("INVALID CONFIG HASH", str(err))
            newer = [p for p in reports.rglob("*") if p.stat().st_mtime > mtime]
            self.assertEqual(newer, [])

    def test_uppercase_hash_rejected(self):
        golden = load_golden()
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        cfg = run.score_config(rows=rows, golden=golden)
        bad = dataclasses.replace(cfg, config_hash="A" * 64)
        try:
            run.write_report(
                reports_dir=pathlib.Path("/tmp/does-not-exist"),
                config_score=bad,
                golden=golden,
                coding_version="0.35.7",
            )
            self.fail("uppercase hash not rejected")
        except run.BenchError as err:
            self.assertIn("INVALID CONFIG HASH", str(err))


# ----------------------------------------------------------------------
# Scoring integration tests — spec 006 prompt 4 (AC17, AC18, AC19, AC21, AC29, DB1)
# ----------------------------------------------------------------------


class TestScoringInvokesNoReviewAndMutatesNothing(unittest.TestCase):
    """AC17 — score mode must not invoke claude and must not mutate any input."""

    def test_score_mode_invokes_no_review(self):
        """`--score --golden` produces pages but counter file stays empty."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)

            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()
            counter_file = tmp / "counter.txt"
            bin_dir = tmp / "bin"
            bin_dir.mkdir()

            shutil.copy(
                str(BENCH_DIR / "testdata" / "ledger-baseline-opus-xhigh-full.jsonl"),
                results_dir / "results.jsonl",
            )

            testsupport.stub_claude(bin_dir, counter_file)

            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(results_dir),
                 "--reports-dir", str(reports_dir),
                 "--coding-repo", ".",
                 ],
                capture_output=True, text=True,
                env=testsupport.with_path(bin_dir),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            counter_text = (
                counter_file.read_text()
                if counter_file.exists()
                else ""
            )
            self.assertEqual(counter_text.strip(), "", "claude was invoked")

            # Ledger unchanged (sha256 + line count)
            ledger_path = results_dir / "results.jsonl"
            ledger_before_sha = hashlib.sha256(
                ledger_path.read_bytes()
            ).hexdigest()
            ledger_before_lines = sum(
                1 for line in ledger_path.read_text().splitlines()
                if line.strip()
            )

            testdata_before = {
                f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((BENCH_DIR / "testdata").iterdir())
                if f.is_file()
            }

            result2 = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(results_dir),
                 "--reports-dir", str(reports_dir),
                 "--coding-repo", ".",
                 ],
                capture_output=True, text=True,
                env=testsupport.with_path(bin_dir),
            )
            self.assertEqual(result2.returncode, 0)

            ledger_after_sha = hashlib.sha256(
                ledger_path.read_bytes()
            ).hexdigest()
            ledger_after_lines = sum(
                1 for line in ledger_path.read_text().splitlines()
                if line.strip()
            )
            self.assertEqual(ledger_before_sha, ledger_after_sha)
            self.assertEqual(ledger_before_lines, ledger_after_lines)

            # Golden set and testdata unchanged.  Compared by digest against a
            # snapshot taken before the scoring subprocess, the same way the
            # ledger is checked above.  This used to shell out to
            # `git diff --exit-code`, which reports the working tree rather than
            # what the subprocess did: any developer holding a legitimate
            # uncommitted fixture edit failed the test, and a mutation staged in
            # the index would have passed it.
            for rel, before in testdata_before.items():
                after = hashlib.sha256((BENCH_DIR / "testdata" / rel).read_bytes()).hexdigest()
                self.assertEqual(before, after, f"scoring mutated testdata/{rel}")

            # Exactly one page written
            pages = sorted(p.name for p in reports_dir.iterdir())
            self.assertEqual(
                pages,
                ["cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b.md"],
                pages,
            )


class TestPreconditionsFailBeforeAnyReview(unittest.TestCase):
    """AC18 — every precondition aborts before any review subprocess starts."""

    def _run_with_stub(self, argv, bin_dir):
        counter_file = bin_dir / "counter.txt"
        testsupport.stub_claude(bin_dir, counter_file)
        result = subprocess.run(
            [sys.executable, str(run.BENCH_DIR / "run.py")] + argv,
            capture_output=True, text=True,
            env=testsupport.with_path(bin_dir),
        )
        counter_text = (
            counter_file.read_text()
            if counter_file.exists()
            else ""
        )
        return result, counter_text

    def test_score_without_golden_exits_two(self):
        """--score without --golden exits 2 and stub was never invoked."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            counter_file = bin_dir / "counter.txt"
            testsupport.stub_claude(bin_dir, counter_file)
            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score", "--out-dir", str(tmp / "results")],
                capture_output=True, text=True,
                env=testsupport.with_path(bin_dir),
            )
            self.assertEqual(result.returncode, 2)
            # Plain message, no frozen literal required
            self.assertIn("--golden", result.stderr)
            try:
                self.assertEqual(counter_file.read_text().strip(), "")
            except FileNotFoundError:
                pass  # stub never ran — counter file was never created

    def test_score_with_malformed_golden_exits_two(self):
        """--score with a golden JSON missing required keys exits 2."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            bad_golden = tmp / "bad_golden.json"
            bad_golden.write_text(
                json.dumps({"entries": [], "match_rule": "", "states": {}}),
                encoding="utf-8",
            )
            result, counter = self._run_with_stub(
                ["--score", "--golden", str(bad_golden),
                 "--out-dir", str(tmp / "results")],
                bin_dir,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("INVALID GOLDEN SET", result.stderr)
            self.assertEqual(counter.strip(), "")

    def test_live_run_golden_version_mismatch_exits_two(self):
        """Live run whose manifest version differs from golden prs_version exits 2."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()

            repo_dir = tmp / "repo"
            testsupport.build_coding_repo(repo_dir)

            testsupport.build_verify_config_dir(
                tmp / ".claude-verify",
                repo_dir,
            )

            cache_root = tmp / "cache"
            manifest_path = testsupport.seed_one_pr_manifest(tmp, cache_root)
            manifest = json.loads(manifest_path.read_text())
            manifest["version"] = "other-version"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result, counter = self._run_with_stub(
                ["--golden", str(GOLDEN_FIXTURE),
                 "--model", "opus",
                 "--effort", "xhigh",
                 "--mode", "full",
                 "--manifest", str(manifest_path),
                 "--coding-repo", str(repo_dir),
                 "--out-dir", str(tmp / "results"),
                 ],
                bin_dir,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("GOLDEN VERSION MISMATCH", result.stderr)
            self.assertIn("other-version", result.stderr)
            self.assertIn("dev-1", result.stderr)
            self.assertEqual(counter.strip(), "")

    def test_score_with_identity_flags_exits_two(self):
        """--score --golden with --model/--effort/--mode exits 2."""
        for flag in ["--model", "--effort", "--mode"]:
            with self.subTest(flag=flag):
                with tempfile.TemporaryDirectory() as tmp:
                    tmp = pathlib.Path(tmp)
                    bin_dir = tmp / "bin"
                    bin_dir.mkdir()
                    counter_file = bin_dir / "counter.txt"
                    testsupport.stub_claude(bin_dir, counter_file)
                    result = subprocess.run(
                        [sys.executable, str(run.BENCH_DIR / "run.py"),
                         "--score",
                         "--golden", str(GOLDEN_FIXTURE),
                         flag, "opus",
                         "--out-dir", str(tmp / "results"),
                         ],
                        capture_output=True, text=True,
                        env=testsupport.with_path(bin_dir),
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("--model", result.stderr)
                    try:
                        self.assertEqual(counter_file.read_text().strip(), "")
                    except FileNotFoundError:
                        pass  # stub never ran


class TestScoreModeOverBadLedgerFailsLoudly(unittest.TestCase):
    """AC19 — corrupt ledger aborts with exit 2 and writes zero pages."""

    def test_missing_ledger_exits_two(self):
        """No results.jsonl → EMPTY LEDGER, zero pages."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            reports_dir = tmp / "reports"
            reports_dir.mkdir()
            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(tmp / "results"),
                 "--reports-dir", str(reports_dir),
                 ],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("EMPTY LEDGER", result.stderr)
            self.assertEqual(list(reports_dir.iterdir()), [])

    def test_zero_byte_ledger_exits_two(self):
        """Zero-byte results.jsonl → EMPTY LEDGER, zero pages."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()
            (results_dir / "results.jsonl").write_bytes(b"")
            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(results_dir),
                 "--reports-dir", str(reports_dir),
                 ],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("EMPTY LEDGER", result.stderr)
            self.assertEqual(list(reports_dir.iterdir()), [])

    def test_all_whitespace_ledger_exits_two(self):
        """All-whitespace results.jsonl → EMPTY LEDGER, zero pages."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()
            (results_dir / "results.jsonl").write_text("  \n\n  \n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(results_dir),
                 "--reports-dir", str(reports_dir),
                 ],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("EMPTY LEDGER", result.stderr)
            self.assertEqual(list(reports_dir.iterdir()), [])

    def test_corrupt_json_line_exits_two(self):
        """A non-JSON line at line 3 → CORRUPT LEDGER with line number."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()

            baseline = (
                pathlib.Path(str(BENCH_DIR / "testdata" / "ledger-baseline-opus-xhigh-full.jsonl"))
                .read_text()
                .splitlines()
            )
            baseline[2] = "{not json"
            ledger = results_dir / "results.jsonl"
            ledger.write_text("\n".join(baseline) + "\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(results_dir),
                 "--reports-dir", str(reports_dir),
                 ],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("CORRUPT LEDGER", result.stderr)
            self.assertIn(f"{ledger}:3:", result.stderr)
            self.assertNotIn(f"{ledger}:2:", result.stderr)
            self.assertNotIn(f"{ledger}:4:", result.stderr)
            self.assertEqual(list(reports_dir.iterdir()), [])

    def test_missing_required_field_exits_two(self):
        """A row missing config_hash → CORRUPT LEDGER with its line number."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()

            baseline = (
                pathlib.Path(str(BENCH_DIR / "testdata" / "ledger-baseline-opus-xhigh-full.jsonl"))
                .read_text()
                .splitlines()
            )
            bad_row = json.loads(baseline[2])
            del bad_row["config_hash"]
            baseline[2] = json.dumps(bad_row)
            ledger = results_dir / "results.jsonl"
            ledger.write_text("\n".join(baseline) + "\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(results_dir),
                 "--reports-dir", str(reports_dir),
                 ],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("CORRUPT LEDGER", result.stderr)
            self.assertIn(f"{ledger}:3:", result.stderr)
            self.assertEqual(list(reports_dir.iterdir()), [])


class TestRowsAgainstAnotherManifestAreSkippedPerRow(unittest.TestCase):
    """AC29 — per-row prs_version filter; per-config gate would write zero pages here."""

    def test_probe_fixture_writes_zero_pages_with_four_skips(self):
        """Probe ledger scored against real golden → 0 pages, 4 skip lines."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()

            shutil.copy(
                str(BENCH_DIR / "testdata" / "ledger-probe-configs-mixed-prs-version.jsonl"),
                results_dir / "results.jsonl",
            )

            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(results_dir),
                 "--reports-dir", str(reports_dir),
                 ],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            pages = list(reports_dir.iterdir())
            self.assertEqual(len(pages), 0, pages)
            skip_lines = [
                l for l in result.stderr.splitlines()
                if "PRS VERSION SKIP" in l
            ]
            self.assertEqual(len(skip_lines), 4, skip_lines)
            # Each of the three probe versions appears in at least one skip line
            all_skip_text = " ".join(skip_lines)
            self.assertIn("empty-diff-probe", all_skip_text)
            self.assertIn("mode-full-probe", all_skip_text)
            self.assertIn("ruleid-probe", all_skip_text)
            self.assertIn("dev-1", all_skip_text)

    def test_baseline_plus_probe_writes_one_page_with_zero_skipped(self):
        """Baseline + probe concatenated → 1 page with rows_skipped: 0."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()

            blob = (
                pathlib.Path(str(BENCH_DIR / "testdata" / "ledger-baseline-opus-xhigh-full.jsonl"))
                .read_text()
                + pathlib.Path(str(BENCH_DIR / "testdata" / "ledger-probe-configs-mixed-prs-version.jsonl"))
                .read_text()
            )
            (results_dir / "results.jsonl").write_text(blob, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(results_dir),
                 "--reports-dir", str(reports_dir),
                 ],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            pages = sorted(p.name for p in reports_dir.iterdir())
            self.assertEqual(
                pages,
                ["cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b.md"],
            )
            skip_lines = [
                l for l in result.stderr.splitlines()
                if "PRS VERSION SKIP" in l
            ]
            self.assertEqual(len(skip_lines), 4, skip_lines)
            text = (reports_dir / pages[0]).read_text()
            skipped_line = [
                l for l in text.splitlines()
                if l.startswith("- rows skipped: ")
            ]
            self.assertEqual(skipped_line, ["- rows skipped: 0"], skipped_line)

    def test_one_row_mismatched_prs_version_skipped_config_still_writes_page(self):
        """One baseline row's prs_version rewritten to a different value → 1 page, rows_skipped: 1."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()

            baseline = (
                pathlib.Path(str(BENCH_DIR / "testdata" / "ledger-baseline-opus-xhigh-full.jsonl"))
                .read_text()
                .splitlines()
            )
            rows = [json.loads(l) for l in baseline]
            for row in rows:
                if row["pr_id"] == "tts-mcp#20":
                    row["prs_version"] = "mode-full-probe"
                    break
            (results_dir / "results.jsonl").write_text(
                "\n".join(json.dumps(r) for r in rows) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(results_dir),
                 "--reports-dir", str(reports_dir),
                 ],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            pages = sorted(p.name for p in reports_dir.iterdir())
            self.assertEqual(len(pages), 1, pages)

            text = (reports_dir / pages[0]).read_text()

            skipped_line = [
                l for l in text.splitlines()
                if l.startswith("- rows skipped: ")
            ]
            self.assertEqual(skipped_line, ["- rows skipped: 1"], skipped_line)

            # tts-mcp#20 absent from Per-PR table
            per_pr_section = text[text.find("## Per-PR"):]
            self.assertNotIn("tts-mcp#20", per_pr_section)

            # Runs table: partial, 4 PRs, 41 golden in scope, 41 hits, 0 misses, recall=1.000
            runs_section = text[text.find("## Runs"):text.find("## Per-PR")]
            runs_lines = [
                l for l in runs_section.splitlines()
                if l.startswith("| 1 |")
            ]
            self.assertEqual(len(runs_lines), 1, runs_lines)
            cells = [c.strip() for c in runs_lines[0].split("|") if c.strip()]
            # cells: #, span, PRs, status, entries, findings, hits, misses, matched, gap, recall, precision, wall
            self.assertEqual(cells[3], "partial", cells)
            # The skipped row is visible as a denominator, not only as "partial":
            # 4 of the 5 manifest PRs produced a scored row.
            self.assertEqual(cells[2], "4/5", cells)
            self.assertEqual(cells[4], "41", cells)
            self.assertEqual(cells[6], "41", cells)
            self.assertEqual(cells[7], "0", cells)
            self.assertEqual(cells[10], "1.000", cells)
            self.assertEqual(cells[11], "1.000", cells)


class TestInvalidConfigHashRejectsOneConfigAndKeepsTheRest(unittest.TestCase):
    """AC21 — invalid config_hash in ledger rejects that config but scores the rest."""

    def test_invalid_config_hash_rejects_one_and_keeps_the_rest(self):
        """A row with an invalid config_hash skips that config; rest get pages."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()

            baseline = [
                json.loads(l)
                for l in (
                    pathlib.Path(str(BENCH_DIR / "testdata" / "ledger-baseline-opus-xhigh-full.jsonl"))
                    .read_text()
                    .splitlines()
                )
                if l.strip()
            ]

            quant_row = next(r for r in baseline if r["pr_id"] == "quant#109")
            bad_row = copy.deepcopy(quant_row)
            bad_row["config_hash"] = "../../etc/passwd"
            # All other fields including prs_version remain correct (dev-1)

            ledger = results_dir / "results.jsonl"
            ledger.write_text(
                "\n".join(json.dumps(r) for r in baseline + [bad_row]) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--score",
                 "--golden", str(GOLDEN_FIXTURE),
                 "--out-dir", str(results_dir),
                 "--reports-dir", str(reports_dir),
                 ],
                capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("INVALID CONFIG HASH", result.stderr)
            self.assertIn("../../etc/passwd", result.stderr)

            pages = sorted(p.name for p in reports_dir.iterdir())
            self.assertEqual(
                pages,
                ["cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b.md"],
            )

            # Only the reports_dir got new files; results/ is unchanged
            for path in reports_dir.iterdir():
                self.assertTrue(path.is_file(), f"{path} is not a file")


class TestLiveRunWithGoldenScoresItsOwnConfigurationOnly(unittest.TestCase):
    """DB1 live-run half — --golden on a live run scores only that config."""

    def test_live_run_with_golden_scores_own_config_only(self):
        """A live run with --golden produces a page only for its own config_hash.

        Uses mock.patch.dict to inject HOME+PATH so run_bench() finds the stub
        and the verify config dir, following the same pattern as test_config.py.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            counter_file = tmp / "counter"
            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()
            cache_root = tmp / "cache"

            # Seed a prior unrelated config into the same results dir
            prior_row = {
                "config_hash": "0" * 64,
                "pr_id": "test#99",
                "prs_version": "dev-1",
                "findings": [],
                "model": "sonnet",
                "effort": "medium",
                "mode": "short",
                "rules_commands_hash": "0" * 64,
                "duration_seconds": 1.0,
                "started_at": "2026-08-09T00:00:00+00:00",
                "notes": [],
                "review_command": "claude --print",
                "raw_output_ref": "",
                "base_sha": "a" * 40,
                "head_sha": "b" * 40,
                "diff_range": "a..b",
                "parent_count": 1,
                "changed_files": 1,
                "runner_version": "1",
            }
            (results_dir / "results.jsonl").write_text(
                json.dumps(prior_row) + "\n",
                encoding="utf-8",
            )

            repo_dir = tmp / "repo"
            testsupport.build_coding_repo(repo_dir)
            cfg_dir = testsupport.build_verify_config_dir(
                tmp / ".claude-verify",
                repo_dir,
            )

            manifest_path = testsupport.seed_one_pr_manifest(tmp, cache_root)
            manifest = json.loads(manifest_path.read_text())
            manifest["version"] = "dev-1"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            small_golden = tmp / "golden.json"
            small_golden.write_text(
                json.dumps({
                    "version": "small-golden",
                    "prs_version": "dev-1",
                    "baseline": {
                        "model": "opus",
                        "effort": "xhigh",
                        "mode": "full",
                        "coding_version": "v99.99.99",
                        "config_hash_prefix": "cc64cc99",
                        "rules_commands_hash_prefix": "ecc80333",
                        "runs": 1,
                        "findings": 1,
                        "wall_time_seconds": 1,
                    },
                    "entries": [
                        {
                            "pr_id": "test#1",
                            "path": "README.md",
                            "signature": ["readme.md:1"],
                            "state": "accepted",
                        },
                    ],
                    "match_rule": "rule_id exact",
                    "states": {"accepted": "ok", "rejected": "no", "unreviewed": "?"},
                }),
                encoding="utf-8",
            )

            testsupport.stub_claude(
                bin_dir,
                counter_file,
                testsupport.review_report(must_fix="Found something."),
            )

            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(tmp)

            with mock.patch.dict(os.environ, env):
                rc = run.run_bench(
                    coding_repo=repo_dir,
                    manifest_path=manifest_path,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model="opus",
                    effort="xhigh",
                    mode="full",
                    config_dir=cfg_dir,
                    golden=json.loads(small_golden.read_text()),
                    reports_dir=reports_dir,
                )

            # rc may be 1 if the stub review was rejected as "NOT A REVIEW"
            self.assertIn(rc, (0, 1), f"expected rc 0 or 1, got {rc}")

            # Only the live-run config got a page (not the prior unrelated one)
            pages = sorted(p.name for p in reports_dir.iterdir())
            self.assertEqual(len(pages), 1, pages)
            self.assertNotIn(
                "0" * 64 + ".md",
                [p.name for p in reports_dir.iterdir()],
            )


class TestRunFailureOutranksScoreResult(unittest.TestCase):
    """DB1 exit-code precedence — a failing run returns non-zero even when scoring succeeds."""

    def test_run_failure_outranks_score_success(self):
        """A failing run with --golden returns the run's non-zero code, not 0.

        The stub exits 3 after the review (so no ledger row is written for this run),
        but the ledger is pre-populated with a valid row so score_ledger can run and
        return 0.  The overall exit must be non-zero (outrank).
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            counter_file = tmp / "counter"
            results_dir = tmp / "results"
            results_dir.mkdir()
            reports_dir = tmp / "reports"
            reports_dir.mkdir()
            cache_root = tmp / "cache"

            repo_dir = tmp / "repo"
            testsupport.build_coding_repo(repo_dir)
            cfg_dir = testsupport.build_verify_config_dir(
                tmp / ".claude-verify",
                repo_dir,
            )

            manifest_path = testsupport.seed_one_pr_manifest(tmp, cache_root)
            manifest = json.loads(manifest_path.read_text())
            manifest["version"] = "test-1"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            small_golden = tmp / "golden.json"
            small_golden.write_text(
                json.dumps({
                    "version": "small-golden",
                    "prs_version": "test-1",
                    "baseline": {
                        "model": "opus",
                        "effort": "xhigh",
                        "mode": "full",
                        "coding_version": "v99.99.99",
                        "config_hash_prefix": "cc64cc99",
                        "rules_commands_hash_prefix": "ecc80333",
                        "runs": 1,
                        "findings": 1,
                        "wall_time_seconds": 1,
                    },
                    "entries": [
                        {
                            "pr_id": "test#1",
                            "path": "README.md",
                            "signature": ["readme.md:1"],
                            "state": "accepted",
                        },
                    ],
                    "match_rule": "rule_id exact",
                    "states": {"accepted": "ok", "rejected": "no", "unreviewed": "?"},
                }),
                encoding="utf-8",
            )

            # Pre-populate the ledger with a valid row so score_ledger has something to score
            prior_row = {
                "config_hash": "1" * 64,
                "pr_id": "test#1",
                "prs_version": "test-1",
                "findings": [],
                "model": "opus",
                "effort": "xhigh",
                "mode": "full",
                "rules_commands_hash": "1" * 64,
                "duration_seconds": 1.0,
                "started_at": "2026-08-09T00:00:00+00:00",
                "notes": [],
                "review_command": "claude --print",
                "raw_output_ref": "",
                "base_sha": "a" * 40,
                "head_sha": "b" * 40,
                "diff_range": "a..b",
                "parent_count": 1,
                "changed_files": 1,
                "runner_version": "1",
            }
            (results_dir / "results.jsonl").write_text(
                json.dumps(prior_row) + "\n",
                encoding="utf-8",
            )

            testsupport.stub_claude_streams(
                bin_dir,
                counter_file,
                stdout_text=testsupport.review_report(must_fix="Found something."),
                exit_code=3,
            )

            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(tmp)

            with mock.patch.dict(os.environ, env):
                rc = run.run_bench(
                    coding_repo=repo_dir,
                    manifest_path=manifest_path,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model="opus",
                    effort="xhigh",
                    mode="full",
                    config_dir=cfg_dir,
                    golden=json.loads(small_golden.read_text()),
                    reports_dir=reports_dir,
                )

            # Run failed (exit 3), scoring succeeded (exit 0).
            # Non-zero run code must outrank zero score code.
            self.assertNotEqual(rc, 0, "run should fail")
            # run_rc is 1 (n_failed>0), not the stub's exit 3.
            # The failure outranks scoring (which would return 0) by producing non-zero.
            self.assertEqual(rc, 1, "run failure outranks scoring success")


class TestDroppedItemsAreVisibleOnThePage(unittest.TestCase):
    """What the gates removed must be readable next to the score it affects.

    The item-level gates (v0.38.3) drop an unattributable finding and grade a
    review on the severity sections it did carry.  Both are recorded on the row.
    If neither reaches the page, a run whose reviews were largely rejected on
    shape renders identically to one that scored cleanly — the failure mode the
    whole bench exists to make visible.
    """

    def _page_for(self, rows):
        golden = load_golden()
        cfg = run.score_config(rows=rows, golden=golden)
        with tempfile.TemporaryDirectory() as tmp:
            path = run.write_report(
                reports_dir=pathlib.Path(tmp), config_score=cfg,
                golden=golden, coding_version="0.38.3",
            )
            return path.read_text(), cfg

    def test_dropped_item_count_reaches_the_per_pr_table(self):
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        for row in rows:
            if row["pr_id"] == "quant#109":
                row["unattributable_count"] = 2
                break

        text, cfg = self._page_for(rows)
        table = parse_table(text, "## Per-PR")
        cells = next(r for r in table if r[1] == "quant#109")

        self.assertEqual(int(cells[7]), 2, cells)
        breakdown = next(
            p for p in cfg.runs[0].per_pr if p.pr_id == "quant#109"
        )
        self.assertEqual(breakdown.unattributable, 2)
        self.assertIn("**2** findings carried no matching key", text)

    def test_missing_section_names_reach_the_per_pr_table(self):
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        for row in rows:
            if row["pr_id"] == "quant#109":
                row["missing_sections"] = ["Must Fix"]
                break

        text, _ = self._page_for(rows)
        table = parse_table(text, "## Per-PR")
        cells = next(r for r in table if r[1] == "quant#109")

        self.assertEqual(cells[8], "Must Fix", cells)
        self.assertIn("missing at least one severity section", text)

    def test_clean_run_says_so_rather_than_going_quiet(self):
        """Absent fields must read as "nothing dropped", not as an empty cell.

        Older ledgers predate both fields entirely; that is indistinguishable
        from a clean run and must render as one.
        """
        rows = load_slice("ledger-baseline-opus-xhigh-full.jsonl")
        for row in rows:
            row.pop("unattributable_count", None)
            row.pop("missing_sections", None)

        text, _ = self._page_for(rows)
        table = parse_table(text, "## Per-PR")

        for cells in table:
            self.assertEqual(int(cells[7]), 0, cells)
            self.assertEqual(cells[8], "—", cells)
        self.assertIn("**5 of 5** PRs produced a scored row", text)
        self.assertNotIn("carried no matching key", text)


if __name__ == "__main__":
    unittest.main()


# ----------------------------------------------------------------------
# Identity is the signature alone (2026-08-10)
# ----------------------------------------------------------------------
class TestSignaturesCarryNoLineReference(unittest.TestCase):
    """A `path:line` signature makes recall measure citation, not detection."""

    def test_live_golden_signatures_are_line_free(self):
        golden = run.load_golden(BENCH_DIR / "golden.json")
        offenders = [
            (e["pr_id"], kw)
            for e in golden["entries"]
            for kw in e["signature"]
            if re.search(r":\d+", kw)
        ]
        self.assertEqual(offenders, [], "signature keywords must not embed a line")

    def test_fixture_signatures_are_line_free(self):
        golden = run.load_golden(GOLDEN_FIXTURE)
        offenders = [kw for e in golden["entries"] for kw in e["signature"]
                     if re.search(r":\d+", kw)]
        self.assertEqual(offenders, [])

    def test_loader_rejects_a_line_bearing_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "golden.json"
            path.write_text(json.dumps({
                "version": "t", "prs_version": "dev-1",
                "match_rule": "t", "states": {}, "entries": [
                    {"pr_id": "a#1", "path": "x.go",
                     "signature": ["x.go:42", "other"], "state": "accepted"}
                ]}), encoding="utf-8")
            with self.assertRaises(run.BenchError) as ctx:
                run.load_golden(path)
            self.assertIn("embeds a line reference", str(ctx.exception))

    def test_loader_rejects_a_single_keyword_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "golden.json"
            path.write_text(json.dumps({
                "version": "t", "prs_version": "dev-1",
                "match_rule": "t", "states": {}, "entries": [
                    {"pr_id": "a#1", "path": "x.go",
                     "signature": ["lonely"], "state": "accepted"}
                ]}), encoding="utf-8")
            with self.assertRaises(run.BenchError) as ctx:
                run.load_golden(path)
            self.assertIn("at least 2 signature keywords", str(ctx.exception))


class TestRuleIdConstrainsButNeverShortCircuits(unittest.TestCase):
    """Regression: one rule firing twice in a file must not alias to one entry.

    The github-pr-review-agent#11 CHANGELOG entry describes a bullet bundling
    three concerns.  A later run reported a *different* defect in the same file
    (a dependency bump prefixed `fix:` where the repo uses `chore:`) under the
    same `changelog/conventional-prefix-required` rule.  The old matcher
    returned on rule_id equality alone, so that unrelated finding was credited
    as a hit for this entry.
    """

    ENTRY = {
        "pr_id": "x#1", "path": "CHANGELOG.md",
        "signature": ["bullet bundles", "split"],
        "rule_id": "changelog/conventional-prefix-required",
        "state": "accepted",
    }

    def test_same_rule_different_issue_does_not_match(self):
        other = {
            "pr_id": "x#1", "path": "CHANGELOG.md", "line": 10,
            "body": "dependency bump is prefixed `fix:`; precedent is `chore:`",
            "rule_id": "changelog/conventional-prefix-required",
        }
        self.assertFalse(run.finding_matches_entry(self.ENTRY, other))

    def test_same_rule_same_issue_still_matches(self):
        same = {
            "pr_id": "x#1", "path": "CHANGELOG.md", "line": 11,
            "body": "one bullet bundles the feature and the docs; split it",
            "rule_id": "changelog/conventional-prefix-required",
        }
        self.assertTrue(run.finding_matches_entry(self.ENTRY, same))

    def test_disagreeing_rule_id_blocks_an_otherwise_matching_body(self):
        wrong_rule = {
            "pr_id": "x#1", "path": "CHANGELOG.md", "line": 11,
            "body": "one bullet bundles the feature and the docs; split it",
            "rule_id": "some/other-rule",
        }
        self.assertFalse(run.finding_matches_entry(self.ENTRY, wrong_rule))

    def test_empty_signature_never_matches(self):
        self.assertFalse(run.finding_matches_entry(
            {"pr_id": "x#1", "path": "a.go", "signature": [], "state": "accepted"},
            {"pr_id": "x#1", "path": "a.go", "body": "anything", "rule_id": None},
        ))


class TestPathIsNotPartOfIdentity(unittest.TestCase):
    """The same defect anchored in a different file is still the same defect.

    Real case: "a write-scoped token is still minted under --skip-post" is keyed
    to pkg/factory/runner.go, but a later run anchored it at cmd/run-task/main.go
    while naming runner.go in the body.  Keying on path scored that as a miss.
    """

    ENTRY = {
        "pr_id": "x#1", "path": "pkg/factory/runner.go",
        "signature": ["write-scoped", "--skip-post"],
        "rule_id": None, "state": "accepted",
    }

    def test_same_issue_anchored_in_another_file_matches(self):
        finding = {
            "pr_id": "x#1", "path": "cmd/run-task/main.go", "line": 138,
            "body": ("the write-scoped GitHub App token is still minted under "
                     "`--skip-post` (`pkg/factory/runner.go:105-106`)"),
            "rule_id": None,
        }
        self.assertTrue(run.finding_matches_entry(self.ENTRY, finding))

    def test_unrelated_body_on_the_recorded_path_does_not_match(self):
        finding = {
            "pr_id": "x#1", "path": "pkg/factory/runner.go", "line": 66,
            "body": "ResolvePosters would read better as ResolvePosterAndVerifier",
            "rule_id": None,
        }
        self.assertFalse(run.finding_matches_entry(self.ENTRY, finding))


class TestNoEntrySignatureSubsumesAnother(unittest.TestCase):
    """Ledger-free aliasing guard.

    `test_no_live_golden_entry_aliases_another` needs bench/results, which is
    gitignored — so it skips in a fresh clone and in CI, exactly where a bad
    adjudication would land unnoticed.  A subset relationship is aliasing that
    can be proved from the golden set alone: if entry A's keywords are a subset
    of entry B's, then every finding matching B also matches A.
    """

    def _check(self, golden):
        by_pr = collections.defaultdict(list)
        for e in golden["entries"]:
            by_pr[e["pr_id"]].append(e)
        for pr, entries in by_pr.items():
            for a, b in itertools.permutations(entries, 2):
                sa = {k.lower() for k in a["signature"]}
                sb = {k.lower() for k in b["signature"]}
                self.assertFalse(
                    sa <= sb,
                    f"{pr}: {a['signature']} is a subset of {b['signature']} — "
                    f"every finding matching the latter also matches the former",
                )

    def test_live_golden_has_no_subsumed_signature(self):
        self._check(run.load_golden(BENCH_DIR / "golden.json"))

    def test_fixture_has_no_subsumed_signature(self):
        self._check(run.load_golden(GOLDEN_FIXTURE))


# ----------------------------------------------------------------------
# Run identity — spec 006 prompt 4 amendment (v0.44)
# ----------------------------------------------------------------------
class TestChunkRunsKeysOnRunId(unittest.TestCase):
    """Rows carry an explicit run_id since v0.44; chunking must use it.

    The pre-v0.44 occurrence-index inference is only exact when every run scores
    the same PRs.  Under row loss it mis-splits: if run 2 drops vault-cli#68,
    then in run 3 that PR's occurrence index is 2, so its row lands in run 2's
    bucket.  Measured 2026-08-10: a 5-run config with 2-7 dropped rows per run
    chunked as [20,20,19,17,8] against the true [18,13,17,18,18].
    """

    def _row(self, run_id, pr_id):
        return {"config_hash": "h", "run_id": run_id, "pr_id": pr_id,
                "prs_version": "curated-1", "findings": []}

    def test_run_id_groups_across_row_loss(self):
        # run 2 drops vault-cli#68 (row loss); run 3 scores it again.
        rows = [
            self._row("r1", "a#1"), self._row("r1", "b#2"),
            self._row("r2", "a#1"),
            self._row("r3", "a#1"), self._row("r3", "b#2"),
        ]
        runs = run.chunk_runs(rows)
        self.assertEqual([len(r) for r in runs], [2, 1, 2])
        self.assertEqual([r["run_id"] for r in runs[2]], ["r3", "r3"])
        self.assertEqual(runs[2][1]["pr_id"], "b#2")

    def test_legacy_rows_without_run_id_fall_back_to_occurrence_index(self):
        rows = [
            {"config_hash": "h", "pr_id": "a#1", "findings": []},
            {"config_hash": "h", "pr_id": "b#2", "findings": []},
            {"config_hash": "h", "pr_id": "a#1", "findings": []},
        ]
        runs = run.chunk_runs(rows)
        self.assertEqual([len(r) for r in runs], [2, 1])
        self.assertEqual(runs[0][0]["pr_id"], "a#1")
        self.assertEqual(runs[0][1]["pr_id"], "b#2")
        self.assertEqual(runs[1][0]["pr_id"], "a#1")

    def test_mixed_presence_uses_occurrence_index(self):
        # A config whose rows are half old (no run_id) and half new must not
        # explode; the conservative fallback applies.
        rows = [
            {"config_hash": "h", "pr_id": "a#1", "findings": []},
            {"config_hash": "h", "run_id": "r2", "pr_id": "a#1", "findings": []},
        ]
        runs = run.chunk_runs(rows)
        self.assertEqual([len(r) for r in runs], [1, 1])


class TestBuildRowCarriesRunId(unittest.TestCase):
    def test_every_row_gets_the_invocation_run_id(self):
        checkout = run.PrCheckout(
            pr_id="a#1", repo_dir=pathlib.Path("/tmp"), worktree=pathlib.Path("/tmp"),
            base_branch="master", head_branch="feature/x", diff_range="a..b",
            base_sha="a", head_sha="b", changed_files=1, parent_count=2, notes=[],
        )
        row = run.build_row(
            checkout=checkout, cfg_hash="h", rc_hash="r", model="opus",
            effort="xhigh", mode="full", prs_version="curated-1",
            review_command="claude", started_at="t0", run_id="run-123",
            duration_seconds=1.0, findings=[], raw_output_ref="x",
        )
        self.assertEqual(row["run_id"], "run-123")
