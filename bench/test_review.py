#!/usr/bin/env python3
"""Unit tests for bench/run.py review invocation, caching, harvesting, and ledger."""

import contextlib
import io
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


# ----------------------------------------------------------------------
# Shared test harness helpers
# ----------------------------------------------------------------------
def run_one_pr_with_payload(td: pathlib.Path, payload: str) -> tuple[int, str, pathlib.Path, pathlib.Path]:
    """Run bench over a one-PR temp manifest with the given stub payload.

    Returns (returncode, captured_stderr, results_dir, cache_root).
    The stub claude is installed on PATH before the call.
    """
    td = pathlib.Path(td)
    cache_root = td / "cache"
    results_dir = td / "results"
    results_dir.mkdir(parents=True)
    bin_dir = td / "bin"
    counter = td / "counter"
    stub = testsupport.stub_claude(bin_dir, counter, payload)
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

    plugin_src = testsupport.build_coding_repo(td / "repo")
    cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

    captured_stderr = io.StringIO()
    with contextlib.redirect_stderr(captured_stderr):
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
    return rc, captured_stderr.getvalue(), results_dir, cache_root


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
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
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

            plugin_src = testsupport.build_coding_repo(td / "repo")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

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
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
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

            plugin_src = testsupport.build_coding_repo(td / "repo")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

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
                # Create plugin cache directory and record in the new format
                cache_dir = cfg_dir / "plugins" / "cache" / "coding" / "coding" / "0.35.2"
                shutil.copytree(run.REPO_ROOT, cache_dir)
                record = {
                    "version": 2,
                    "plugins": {
                        "coding@coding": [{
                            "scope": "user",
                            "installPath": str(cache_dir),
                            "version": "0.35.2",
                            "installedAt": "2026-08-08T00:00:00.000Z",
                            "lastUpdated": "2026-08-08T00:00:00.000Z",
                        }]
                    }
                }
                (cfg_dir / "plugins" / "installed_plugins.json").write_text(
                    json.dumps(record), encoding="utf-8"
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
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
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

            plugin_src = testsupport.build_coding_repo(td / "repo")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

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
            report_text = testsupport.review_report(
                must_fix="- `agent-cmd/command-thin`: sample finding at `agents/x.md:12`."
            )
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

            plugin_src = testsupport.build_coding_repo(td / "repo")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

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

            plugin_src = testsupport.build_coding_repo(td / "repo")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

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
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
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

            plugin_src = testsupport.build_coding_repo(td / "repo")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

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
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
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

            plugin_src = testsupport.build_coding_repo(td / "repo")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

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


class TestRealCaptureHarvestsToZeroFindings(unittest.TestCase):
    """AC8: the verbatim-capture fixture harvests to zero findings."""

    def test_real_capture_harvests_to_zero_findings(self):
        text = (run.BENCH_DIR / "testdata" / "real-capture-report.md").read_text()
        ids = run.load_rule_ids(run.REPO_ROOT)
        findings = run.harvest(text, ids)
        self.assertEqual(findings, [], f"real capture must harvest to zero findings, got: {findings}")


class TestTrailingProseDoesNotSwallowARealFinding(unittest.TestCase):
    """AC9: a real finding's body is not corrupted by trailing prose."""

    def test_trailing_prose_does_not_swallow_a_real_finding(self):
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        # Pick a rule that actually exists in the index
        real_rule_id = next((rid for rid in known_ids if "/" in rid), None)
        self.assertIsNotNone(real_rule_id, "rules/index.json must contain at least one rule with a slash")

        report = (
            f"## Must Fix (Critical)\n"
            f"- `{real_rule_id}`: passing `None` as the default here hides the missing-value case in src/foo.go:12\n"
            f"## Should Fix (Important)\n"
            f"None.\n"
            f"## Nice to Have (Optional)\n"
            f"None.\n"
            f"---\n"
            f"**Summary:** This is the closing panel prose.\n"
            f"Some additional context about what was reviewed.\n"
        )
        findings = run.harvest(report, known_ids)
        self.assertEqual(len(findings), 1, f"expected exactly 1 finding, got: {findings}")
        f = findings[0]
        self.assertEqual(f["path"], "src/foo.go")
        self.assertEqual(f["line"], 12)
        self.assertIn("None", f["body"], "body must contain the word None (exact equality sentinel regression guard)")
        self.assertNotIn("Summary", f["body"], "body must not contain trailing prose")
        self.assertNotIn("closing panel", f["body"], "body must not contain trailing prose")


class TestHeadingLevelDoesNotChangeHarvest(unittest.TestCase):
    """AC10: heading level is irrelevant to harvesting."""

    def test_heading_level_does_not_change_harvest(self):
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        real_rule_id = next((rid for rid in known_ids if "/" in rid), None)
        self.assertIsNotNone(real_rule_id)

        report_template = (
            lambda prefix: (
                f"{prefix} Must Fix (Critical)\n"
                f"- `{real_rule_id}`: a finding in file.go:5\n"
                f"{prefix} Should Fix (Important)\n"
                f"None.\n"
                f"{prefix} Nice to Have (Optional)\n"
                f"None.\n"
            )
        )

        reports = {level: report_template(level) for level in ("##", "###", "####")}
        harvests = {level: run.harvest(text, known_ids) for level, text in reports.items()}

        self.assertEqual(
            harvests["##"],
            harvests["###"],
            f"## vs ###: {harvests['##']} vs {harvests['###']}",
        )
        self.assertEqual(
            harvests["##"],
            harvests["####"],
            f"## vs ####: {harvests['##']} vs {harvests['####']}",
        )


class TestSectionNameInProseOrFenceIsNotAHeading(unittest.TestCase):
    """Section names in prose or inside a fenced block do not open a section."""

    def test_heading_section_name_rejects_prose_and_fence(self):
        # Prose mentions are not headings
        self.assertIsNone(run.heading_section_name("**Must Fix**"))
        self.assertIsNone(run.heading_section_name("We looked at Must Fix items."))
        self.assertIsNone(run.heading_section_name("must fix:"))
        # Real headings at various levels
        self.assertEqual(run.heading_section_name("## Must Fix (Critical)"), "Must Fix")
        self.assertEqual(run.heading_section_name("###### nice to have"), "Nice to Have")
        self.assertEqual(run.heading_section_name("### Should Fix (Important)"), "Should Fix")

    def test_fence_contains_heading_not_a_section(self):
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        report = "```\n## Must Fix (Critical)\n- a finding\n```\n"
        findings = run.harvest(report, known_ids)
        self.assertEqual(findings, [], f"fenced heading must not open a section, got: {findings}")


class TestThematicBreakEndsASection(unittest.TestCase):
    """A thematic break immediately after a finding ends the section."""

    def test_thematic_break_ends_a_section(self):
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        real_rule_id = next((rid for rid in known_ids if "/" in rid), None)
        self.assertIsNotNone(real_rule_id)

        report = (
            f"## Nice to Have (Optional)\n"
            f"- `{real_rule_id}`: a real finding in file.go:99\n"
            f"---\n"
            f"**Summary:** This is trailing prose that must not be appended to the finding.\n"
            f"Another paragraph of closing remarks.\n"
        )
        findings = run.harvest(report, known_ids)
        self.assertEqual(len(findings), 1, f"expected 1 finding, got: {findings}")
        self.assertNotIn("Summary", findings[0]["body"])
        self.assertNotIn("trailing prose", findings[0]["body"])
        self.assertNotIn("closing remarks", findings[0]["body"])


class TestProseBeforeAListItemOpensNothing(unittest.TestCase):
    """Prose in a section before any list item buffers nothing."""

    def test_prose_before_a_list_item_opens_nothing(self):
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        real_rule_id = next((rid for rid in known_ids if "/" in rid), None)
        self.assertIsNotNone(real_rule_id)

        report = (
            f"## Must Fix (Critical)\n"
            f"None.\n"
            f"\n"
            f"- `{real_rule_id}`: the actual finding in bar.go:7\n"
            f"## Should Fix (Important)\n"
            f"None.\n"
            f"## Nice to Have (Optional)\n"
            f"None.\n"
        )
        findings = run.harvest(report, known_ids)
        self.assertEqual(len(findings), 1, f"expected 1 finding, got: {findings}")
        self.assertNotIn("None.", findings[0]["body"])
        self.assertEqual(findings[0]["path"], "bar.go")
        self.assertEqual(findings[0]["line"], 7)


# ----------------------------------------------------------------------
# New tests for the non-review sanity gate
# ----------------------------------------------------------------------
class TestNonReviewOutputIsRejected(unittest.TestCase):
    """AC2: output that is not review-shaped is rejected."""

    def test_non_review_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stderr, results_dir, cache_root = run_one_pr_with_payload(
                td, "Unknown command: /coding:pr-review"
            )

            self.assertEqual(rc, 1, "run must exit 1 for non-review")
            self.assertIn(run.NON_REVIEW_MARKER, stderr)
            self.assertIn("test#1", stderr)
            self.assertIn("Unknown command:", stderr)

            # No ledger row
            ledger = run.ledger_path(results_dir)
            if ledger.exists():
                rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
            else:
                rows = []
            self.assertEqual(len(rows), 0, "no ledger row for rejected review")

            # No cache entry
            reviews = run.reviews_root(cache_root)
            if reviews.exists():
                files = list(reviews.glob("*.json")) + list(reviews.glob("*.stdout.txt"))
            else:
                files = []
            self.assertEqual(len(files), 0, "no cache files for rejected review")


class TestSectionNamesOutsideHeadingsDoNotSatisfyTheGate(unittest.TestCase):
    """AC3: bare section literals in prose/fence/bold do not satisfy the gate."""

    def test_section_names_outside_headings_do_not_satisfy_the_gate(self):
        payload = (
            "We looked at Must Fix items.\n\n"
            "```\n"
            "## Should Fix (Important)\n"
            "```\n\n"
            "**Nice to Have**\n"
        )
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stderr, results_dir, cache_root = run_one_pr_with_payload(td, payload)

            self.assertEqual(rc, 1)
            self.assertIn(run.NON_REVIEW_MARKER, stderr)

            ledger = run.ledger_path(results_dir)
            if ledger.exists():
                rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
            else:
                rows = []
            self.assertEqual(len(rows), 0)

            reviews = run.reviews_root(cache_root)
            if reviews.exists():
                files = list(reviews.glob("*.json")) + list(reviews.glob("*.stdout.txt"))
            else:
                files = []
            self.assertEqual(len(files), 0)


class TestMissingSectionNamesAreReportedExactly(unittest.TestCase):
    """AC4: the missing-sections diagnosis names only the absent sections."""

    def test_missing_section_names_are_reported_exactly(self):
        # Case A: Nice to Have absent
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stderr, results_dir, cache_root = run_one_pr_with_payload(
                td, testsupport.review_report(nice_to_have=None)
            )
            self.assertEqual(rc, 1)

            missing_line = next(
                (l for l in stderr.splitlines() if l.startswith("missing sections: ")),
                "",
            )
            remainder = missing_line[len("missing sections: "):]
            self.assertEqual(remainder, "Nice to Have",
                "Case A: only Nice to Have missing")
            self.assertNotIn("Must Fix", remainder)
            self.assertNotIn("Should Fix", remainder)

            ledger = run.ledger_path(results_dir)
            rows = [] if not ledger.exists() else [
                json.loads(ln) for ln in ledger.read_text().splitlines()
            ]
            self.assertEqual(len(rows), 0)

        # Case B: Should Fix and Nice to Have absent
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stderr, results_dir, cache_root = run_one_pr_with_payload(
                td, testsupport.review_report(should_fix=None, nice_to_have=None)
            )
            self.assertEqual(rc, 1)

            missing_line = next(
                (l for l in stderr.splitlines() if l.startswith("missing sections: ")),
                "",
            )
            remainder = missing_line[len("missing sections: "):]
            self.assertEqual(remainder, "Should Fix, Nice to Have",
                "Case B: Should Fix and Nice to Have missing in that order")
            self.assertNotIn("Must Fix", remainder)

            ledger = run.ledger_path(results_dir)
            rows = [] if not ledger.exists() else [
                json.loads(ln) for ln in ledger.read_text().splitlines()
            ]
            self.assertEqual(len(rows), 0)


class TestRejectionExcerptIsBounded(unittest.TestCase):
    """AC5: rejection excerpt is bounded and carries a truncation marker."""

    def test_rejection_excerpt_is_bounded(self):
        result = run.non_review_report("test#1", ["Must Fix"], "x" * 100_000)
        self.assertLess(len(result.encode("utf-8")), 8192,
            "rejection diagnosis must be under 8 kB")
        self.assertIn("[... truncated,", result)
        self.assertIn("100000", result)


class TestReviewShapedOutputAtEitherHeadingLevelProducesARow(unittest.TestCase):
    """AC6: review-shaped output at h2 and h4 both produce a ledger row."""

    def test_review_shaped_output_at_either_heading_level_produces_a_row(self):
        for level in (2, 4):
            with tempfile.TemporaryDirectory() as td:
                td = pathlib.Path(td)
                rc, stderr, results_dir, cache_root = run_one_pr_with_payload(
                    td, testsupport.review_report(heading_level=level)
                )

                self.assertEqual(rc, 0,
                    f"heading_level={level}: run must succeed")

                ledger = run.ledger_path(results_dir)
                self.assertTrue(ledger.exists())
                rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
                self.assertEqual(len(rows), 1,
                    f"heading_level={level}: exactly 1 row expected")
                self.assertEqual(rows[0]["pr_id"], "test#1",
                    f"heading_level={level}: row must carry correct pr_id")


class TestGateDoesNotApplyToACacheHit(unittest.TestCase):
    """The sanity gate is not applied to previously cached output."""

    def test_gate_does_not_apply_to_a_cache_hit(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir1 = td / "results1"
            results_dir1.mkdir(parents=True)
            results_dir2 = td / "results2"
            results_dir2.mkdir(parents=True)
            bin_dir = td / "bin"
            counter = td / "counter"

            # First run: review-shaped payload, produces a row and cache entry
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

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

            plugin_src = testsupport.build_coding_repo(td / "repo")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

            with mock.patch.dict(os.environ, env):
                rc1 = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=results_dir1,
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )

            self.assertEqual(rc1, 0, "first run must succeed")

            # Second run: same cache, but stub replaced with non-review payload.
            # Must be a cache hit — gate must NOT be applied.
            bad_counter = td / "bad_counter"
            stub2 = testsupport.stub_claude(bin_dir, bad_counter, "Unknown command: /coding:pr-review")
            captured_stderr = io.StringIO()
            with contextlib.redirect_stderr(captured_stderr):
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

            self.assertEqual(rc2, 0, "second run must be a cache hit (gate not applied)")


if __name__ == "__main__":
    unittest.main()
