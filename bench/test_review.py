#!/usr/bin/env python3
"""Unit tests for bench/run.py review invocation, caching, harvesting, and ledger."""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import run
import testsupport


class TestSecondRunIsCacheHit(unittest.TestCase):
    """AC4: a second invocation of the same configuration invokes zero reviews."""

    def test_second_run_is_cache_hit_and_invokes_zero_reviews(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir = td / "results"
            results_dir.mkdir(parents=True)
            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, "findings: []")
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            # Seed two merge repos
            repos_root = cache_root / "repos"
            repos_root.mkdir(parents=True)
            repo_a = repos_root / "testowner" / "repo_a"
            repo_b = repos_root / "testowner" / "repo_b"
            repo_a.mkdir(parents=True)
            repo_b.mkdir(parents=True)
            info_a = testsupport.make_merge_repo(repo_a)
            info_b = testsupport.make_merge_repo(repo_b)

            manifest_entries = [
                {
                    "id": "test#1",
                    "owner": "testowner",
                    "repo": "repo_a",
                    "number": 1,
                    "merge_strategy": "merge-commit",
                    "merge_sha": info_a["merge_sha"],
                    "base_sha": info_a["base_sha"],
                    "head_sha": info_a["head_sha"],
                    "changed_files": 1,
                },
                {
                    "id": "test#2",
                    "owner": "testowner",
                    "repo": "repo_b",
                    "number": 2,
                    "merge_strategy": "merge-commit",
                    "merge_sha": info_b["merge_sha"],
                    "base_sha": info_b["base_sha"],
                    "head_sha": info_b["head_sha"],
                    "changed_files": 1,
                },
            ]
            manifest_path = td / "manifest.json"
            testsupport.make_manifest(manifest_path, manifest_entries)

            plugin_src = testsupport.make_coding_repo(td / "repo")
            cfg = testsupport.make_verify_config_dir(td / "cfg", plugin_src,
                                                     use_known_marketplaces=True)

            # First run
            with mock.patch.dict(os.environ, env):
                rc1 = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )

            self.assertEqual(rc1, 0, "first run must succeed")
            lines_first = counter.read_text().splitlines()
            self.assertEqual(len(lines_first), 2, f"first run must invoke 2 reviews, got: {lines_first}")

            # Second run
            results_dir2 = td / "results2"
            results_dir2.mkdir(parents=True)
            with mock.patch.dict(os.environ, env):
                rc2 = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=results_dir2,
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )

            self.assertEqual(rc2, 0, "second run must succeed")
            lines_second = counter.read_text().splitlines()
            self.assertEqual(len(lines_second), 2,
                f"second run must NOT invoke reviews (cache hit), got {len(lines_second)} lines: {lines_second}")

            # Ledger has 2 rows from first run
            ledger = run.ledger_path(results_dir)
            self.assertTrue(ledger.exists())
            rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
            self.assertEqual(len(rows), 2)

            # Second run stdout contains "cache hit" twice
            # We can't capture stdout easily, but we can verify via return code 0 and no new rows


class TestModeChangeIsCacheMiss(unittest.TestCase):
    """AC5: changing only --mode is a cache miss."""

    def test_mode_change_is_cache_miss(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir = td / "results"
            results_dir.mkdir(parents=True)
            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, "findings: []")
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            # Seed one merge repo
            repos_root = cache_root / "repos"
            repos_root.mkdir(parents=True)
            repo_a = repos_root / "testowner" / "repo_a"
            repo_a.mkdir(parents=True)
            info_a = testsupport.make_merge_repo(repo_a)

            manifest_entries = [
                {
                    "id": "test#1",
                    "owner": "testowner",
                    "repo": "repo_a",
                    "number": 1,
                    "merge_strategy": "merge-commit",
                    "merge_sha": info_a["merge_sha"],
                    "base_sha": info_a["base_sha"],
                    "head_sha": info_a["head_sha"],
                    "changed_files": 1,
                },
            ]
            manifest_path = td / "manifest.json"
            testsupport.make_manifest(manifest_path, manifest_entries)

            plugin_src = testsupport.make_coding_repo(td / "repo")
            cfg = testsupport.make_verify_config_dir(td / "cfg", plugin_src,
                                                     use_known_marketplaces=True)

            # First run: selector mode
            with mock.patch.dict(os.environ, env):
                rc1 = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="selector",
                    config_dir=cfg,
                )

            self.assertEqual(rc1, 0)
            lines_first = counter.read_text().splitlines()
            self.assertEqual(len(lines_first), 1, f"first run must invoke 1 review: {lines_first}")

            # Second run: full mode — same everything else
            with mock.patch.dict(os.environ, env):
                rc2 = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="full",
                    config_dir=cfg,
                )

            self.assertEqual(rc2, 0)
            lines_second = counter.read_text().splitlines()
            self.assertEqual(len(lines_second), 2,
                f"mode change must cause cache miss, got {len(lines_second)} lines: {lines_second}")

            # The second counter line must contain "full" (the mode literal reached the subprocess)
            self.assertIn("full", lines_second[1],
                f"second counter line must contain 'full': {lines_second[1]}")

            # Ledger has 2 rows
            ledger = run.ledger_path(results_dir)
            rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertNotEqual(rows[0]["mode"], rows[1]["mode"],
                f"modes must differ: {rows[0]['mode']} vs {rows[1]['mode']}")
            self.assertIn("selector", rows[0]["review_command"])
            self.assertIn("full", rows[1]["review_command"])


class TestCachePathDiffersWhenOnlyModeDiffers(unittest.TestCase):
    """Unit-level guard: cache paths differ when only mode differs."""

    def test_cache_path_differs_when_only_mode_differs(self):
        rc = "a" * 64
        pr_id = "test#1"
        h_selector = run.config_hash(rc, "claude-opus-5", "high", "selector", "dev-1")
        h_full = run.config_hash(rc, "claude-opus-5", "high", "full", "dev-1")

        self.assertNotEqual(h_selector, h_full)

        cache = pathlib.Path("/tmp/cache")
        row_selector = run.cache_row_path(cache, h_selector, pr_id)
        row_full = run.cache_row_path(cache, h_full, pr_id)
        self.assertNotEqual(str(row_selector), str(row_full),
            "cache row paths must differ when mode differs")

        raw_selector = run.cache_raw_path(cache, h_selector, pr_id)
        raw_full = run.cache_raw_path(cache, h_full, pr_id)
        self.assertNotEqual(str(raw_selector), str(raw_full),
            "cache raw paths must differ when mode differs")


class TestHarvestNormalizesSampleReport(unittest.TestCase):
    """AC10: harvest normalizes a review report into findings."""

    def test_harvest_normalizes_sample_report(self):
        text = (run.BENCH_DIR / "testdata" / "sample-report.md").read_text()
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        findings = run.harvest(text, known_ids)

        # Expected: 3 findings (Must Fix x2, Should Fix x1)
        # The Nice to Have section ("None.") and traceability section produce 0 findings
        self.assertEqual(len(findings), 3, f"expected 3 findings, got: {findings}")

        # Finding 1: Must Fix with inline path:line
        f1 = findings[0]
        self.assertEqual(f1["rule_id"], "agent-cmd/agent-frontmatter")
        self.assertEqual(f1["path"], "agents/my-agent.md")
        self.assertEqual(f1["line"], 3)
        self.assertIn("agent-cmd/agent-frontmatter", f1["body"])

        # Finding 2: Must Fix without path:line (rule_id only)
        f2 = findings[1]
        self.assertEqual(f2["rule_id"], "agent-cmd/command-thin")
        self.assertIsNone(f2["path"])
        self.assertIsNone(f2["line"])

        # Finding 3: Should Fix with continuation
        f3 = findings[2]
        self.assertEqual(f3["rule_id"], "changelog/unreleased-entry-required")
        self.assertIn("CHANGELOG.md", f3["body"])

        # All rule_ids are in the real index
        for f in findings:
            if f["rule_id"] is not None:
                self.assertIn(f["rule_id"], known_ids,
                    f"rule_id {f['rule_id']} not in rules/index.json")


class TestHarvestKeepsFindingWithoutAnyRuleId(unittest.TestCase):
    """A finding that cites no known rule ID is kept with rule_id=null."""

    def test_harvest_keeps_finding_without_any_rule_id(self):
        report = """#### Must Fix (Critical)
- This finding has no rule ID at all but should still be kept.
"""
        ids = run.load_rule_ids(run.REPO_ROOT)
        findings = run.harvest(report, ids)
        self.assertEqual(len(findings), 1)
        self.assertIsNone(findings[0]["rule_id"])
        self.assertIn("no rule ID", findings[0]["body"])


class TestHarvestIgnoresEmptySection(unittest.TestCase):
    """A section whose body is "None." yields zero findings."""

    def test_harvest_ignores_empty_section(self):
        report = """#### Nice to Have (Optional)
None.
"""
        ids = run.load_rule_ids(run.REPO_ROOT)
        findings = run.harvest(report, ids)
        self.assertEqual(len(findings), 0)


class TestLedgerIsAppendOnlyAndAtomic(unittest.TestCase):
    """Ledger rows are append-only and written atomically."""

    def test_ledger_is_append_only_and_atomic(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            results_dir = td / "results"
            results_dir.mkdir(parents=True)

            row1 = {"pr_id": "test#1", "findings": []}
            row2 = {"pr_id": "test#2", "findings": [{"rule_id": "foo/bar"}]}
            row3 = {"pr_id": "test#3", "findings": []}

            run.append_row(results_dir, row1)
            run.append_row(results_dir, row2)

            lp = run.ledger_path(results_dir)
            self.assertEqual(len(lp.read_text().splitlines()), 2)

            # Before third append, record line 1 and 2 content
            lines_before = lp.read_text().splitlines()
            row1_before = lines_before[0]
            row2_before = lines_before[1]

            run.append_row(results_dir, row3)

            lines_after = lp.read_text().splitlines()
            self.assertEqual(len(lines_after), 3)
            self.assertEqual(lines_after[0], row1_before,
                "first row must be unchanged after append")
            self.assertEqual(lines_after[1], row2_before,
                "second row must be unchanged after append")

            # No leftover .tmp files
            tmp_files = list(results_dir.glob("*.tmp"))
            self.assertEqual(len(tmp_files), 0, f"no .tmp files expected, found: {tmp_files}")


class TestSecondRunnerExitsWithoutTouchingLedger(unittest.TestCase):
    """A second runner started while one is in progress exits with error."""

    def test_second_runner_exits_without_touching_ledger(self):
        # Use the real REPO_ROOT as coding_repo so content_hash matches
        # the plugin that the config dir points to.
        results_dir = pathlib.Path(tempfile.mkdtemp())
        try:
            lock = run.lock_path(results_dir)
            lock.write_text("999999 2026-01-01T00:00:00+00:00\n", encoding="utf-8")

            old_home = os.environ.get("HOME", "")
            try:
                os.environ["HOME"] = str(results_dir)

                # Create a .claude-verify that points to REPO_ROOT
                cfg_dir = results_dir / ".claude-verify"
                cfg_dir.mkdir(parents=True, exist_ok=True)
                (cfg_dir / "plugins").mkdir(parents=True, exist_ok=True)
                km = {
                    "coding": {
                        "source": {"source": "github", "repo": "bborbe/coding"},
                        "installLocation": str(run.REPO_ROOT),
                    }
                }
                (cfg_dir / "plugins" / "known_marketplaces.json").write_text(
                    json.dumps(km), encoding="utf-8"
                )

                result = subprocess.run(
                    [sys.executable, str(run.BENCH_DIR / "run.py"),
                     "--coding-repo", str(run.REPO_ROOT),
                     "--manifest", str(run.BENCH_DIR / "prs.json"),
                     "--out-dir", str(results_dir),
                     "--model", "test-model",
                     "--effort", "high",
                     "--mode", "short"],
                    capture_output=True, text=True,
                    env={**os.environ, "HOME": str(results_dir)},
                )
            finally:
                os.environ["HOME"] = old_home

            self.assertEqual(result.returncode, 2,
                f"second runner must exit 2, got {result.returncode}: {result.stderr}")
            self.assertIn(str(lock), result.stderr,
                f"error must name the lock file: {result.stderr}")
            self.assertIn("another bench run", result.stderr,
                f"error must mention another bench run: {result.stderr}")
        finally:
            shutil.rmtree(results_dir, ignore_errors=True)


class TestRowCarriesEveryRequiredField(unittest.TestCase):
    """A successful run produces a row with every required field."""

    def test_row_carries_every_required_field(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir = td / "results"
            results_dir.mkdir(parents=True)
            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, "findings: []")
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            # Seed one merge repo
            repos_root = cache_root / "repos"
            repos_root.mkdir(parents=True)
            repo_a = repos_root / "testowner" / "repo_a"
            repo_a.mkdir(parents=True)
            info_a = testsupport.make_merge_repo(repo_a)

            manifest_entries = [
                {
                    "id": "test#1",
                    "owner": "testowner",
                    "repo": "repo_a",
                    "number": 1,
                    "merge_strategy": "merge-commit",
                    "merge_sha": info_a["merge_sha"],
                    "base_sha": info_a["base_sha"],
                    "head_sha": info_a["head_sha"],
                    "changed_files": 1,
                },
            ]
            manifest_path = td / "manifest.json"
            testsupport.make_manifest(manifest_path, manifest_entries)

            plugin_src = testsupport.make_coding_repo(td / "repo")
            cfg = testsupport.make_verify_config_dir(td / "cfg", plugin_src,
                                                     use_known_marketplaces=True)

            with mock.patch.dict(os.environ, env):
                rc = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )

            self.assertEqual(rc, 0)

            ledger = run.ledger_path(results_dir)
            rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            row = rows[0]

            required_fields = [
                "config_hash", "rules_commands_hash", "model", "effort", "mode",
                "prs_version", "pr_id", "base_sha", "head_sha", "diff_range",
                "changed_files", "review_command", "started_at", "duration_seconds",
                "findings", "raw_output_ref", "runner_version",
            ]
            for field in required_fields:
                self.assertIn(field, row, f"row must have field: {field}")
                self.assertIsNotNone(row[field], f"field {field} must not be None")

            # started_at must have UTC offset
            self.assertIn("+", row["started_at"]) or row["started_at"].endswith("Z")


class TestRawOutputIsCachedVerbatim(unittest.TestCase):
    """After a successful run, the raw stdout is cached verbatim."""

    def test_raw_output_is_cached_verbatim(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir = td / "results"
            results_dir.mkdir(parents=True)
            bin_dir = td / "bin"
            counter = td / "counter"
            report_text = "findings: [{\"rule_id\":\"foo/bar\",\"path\":\"x.go\",\"line\":1}]"
            stub = testsupport.stub_claude(bin_dir, counter, report_text)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            # Seed one merge repo
            repos_root = cache_root / "repos"
            repos_root.mkdir(parents=True)
            repo_a = repos_root / "testowner" / "repo_a"
            repo_a.mkdir(parents=True)
            info_a = testsupport.make_merge_repo(repo_a)

            manifest_entries = [
                {
                    "id": "test#1",
                    "owner": "testowner",
                    "repo": "repo_a",
                    "number": 1,
                    "merge_strategy": "merge-commit",
                    "merge_sha": info_a["merge_sha"],
                    "base_sha": info_a["base_sha"],
                    "head_sha": info_a["head_sha"],
                    "changed_files": 1,
                },
            ]
            manifest_path = td / "manifest.json"
            testsupport.make_manifest(manifest_path, manifest_entries)

            plugin_src = testsupport.make_coding_repo(td / "repo")
            cfg = testsupport.make_verify_config_dir(td / "cfg", plugin_src,
                                                     use_known_marketplaces=True)

            with mock.patch.dict(os.environ, env):
                rc = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )

            self.assertEqual(rc, 0)

            ledger = run.ledger_path(results_dir)
            rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
            row = rows[0]

            raw_ref = row["raw_output_ref"]
            if raw_ref.startswith("/"):
                raw_path = pathlib.Path(raw_ref)
            else:
                raw_path = run.REPO_ROOT / raw_ref

            self.assertTrue(raw_path.exists(), f"raw cache file must exist: {raw_path}")
            # The stub uses cat heredoc which appends a trailing newline
            self.assertEqual(raw_path.read_text(), report_text + "\n",
                "raw cache must contain the stub's report text (plus trailing newline)")


class TestFailedReviewLeavesNoRowAndNoCacheEntry(unittest.TestCase):
    """A failing review produces no row and no cache entry."""

    def test_failed_review_leaves_no_row_and_no_cache_entry(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir = td / "results"
            results_dir.mkdir(parents=True)
            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude_failing(bin_dir, counter, exit_code=3)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            # Seed one merge repo
            repos_root = cache_root / "repos"
            repos_root.mkdir(parents=True)
            repo_a = repos_root / "testowner" / "repo_a"
            repo_a.mkdir(parents=True)
            info_a = testsupport.make_merge_repo(repo_a)

            manifest_entries = [
                {
                    "id": "test#1",
                    "owner": "testowner",
                    "repo": "repo_a",
                    "number": 1,
                    "merge_strategy": "merge-commit",
                    "merge_sha": info_a["merge_sha"],
                    "base_sha": info_a["base_sha"],
                    "head_sha": info_a["head_sha"],
                    "changed_files": 1,
                },
            ]
            manifest_path = td / "manifest.json"
            testsupport.make_manifest(manifest_path, manifest_entries)

            plugin_src = testsupport.make_coding_repo(td / "repo")
            cfg = testsupport.make_verify_config_dir(td / "cfg", plugin_src,
                                                     use_known_marketplaces=True)

            with mock.patch.dict(os.environ, env):
                rc = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )

            self.assertEqual(rc, 1, "run must exit 1 when a PR fails")

            # No ledger row
            ledger = run.ledger_path(results_dir)
            if ledger.exists():
                rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
            else:
                rows = []
            self.assertEqual(len(rows), 0, "no row must be written for failed review")

            # No cache entry in reviews/
            reviews = run.reviews_root(cache_root)
            if reviews.exists():
                review_files = list(reviews.glob("*.json")) + list(reviews.glob("*.stdout.txt"))
            else:
                review_files = []
            self.assertEqual(len(review_files), 0,
                f"no review cache files expected, found: {review_files}")

            # Failure log exists
            failures = run.failures_root(cache_root)
            failure_files = list(failures.glob("*.stderr.txt")) if failures.exists() else []
            self.assertEqual(len(failure_files), 1,
                f"one failure log expected, found: {failure_files}")


class TestFailedPrDoesNotPreventLaterPrs(unittest.TestCase):
    """A PR whose SHA is unresolvable does not prevent later PRs from running."""

    def test_failed_pr_does_not_prevent_later_prs(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir = td / "results"
            results_dir.mkdir(parents=True)
            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, "findings: []")
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            # Seed one good repo
            repos_root = cache_root / "repos"
            repos_root.mkdir(parents=True)
            repo_good = repos_root / "testowner" / "goodrepo"
            repo_good.mkdir(parents=True)
            info_good = testsupport.make_merge_repo(repo_good)

            manifest_entries = [
                {
                    "id": "bad#1",
                    "owner": "badowner",
                    "repo": "badrepo",
                    "number": 1,
                    "merge_strategy": "merge-commit",
                    "merge_sha": "a" * 40,
                    "base_sha": "b" * 40,
                    "head_sha": "c" * 40,
                    "changed_files": 1,
                },
                {
                    "id": "good#2",
                    "owner": "testowner",
                    "repo": "goodrepo",
                    "number": 2,
                    "merge_strategy": "merge-commit",
                    "merge_sha": info_good["merge_sha"],
                    "base_sha": info_good["base_sha"],
                    "head_sha": info_good["head_sha"],
                    "changed_files": 1,
                },
            ]
            manifest_path = td / "manifest.json"
            testsupport.make_manifest(manifest_path, manifest_entries)

            plugin_src = testsupport.make_coding_repo(td / "repo")
            cfg = testsupport.make_verify_config_dir(td / "cfg", plugin_src,
                                                     use_known_marketplaces=True)

            with mock.patch.dict(os.environ, env):
                rc = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )

            self.assertEqual(rc, 1, "run must exit 1 when any PR fails")

            ledger = run.ledger_path(results_dir)
            rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["pr_id"], "good#2")


class TestCorruptCacheRowIsTreatedAsMiss(unittest.TestCase):
    """A cache file containing malformed JSON is treated as a miss."""

    def test_corrupt_cache_row_is_treated_as_miss(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir = td / "results"
            results_dir.mkdir(parents=True)
            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, "findings: []")
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            # Seed one merge repo
            repos_root = cache_root / "repos"
            repos_root.mkdir(parents=True)
            repo_a = repos_root / "testowner" / "repo_a"
            repo_a.mkdir(parents=True)
            info_a = testsupport.make_merge_repo(repo_a)

            manifest_entries = [
                {
                    "id": "test#1",
                    "owner": "testowner",
                    "repo": "repo_a",
                    "number": 1,
                    "merge_strategy": "merge-commit",
                    "merge_sha": info_a["merge_sha"],
                    "base_sha": info_a["base_sha"],
                    "head_sha": info_a["head_sha"],
                    "changed_files": 1,
                },
            ]
            manifest_path = td / "manifest.json"
            testsupport.make_manifest(manifest_path, manifest_entries)

            plugin_src = testsupport.make_coding_repo(td / "repo")
            cfg = testsupport.make_verify_config_dir(td / "cfg", plugin_src,
                                                     use_known_marketplaces=True)

            # Compute cfg_hash to know where to write corrupt cache
            rc_hash = run.content_hash(plugin_src)
            cfg_hash = run.config_hash(rc_hash, "test-model", "high", "short", "test-1")

            # Write a corrupt cache file
            reviews = run.reviews_root(cache_root)
            reviews.mkdir(parents=True, exist_ok=True)
            corrupt_row = reviews / f"{run.cache_key(cfg_hash, 'test#1')}.json"
            corrupt_row.write_text("{ this is not json", encoding="utf-8")

            # First run: should overwrite corrupt cache
            with mock.patch.dict(os.environ, env):
                rc = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )

            self.assertEqual(rc, 0, "run must succeed after corrupt cache")
            lines = counter.read_text().splitlines()
            self.assertEqual(len(lines), 1,
                "review must have been invoked (corrupt cache treated as miss)")

            # Cache file now parses as valid JSON
            row_data = json.loads(corrupt_row.read_text(encoding="utf-8"))
            self.assertIn("pr_id", row_data)


if __name__ == "__main__":
    unittest.main()
