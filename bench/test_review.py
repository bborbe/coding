#!/usr/bin/env python3
"""Unit tests for bench/run.py review invocation, caching, harvesting, and ledger."""

import contextlib
from contextlib import nullcontext
import hashlib
import io
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


# ----------------------------------------------------------------------
# Shared test harness helpers
# ----------------------------------------------------------------------
def run_one_pr_with_payload(td: pathlib.Path, payload: str) -> tuple[int, str, str, pathlib.Path, pathlib.Path]:
    """Run bench over a one-PR temp manifest with the given stub payload.

    Returns (returncode, captured_stdout, captured_stderr, results_dir, cache_root).
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

    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    with contextlib.redirect_stdout(captured_stdout):
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
    return rc, captured_stdout.getvalue(), captured_stderr.getvalue(), results_dir, cache_root


def run_one_pr_with_streams(td: pathlib.Path, *, stdout_text: str = "",
                            stderr_text: str = "", exit_code: int = 0,
                            sleep_seconds: int = 0,
                            timeout_seconds: int | None = None):
    """Run bench over a one-PR temp manifest against a two-stream stub claude.

    Same seeding as run_one_pr_with_payload (one merge repo under
    <cache_root>/repos/testowner/repo_a, a one-entry manifest, a coding repo and an
    isolated config dir, the stub on PATH), but installs stub_claude_streams and
    captures stdout as well as stderr.  When timeout_seconds is given, run.
    REVIEW_TIMEOUT_SECONDS is patched to it for the duration of the call so the
    real timeout path can be exercised in about a second.

    Returns (returncode, captured_stdout, captured_stderr, results_dir, cache_root,
    counter_path).
    """
    td = pathlib.Path(td)
    cache_root = td / "cache"
    results_dir = td / "results"
    results_dir.mkdir(parents=True)
    bin_dir = td / "bin"
    counter = td / "counter"
    stub = testsupport.stub_claude_streams(
        bin_dir, counter,
        stdout_text=stdout_text, stderr_text=stderr_text,
        exit_code=exit_code, sleep_seconds=sleep_seconds,
    )
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

    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    timeout_patch = (
        mock.patch.object(run, "REVIEW_TIMEOUT_SECONDS", timeout_seconds)
        if timeout_seconds is not None else nullcontext()
    )
    with contextlib.redirect_stdout(captured_stdout), \
         contextlib.redirect_stderr(captured_stderr), \
         timeout_patch, \
         mock.patch.dict(os.environ, env):
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
    return rc, captured_stdout.getvalue(), captured_stderr.getvalue(), results_dir, cache_root, counter


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
        result = run.harvest(text, known_ids)
        findings = result.findings

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
- **`src/x.py:4`** This finding has no rule ID at all but should still be kept.
"""
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        findings = result.findings
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
        result = run.harvest(report, ids)
        findings = result.findings
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
                # Exclude the bench cache: it holds cloned PR repos whose .venv
                # dirs symlink into the host uv store.  copytree dereferences
                # symlinks by default, so without this the copy either explodes
                # to ~1GB or fails outright wherever those targets are absent
                # (e.g. inside a container).  content_hash only reads rules/ and
                # commands/, so nothing excluded here can affect the digest.
                shutil.copytree(
                    run.REPO_ROOT, cache_dir,
                    ignore=shutil.ignore_patterns(
                        ".cache", ".git", "results", ".venv", "__pycache__",
                    ),
                )
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
                must_fix="- **`agents/x.md:12`** sample finding."
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
            failure_files = list(failures.glob(f"*{run.FAILURE_ARTIFACT_SUFFIX}")) if failures.exists() else []
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
        result = run.harvest(text, ids)
        findings = result.findings
        unattributable = result.unattributable
        self.assertEqual(findings, [], f"real capture must harvest to zero findings, got: {findings}")
        self.assertEqual(unattributable, [], f"real capture must harvest to zero unattributable, got: {unattributable}")


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
        result = run.harvest(report, known_ids)
        findings = result.findings
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
        results = {level: run.harvest(text, known_ids) for level, text in reports.items()}
        harvests = {level: r.findings for level, r in results.items()}

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
        result = run.harvest(report, known_ids)
        findings = result.findings
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
        result = run.harvest(report, known_ids)
        findings = result.findings
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
        result = run.harvest(report, known_ids)
        findings = result.findings
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
            rc, stdout, stderr, results_dir, cache_root = run_one_pr_with_payload(
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
            rc, stdout, stderr, results_dir, cache_root = run_one_pr_with_payload(td, payload)

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
    """AC4, amended 2026-08-09: absent sections are named exactly — on the row.

    This asserted that any absent section failed the PR with no row.  That was
    stricter than the sanity gate's purpose (D2: output that is not a review at
    all) and discarded substantive reviews over heading shape — a 20-PR Opus pass
    lost `discord-assistant#5` for carrying Should Fix and Nice to Have but not
    Must Fix.  A partial set now scores, and the absent names are recorded on the
    row in canonical order, which is what this test still guards.
    """

    def test_missing_section_names_are_recorded_exactly(self):
        # Case A: Nice to Have absent
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stdout, stderr, results_dir, cache_root = run_one_pr_with_payload(
                td, testsupport.review_report(nice_to_have=None)
            )
            self.assertEqual(rc, 0, "a partial section set must not fail the run")

            ledger = run.ledger_path(results_dir)
            rows = [] if not ledger.exists() else [
                json.loads(ln) for ln in ledger.read_text().splitlines()
            ]
            self.assertEqual(len(rows), 1, "a partial section set still scores")
            self.assertEqual(rows[0]["missing_sections"], ["Nice to Have"],
                "Case A: only Nice to Have recorded absent")

        # Case B: Should Fix and Nice to Have absent — canonical order preserved
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stdout, stderr, results_dir, cache_root = run_one_pr_with_payload(
                td, testsupport.review_report(should_fix=None, nice_to_have=None)
            )
            self.assertEqual(rc, 0)

            ledger = run.ledger_path(results_dir)
            rows = [] if not ledger.exists() else [
                json.loads(ln) for ln in ledger.read_text().splitlines()
            ]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["missing_sections"],
                             ["Should Fix", "Nice to Have"],
                "Case B: both recorded, in canonical order, Must Fix absent")


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
                rc, stdout, stderr, results_dir, cache_root = run_one_pr_with_payload(
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


class TestFailedReviewArtifactCarriesBothStreams(unittest.TestCase):
    """AC10 Case A: a non-zero-exit failure artifact contains both stream labels and sentinels."""

    def test_failed_review_artifact_carries_both_streams(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stdout, stderr, results_dir, cache_root, counter = run_one_pr_with_streams(
                td,
                stdout_text="STDOUT-SENTINEL-8F1",
                stderr_text="STDERR-SENTINEL-C3A",
                exit_code=3,
            )

            self.assertEqual(rc, 1, "run must exit 1 when review fails")

            failures = run.failures_root(cache_root)
            self.assertTrue(failures.exists())
            artifact_files = list(failures.glob(f"*{run.FAILURE_ARTIFACT_SUFFIX}"))
            self.assertEqual(len(artifact_files), 1,
                f"exactly one artifact expected, found: {artifact_files}")

            text = artifact_files[0].read_text(encoding="utf-8")

            # Both labels present
            self.assertIn(run.FAILURE_STDOUT_LABEL, text)
            self.assertIn(run.FAILURE_STDERR_LABEL, text)

            # Each sentinel in its own segment (not just anywhere in the file)
            stdout_segment = text.split(run.FAILURE_STDOUT_LABEL)[1].split(run.FAILURE_STDERR_LABEL)[0]
            stderr_segment = text.split(run.FAILURE_STDERR_LABEL)[1]
            self.assertIn("STDOUT-SENTINEL-8F1", stdout_segment)
            self.assertIn("STDERR-SENTINEL-C3A", stderr_segment)

            # Ledger gained 0 rows
            ledger = run.ledger_path(results_dir)
            rows = [] if not ledger.exists() else [
                json.loads(ln) for ln in ledger.read_text().splitlines()
            ]
            self.assertEqual(len(rows), 0, "no ledger row for failed review")

            # No review cache entry
            reviews = run.reviews_root(cache_root)
            review_files = (
                list(reviews.glob("*.json")) + list(reviews.glob("*.stdout.txt"))
                if reviews.exists() else []
            )
            self.assertEqual(len(review_files), 0,
                f"no review cache files expected, found: {review_files}")


class TestFailedReviewArtifactMarksAnEmptyStreamEmpty(unittest.TestCase):
    """AC10 Case B: an artifact for a stderr-only failure marks the empty stdout section."""

    def test_failed_review_artifact_marks_an_empty_stream_empty(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stdout, stderr, results_dir, cache_root, counter = run_one_pr_with_streams(
                td,
                stdout_text="STDOUT-SENTINEL-8F1",
                stderr_text="",
                exit_code=3,
            )

            self.assertEqual(rc, 1)

            failures = run.failures_root(cache_root)
            self.assertTrue(failures.exists())
            artifact_files = list(failures.glob(f"*{run.FAILURE_ARTIFACT_SUFFIX}"))
            self.assertEqual(len(artifact_files), 1)

            text = artifact_files[0].read_text(encoding="utf-8")

            # Both labels present
            self.assertIn(run.FAILURE_STDOUT_LABEL, text)
            self.assertIn(run.FAILURE_STDERR_LABEL, text)

            # stdout segment contains the sentinel
            stdout_segment = text.split(run.FAILURE_STDOUT_LABEL)[1].split(run.FAILURE_STDERR_LABEL)[0]
            self.assertIn("STDOUT-SENTINEL-8F1", stdout_segment)

            # stderr segment is present and marked empty
            stderr_segment = text.split(run.FAILURE_STDERR_LABEL)[1]
            self.assertIn(run.FAILURE_EMPTY_STREAM_MARKER, stderr_segment)
            # The empty marker must appear in the stderr segment, not just anywhere
            self.assertEqual(
                stderr_segment.strip().startswith(run.FAILURE_EMPTY_STREAM_MARKER), True,
                f"stderr segment must start with empty marker: {stderr_segment!r}"
            )


class TestTimeoutFailureArtifactCarriesBothStreams(unittest.TestCase):
    """AC11 unit level: write_failure_artifact handles the mixed bytes/str timeout shape."""

    def test_timeout_failure_artifact_carries_both_streams(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            err = subprocess.TimeoutExpired(
                cmd=["claude"], timeout=1,
                output=b"STDOUT-SENTINEL-8F1", stderr="STDERR-SENTINEL-C3A",
            )
            path = run.write_failure_artifact(
                cache_root, "cfg", "test#1",
                reason="timeout",
                stdout=err.stdout, stderr=err.stderr,
            )
            text = path.read_text(encoding="utf-8")

            self.assertIn(run.FAILURE_STDOUT_LABEL, text)
            self.assertIn(run.FAILURE_STDERR_LABEL, text)
            self.assertIn("STDOUT-SENTINEL-8F1", text)
            self.assertIn("STDERR-SENTINEL-C3A", text)
            self.assertTrue(path.name.endswith(run.FAILURE_ARTIFACT_SUFFIX))
            # Artifact is not a cache entry
            self.assertFalse(
                run.reviews_root(cache_root).exists() or
                list(run.reviews_root(cache_root).glob("*.json")) or
                list(run.reviews_root(cache_root).glob("*.stdout.txt")),
                "artifact must not create a review cache entry"
            )


class TestReviewTimeoutWritesBothStreamArtifact(unittest.TestCase):
    """AC11 real path: a timeout produces an artifact with both streams."""

    def test_review_timeout_writes_a_both_stream_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stdout, stderr, results_dir, cache_root, counter = run_one_pr_with_streams(
                td,
                stdout_text="STDOUT-SENTINEL-8F1",
                stderr_text="STDERR-SENTINEL-C3A",
                sleep_seconds=5,
                timeout_seconds=1,
            )

            self.assertEqual(rc, 1, "run must exit 1 on timeout")
            self.assertIn("failed", stdout)
            self.assertIn("timeout", stdout)

            failures = run.failures_root(cache_root)
            self.assertTrue(failures.exists())
            artifact_files = list(failures.glob(f"*{run.FAILURE_ARTIFACT_SUFFIX}"))
            self.assertEqual(len(artifact_files), 1)

            text = artifact_files[0].read_text(encoding="utf-8")
            self.assertIn(run.FAILURE_STDOUT_LABEL, text)
            self.assertIn(run.FAILURE_STDERR_LABEL, text)

            stdout_segment = text.split(run.FAILURE_STDOUT_LABEL)[1].split(run.FAILURE_STDERR_LABEL)[0]
            stderr_segment = text.split(run.FAILURE_STDERR_LABEL)[1]
            self.assertIn("STDOUT-SENTINEL-8F1", stdout_segment)
            self.assertIn("STDERR-SENTINEL-C3A", stderr_segment)

            # Ledger gained 0 rows
            ledger = run.ledger_path(results_dir)
            rows = [] if not ledger.exists() else [
                json.loads(ln) for ln in ledger.read_text().splitlines()
            ]
            self.assertEqual(len(rows), 0, "no ledger row for timeout")

            # No review cache entry
            reviews = run.reviews_root(cache_root)
            review_files = (
                list(reviews.glob("*.json")) + list(reviews.glob("*.stdout.txt"))
                if reviews.exists() else []
            )
            self.assertEqual(len(review_files), 0)


class TestNonReviewRejectionWritesBothStreamArtifact(unittest.TestCase):
    """AC12: a non-review rejection produces an artifact with both streams."""

    def test_non_review_rejection_writes_a_both_stream_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stdout, stderr, results_dir, cache_root, counter = run_one_pr_with_streams(
                td,
                stdout_text="Unknown command: /coding:pr-review",
                stderr_text="STDERR-SENTINEL-C3A",
                exit_code=0,
            )

            self.assertEqual(rc, 1, "run must exit 1 for non-review")

            failures = run.failures_root(cache_root)
            self.assertTrue(failures.exists())
            artifact_files = list(failures.glob(f"*{run.FAILURE_ARTIFACT_SUFFIX}"))
            self.assertEqual(len(artifact_files), 1)

            text = artifact_files[0].read_text(encoding="utf-8")

            # Both labels present
            self.assertIn(run.FAILURE_STDOUT_LABEL, text)
            self.assertIn(run.FAILURE_STDERR_LABEL, text)

            # Both payloads present
            self.assertIn("Unknown command: /coding:pr-review", text)
            self.assertIn("STDERR-SENTINEL-C3A", text)

            # Ledger gained 0 rows
            ledger = run.ledger_path(results_dir)
            rows = [] if not ledger.exists() else [
                json.loads(ln) for ln in ledger.read_text().splitlines()
            ]
            self.assertEqual(len(rows), 0, "no ledger row for non-review")

            # No review cache entry
            reviews = run.reviews_root(cache_root)
            review_files = (
                list(reviews.glob("*.json")) + list(reviews.glob("*.stdout.txt"))
                if reviews.exists() else []
            )
            self.assertEqual(len(review_files), 0)

            # Gate semantics preserved: NON_REVIEW_MARKER still appears in captured stderr
            self.assertIn(run.NON_REVIEW_MARKER, stderr)
            self.assertIn("missing sections:", stderr)


class TestFailureArtifactIsNotACacheEntry(unittest.TestCase):
    """Artifact is diagnostic only — a second run invokes the review again."""

    def test_failure_artifact_is_not_a_cache_entry(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir1 = td / "results1"
            results_dir1.mkdir(parents=True)
            results_dir2 = td / "results2"
            results_dir2.mkdir(parents=True)
            bin_dir = td / "bin"
            counter = td / "counter"

            stub = testsupport.stub_claude_streams(
                bin_dir, counter,
                stdout_text="STDOUT-SENTINEL-8F1",
                stderr_text="STDERR-SENTINEL-C3A",
                exit_code=3,
            )
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

            # First run — fails and writes artifact
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
            self.assertEqual(rc1, 1)

            # Counter should have one entry
            lines_first = counter.read_text().splitlines()
            self.assertEqual(len(lines_first), 1)

            # Second run — review must be invoked again (not cached)
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
            self.assertEqual(rc2, 1)

            # Counter must have two entries (no cache hit)
            lines_second = counter.read_text().splitlines()
            self.assertEqual(len(lines_second), 2,
                "review must be invoked on second run — artifact is not a cache entry")

            # Both runs' ledgers are empty
            for rd in [results_dir1, results_dir2]:
                ledger = run.ledger_path(rd)
                rows = [] if not ledger.exists() else [
                    json.loads(ln) for ln in ledger.read_text().splitlines()
                ]
                self.assertEqual(len(rows), 0,
                    f"no ledger rows for failed runs in {rd}")


class TestCaptureFixturesMatchPublishedDigests(unittest.TestCase):
    """AC2: four operator-installed verbatim capture fixtures match their published digests."""

    FIXTURES = [
        ("bench/testdata/capture-notes-block-h2.md",
         "6427028bef301ff822cca6dbf9308896f1899ac5a972ed3fddc276f2216552b9",
         17),
        ("bench/testdata/capture-numbered-findings-h3.md",
         "5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93",
         28),
        ("bench/testdata/capture-traceability-h4.md",
         "2922746bb95bdb3a67a683942531362271d8f3ccd558067d910146e054bcfe7c",
         57),
        ("bench/testdata/capture-summary-trailer-h4.md",
         "36e15eca61133033d81687f87a82b044333c6a7465508d1757f8493361137e79",
         21),
    ]

    def test_each_fixture_matches_its_published_sha256_and_line_count(self):
        for rel_path, expected_sha256, expected_lines in self.FIXTURES:
            with self.subTest(fixture=rel_path):
                path = run.BENCH_DIR / rel_path.replace("bench/", "")
                observed_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
                observed_lines = len(path.read_text().splitlines())
                self.assertEqual(
                    observed_sha256, expected_sha256,
                    f"fixture {rel_path}: expected sha256 {expected_sha256}, got {observed_sha256}"
                )
                self.assertEqual(
                    observed_lines, expected_lines,
                    f"fixture {rel_path}: expected {expected_lines} lines, got {observed_lines}"
                )


class TestNotesBlockCaptureHarvestsToNothing(unittest.TestCase):
    """AC3: trailing notes block harvests to nothing at all."""

    def test_notes_block_capture_harvests_to_empty_findings_and_empty_unattributable(self):
        text = (run.BENCH_DIR / "testdata" / "capture-notes-block-h2.md").read_text()
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(text, ids)
        self.assertEqual(
            result.findings, [],
            f"notes-block capture must yield empty findings, got: {result.findings}"
        )
        self.assertEqual(
            result.unattributable, [],
            f"notes-block capture must yield empty unattributable, got: {result.unattributable}"
        )


class TestBoldLabelTerminatorIsGeneral(unittest.TestCase):
    """AC4: bold-run terminator is general, not a hardcoded label."""

    def test_case_a_notes_block_with_three_bullets_yields_nothing(self):
        report = (
            "## Must Fix (Critical)\n"
            "None.\n"
            "\n"
            "**Notes:**\n"
            "- precommit skipped\n"
            "- npm ci was not run\n"
            "- LICENSE file present\n"
        )
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(result.findings, [],
            f"Case A: expected empty findings, got: {result.findings}")
        self.assertEqual(result.unattributable, [],
            f"Case A: expected empty unattributable, got: {result.unattributable}")

    def test_case_b_summary_label_with_prose_and_bullet_yields_nothing(self):
        report = (
            "## Must Fix (Critical)\n"
            "None.\n"
            "\n"
            "**Summary:** This is a closing panel.\n"
            "- precommit skipped\n"
        )
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(result.findings, [],
            f"Case B: expected empty findings, got: {result.findings}")
        self.assertEqual(result.unattributable, [],
            f"Case B: expected empty unattributable, got: {result.unattributable}")

    def test_case_c_one_real_finding_before_notes_block_yields_only_that_finding(self):
        report = (
            "## Must Fix (Critical)\n"
            "- **`src/foo.py:7`** the one real finding, which must survive.\n"
            "\n"
            "**Notes:**\n"
            "- this bullet must not appear\n"
            "- nor this one\n"
        )
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(len(result.findings), 1,
            f"Case C: expected exactly 1 finding, got: {result.findings}")
        self.assertEqual(result.unattributable, [],
            f"Case C: expected empty unattributable, got: {result.unattributable}")
        self.assertEqual(result.findings[0]["path"], "src/foo.py")
        self.assertEqual(result.findings[0]["line"], 7)
        self.assertIn("the one real finding", result.findings[0]["body"])
        self.assertNotIn("this bullet must not appear", result.findings[0]["body"])
        self.assertNotIn("nor this one", result.findings[0]["body"])


class TestContentOutsideASeveritySectionIsNeverAFinding(unittest.TestCase):
    """AC10: content outside a severity section is never a finding and never unattributable."""

    def test_case_a_numbered_findings_positive_notes_bullets_not_in_harvest(self):
        # Substrings that occur exactly once in the ### Positive notes bullets:
        #   fixture line 23: "build-backend switch is clean"
        #   fixture line 24: "mktemp"
        #   fixture line 25: "S104"
        #   fixture line 26: "TestClient"
        # Each was chosen because it occurs exactly once in the fixture and that
        # one occurrence is inside a ### Positive notes bullet.  "hatchling" and
        # "pip-audit" are disqualified: "hatchling" appears twice (line 20 is a
        # Nice to Have finding, line 23 is positive notes); "pip-audit" appears
        # three times (lines 15, 24, 24).  "ruff " appears twice (lines 5, 25).
        text = (run.BENCH_DIR / "testdata" / "capture-numbered-findings-h3.md").read_text()
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(text, ids)

        self.assertTrue(
            result.findings or result.unattributable,
            "corpus is non-degenerate: harvest returned something"
        )

        # All four positive-notes substrings must be absent from both components
        positive_substrings = (
            "build-backend switch is clean",  # line 23
            "mktemp",                         # line 24
            "S104",                           # line 25
            "TestClient",                     # line 26
        )
        for substr in positive_substrings:
            for finding in result.findings:
                self.assertNotIn(
                    substr, finding["body"],
                    f"substring {substr!r} must not appear in findings body"
                )
            for item in result.unattributable:
                self.assertNotIn(
                    substr, item.get("body", ""),
                    f"substring {substr!r} must not appear in unattributable body"
                )

    def test_case_b_traceability_table_rule_ids_not_in_harvest(self):
        text = (run.BENCH_DIR / "testdata" / "capture-traceability-h4.md").read_text()
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(text, ids)

        # Collect rule IDs from the traceability table (fixture lines 33-54, 22 rows)
        table_ids = re.findall(r"^\| ([a-z][a-z0-9/-]+) \|", text, re.MULTILINE)
        self.assertEqual(
            len(table_ids), 22,
            f"traceability table must have 22 rows, got: {len(table_ids)} — "
            "check regex anchoring (re.MULTILINE required)"
        )

        for finding in result.findings:
            self.assertNotIn(
                finding.get("rule_id"), table_ids,
                f"rule_id {finding.get('rule_id')!r} must not come from traceability table"
            )

    def test_case_c_both_zero_finding_captures_harvest_to_empty(self):
        for rel_path in (
            "bench/testdata/real-capture-report.md",
            "bench/testdata/capture-summary-trailer-h4.md",
        ):
            with self.subTest(fixture=rel_path):
                text = (run.BENCH_DIR / rel_path.replace("bench/", "")).read_text()
                ids = run.load_rule_ids(run.REPO_ROOT)
                result = run.harvest(text, ids)
                self.assertEqual(
                    result.findings, [],
                    f"{rel_path}: expected empty findings, got: {result.findings}"
                )
                self.assertEqual(
                    result.unattributable, [],
                    f"{rel_path}: expected empty unattributable, got: {result.unattributable}"
                )


class TestHeadingLevelIsIrrelevantToTermination(unittest.TestCase):
    """AC14: heading level is irrelevant to termination and harvesting."""

    def test_heading_level_does_not_change_harvest_at_different_levels(self):
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        real_rule_id = next((rid for rid in known_ids if "/" in rid), None)
        self.assertIsNotNone(real_rule_id)

        # Render identical content at ##, ###, #### — each carrying one finding followed
        # by a **Notes:** block and two more bullets.  The finding must appear at every
        # level, and all three harvests must be equal.
        def make_report(level):
            return (
                f"{level} Must Fix (Critical)\n"
                f"- **`src/foo.py:7`** a finding that must appear at every level.\n"
                f"\n"
                f"**Notes:**\n"
                f"- this bullet must not appear\n"
                f"- nor this one\n"
            )

        results = {lvl: run.harvest(make_report(lvl), known_ids) for lvl in ("##", "###", "####")}
        findings = {lvl: r.findings for lvl, r in results.items()}

        # Per-level assertions — each level must yield exactly one finding
        for lvl in ("##", "###", "####"):
            with self.subTest(level=lvl):
                self.assertEqual(len(findings[lvl]), 1,
                    f"{lvl}: expected exactly 1 finding, got: {findings[lvl]}")
                self.assertEqual(findings[lvl][0]["path"], "src/foo.py")
                self.assertEqual(findings[lvl][0]["line"], 7)
                self.assertEqual(results[lvl].unattributable, [],
                    f"{lvl}: expected empty unattributable, got: {results[lvl].unattributable}")

        # Three-way equality — empty results compare equal, so per-level assertions
        # are required alongside this equality check
        self.assertEqual(
            findings["##"], findings["###"],
            f"## vs ###: {findings['##']} vs {findings['###']}"
        )
        self.assertEqual(
            findings["##"], findings["####"],
            f"## vs ####: {findings['##']} vs {findings['####']}"
        )

    def test_h3_terminates_open_h2_section(self):
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        real_rule_id = next((rid for rid in known_ids if "/" in rid), None)
        self.assertIsNotNone(real_rule_id)

        report = (
            "## Must Fix (Critical)\n"
            f"- `{real_rule_id}`: a real finding in file.go:99\n"
            "### Some other heading\n"
            "- this bullet must not appear\n"
        )
        result = run.harvest(report, known_ids)
        self.assertEqual(len(result.findings), 1,
            f"expected exactly 1 finding, got: {result.findings}")

    def test_h2_terminates_open_h4_section(self):
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        real_rule_id = next((rid for rid in known_ids if "/" in rid), None)
        self.assertIsNotNone(real_rule_id)

        report = (
            "#### Must Fix (Critical)\n"
            f"- `{real_rule_id}`: a real finding in file.go:99\n"
            "## Some other heading\n"
            "- this bullet must not appear\n"
        )
        result = run.harvest(report, known_ids)
        self.assertEqual(len(result.findings), 1,
            f"expected exactly 1 finding, got: {result.findings}")


class TestOrderedAndUnorderedItemsBothOpenFindings(unittest.TestCase):
    """AC6: ordered and unordered list items both open findings, in document order."""

    def test_ordered_and_unordered_items_yield_findings_in_document_order(self):
        # Mixing unordered (-, *) and ordered (3., 4., 10.) styles.
        # Ordered numbering starts at 3 and includes a two-digit marker.
        # Every item carries a path in backticks so paths are extractable (prompt 3).
        report = (
            "## Must Fix (Critical)\n"
            "- **`a/one.py:1`** first item, unordered dash.\n"
            "* **`a/two.py:2`** second item, unordered star.\n"
            "3. **`a/three.py:3`** third item, ordered starting at three.\n"
            "4. **`a/four.py:4`** fourth item.\n"
            "10. **`a/ten.py:10`** fifth item, two-digit marker.\n"
        )
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        findings = result.findings

        self.assertEqual(
            len(findings), 5,
            f"expected 5 findings, got {len(findings)}: {[f['body'] for f in findings]}"
        )
        paths = [f["path"] for f in findings]
        self.assertEqual(
            paths, ["a/one.py", "a/two.py", "a/three.py", "a/four.py", "a/ten.py"],
            f"paths must be in document order, got: {paths}"
        )

    def test_ordered_item_inside_fence_yields_nothing(self):
        # An ordered item inside a fenced block is example text, not a finding.
        # Both findings and unattributable must be empty.
        report = (
            "## Should Fix (Important)\n"
            "None.\n"
            "\n"
            "```\n"
            "1. this ordered item is inside a fence and is not a finding\n"
            "```\n"
        )
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(
            result.findings, [],
            f"expected empty findings, got: {result.findings}"
        )
        self.assertEqual(
            result.unattributable, [],
            f"expected empty unattributable (not an unattributable item), got: {result.unattributable}"
        )


class TestBodyPreservesLeadingBoldRun(unittest.TestCase):
    """AC9: the list-item body preserves a leading bold run verbatim."""

    def test_traceability_capture_bold_run_survives_normalization(self):
        text = (run.BENCH_DIR / "testdata" / "capture-traceability-h4.md").read_text()
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(text, ids)

        self.assertEqual(
            len(result.findings), 1,
            f"expected 1 finding, got {len(result.findings)}: {[f['body'] for f in result.findings]}"
        )
        observed_body = result.findings[0]["body"]
        self.assertTrue(
            observed_body.startswith("**No test coverage for"),
            f"leading bold run was mangled, got: {observed_body[:60]!r}"
        )
        self.assertEqual(
            result.unattributable, [],
            f"expected empty unattributable, got: {result.unattributable}"
        )
        # AC9 completion: path is read from the leading bold reference
        self.assertEqual(
            result.findings[0]["path"], "src/config.ts",
            f"expected path src/config.ts from leading bold reference, got: {result.findings[0]['path']}"
        )


class TestNumberedCaptureFindingsCarryAttribution(unittest.TestCase):
    """AC5: the five previously-dropped numbered findings carry the capture's attribution."""

    def test_numbered_capture_findings_carry_attribution(self):
        text = (run.BENCH_DIR / "testdata" / "capture-numbered-findings-h3.md").read_text()
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(text, ids)

        expected = [
            ("CHANGELOG.md", 18, "changelog/conventional-prefix-required"),
            ("README.md", 76, "readme/user-facing-not-agent-context"),
            (".github/workflows/ci.yml", 32, None),
            ("Makefile.precommit", None, None),
            ("Makefile.precommit", None, None),
        ]
        observed = [(f["path"], f["line"], f["rule_id"]) for f in result.findings[:5]]
        self.assertEqual(
            observed, expected,
            f"first five findings: expected {expected}, got: {observed}"
        )
        self.assertEqual(
            len(result.findings), 5,
            f"expected 5 total findings, got: {len(result.findings)}"
        )


class TestRuleIdComesFromTheItemsOwnMarkers(unittest.TestCase):
    """AC7: rule_id comes from the item's own markers in priority order."""

    def test_case_a_tag_with_unknown_id_yields_literal(self):
        # Case A: an item tagged with an id absent from rules/index.json yields that literal
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        self.assertNotIn(
            "made-up/not-in-the-index", known_ids,
            "test precondition: made-up/not-in-the-index must not be in the index"
        )

        report = (
            "## Must Fix (Critical)\n"
            "- **`src/x.py:1`** something is wrong here. *(rule: `made-up/not-in-the-index`)*\n"
        )
        result = run.harvest(report, known_ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            result.findings[0]["rule_id"], "made-up/not-in-the-index",
            f"Case A: expected literal rule_id, got: {result.findings[0]['rule_id']}"
        )

    def test_case_b_prose_names_different_rule_before_marker_yields_marker(self):
        # Case B: prose names a different real rule before the item's own marker
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        real_ids = sorted(known_ids)
        id_a, id_b = real_ids[0], real_ids[1] if len(real_ids) > 1 else real_ids[0]
        if id_a == id_b:
            id_b = next((r for r in known_ids if r != id_a), id_a)
        self.assertNotEqual(id_a, id_b, "test needs two distinct rule IDs")

        report = (
            f"## Must Fix (Critical)\n"
            f"- **{id_a}** is wrong here. *(rule: `{id_b}`)*\n"
        )
        result = run.harvest(report, known_ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            result.findings[0]["rule_id"], id_b,
            f"Case B: expected marker id {id_b}, got: {result.findings[0]['rule_id']}"
        )

    def test_case_c_no_marker_head_token_in_index_yields_that_id(self):
        # Case C: no marker, head-anchored backtick token IS in index
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        real_id = next((rid for rid in known_ids if "/" in rid), None)
        self.assertIsNotNone(real_id, "test needs a real rule ID with a slash")

        report = (
            f"## Must Fix (Critical)\n"
            f"- `{real_id}`: a finding in src/x.py:1\n"
        )
        result = run.harvest(report, known_ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            result.findings[0]["rule_id"], real_id,
            f"Case C: expected head token {real_id}, got: {result.findings[0]['rule_id']}"
        )

    def test_case_d_no_marker_head_token_not_in_index_yields_none(self):
        # Case D: no marker, head-anchored backtick token NOT in index
        known_ids = run.load_rule_ids(run.REPO_ROOT)
        self.assertNotIn(
            "not-a-real-rule-id", known_ids,
            "test precondition: not-a-real-rule-id must not be in the index"
        )

        report = (
            "## Must Fix (Critical)\n"
            "- `not-a-real-rule-id`: a finding in src/x.py:7\n"
        )
        result = run.harvest(report, known_ids)
        self.assertEqual(len(result.findings), 1)
        self.assertIsNone(
            result.findings[0]["rule_id"],
            f"Case D: expected rule_id None, got: {result.findings[0]['rule_id']}"
        )
        self.assertEqual(
            result.findings[0]["path"], "src/x.py",
            f"Case D: expected path src/x.py, got: {result.findings[0]['path']}"
        )
        self.assertEqual(
            result.findings[0]["line"], 7,
            f"Case D: expected line 7, got: {result.findings[0]['line']}"
        )


class TestPathAndLineComeFromTheLeadingBoldReference(unittest.TestCase):
    """AC8: path and line come from the leading bold reference."""

    def test_changelog_dot_md_colon_18(self):
        report = "## Must Fix (Critical)\n- **`CHANGELOG.md:18`** something.\n"
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            (result.findings[0]["path"], result.findings[0]["line"]),
            ("CHANGELOG.md", 18),
            f"expected (CHANGELOG.md, 18), got: ({result.findings[0]['path']}, {result.findings[0]['line']})"
        )

    def test_readme_md_with_lines_76_to_94(self):
        report = "## Must Fix (Critical)\n- **`README.md` \"Security gates\" section (~lines 76-94)** something.\n"
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            (result.findings[0]["path"], result.findings[0]["line"]),
            ("README.md", 76),
            f"expected (README.md, 76), got: ({result.findings[0]['path']}, {result.findings[0]['line']})"
        )

    def test_github_workflows_ci_yml_colon_32(self):
        report = "## Must Fix (Critical)\n- **`.github/workflows/ci.yml:32`** something.\n"
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            (result.findings[0]["path"], result.findings[0]["line"]),
            (".github/workflows/ci.yml", 32),
            f"expected (.github/workflows/ci.yml, 32), got: ({result.findings[0]['path']}, {result.findings[0]['line']})"
        )

    def test_ci_plus_makefile_precommit(self):
        report = "## Must Fix (Critical)\n- **CI + `Makefile.precommit`** something.\n"
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            (result.findings[0]["path"], result.findings[0]["line"]),
            ("Makefile.precommit", None),
            f"expected (Makefile.precommit, None), got: ({result.findings[0]['path']}, {result.findings[0]['line']})"
        )

    def test_leading_bold_takes_precedence_over_trailing_prose(self):
        # Negative case: leading bold names a/b.py:10, trailing prose mentions c/d.py:99
        report = (
            "## Must Fix (Critical)\n"
            "- **`a/b.py:10`** something is wrong.\n"
            "More prose here, mentioning c/d.py:99 in passing.\n"
        )
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            (result.findings[0]["path"], result.findings[0]["line"]),
            ("a/b.py", 10),
            f"expected (a/b.py, 10) from leading bold, got: ({result.findings[0]['path']}, {result.findings[0]['line']})"
        )

    def test_bold_run_with_path_only_ignores_trailing_line_prose(self):
        # Negative case: leading bold names a/b.py only, prose mentions line 42
        report = (
            "## Must Fix (Critical)\n"
            "- **`a/b.py`** something is wrong.\n"
            "More prose here, referencing line 42.\n"
        )
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            (result.findings[0]["path"], result.findings[0]["line"]),
            ("a/b.py", None),
            f"expected (a/b.py, None) — line in prose is not used when bold supplies path, got: ({result.findings[0]['path']}, {result.findings[0]['line']})"
        )

    def test_bold_run_without_line_does_not_use_trailing_full_path_line(self):
        # Discriminating negative case: leading bold names a/b.py only, trailing prose
        # carries a full c/d.py:99 reference — the trailing reference must NOT be used
        report = (
            "## Must Fix (Critical)\n"
            "- **`a/b.py`** something is wrong.\n"
            "More prose here, mentioning c/d.py:99 in passing.\n"
        )
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            (result.findings[0]["path"], result.findings[0]["line"]),
            ("a/b.py", None),
            f"expected (a/b.py, None) — trailing c/d.py:99 must not be used when bold already supplied path, got: ({result.findings[0]['path']}, {result.findings[0]['line']})"
        )


class TestExtractedValuesAreDataNotPaths(unittest.TestCase):
    """Safety: extracted path values are never opened or accessed as filesystem paths."""

    def test_etc_passwd_path_is_recorded_without_filesystem_access(self):
        # A finding emitting ../../etc/passwd:1 must produce a ledger row with that
        # string and no filesystem access.
        report = "## Must Fix (Critical)\n- **`../../etc/passwd:1`** something.\n"
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(report, ids)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(
            result.findings[0]["path"], "../../etc/passwd",
            f"expected ../../etc/passwd, got: {result.findings[0]['path']}"
        )
        self.assertEqual(result.findings[0]["line"], 1)


class TestTraceabilityTableDoesNotContributeRuleIds(unittest.TestCase):
    """AC10 Case B regression: rule ids from a traceability table outside sections are not attributed."""

    def test_traceability_capture_rule_ids_not_from_table(self):
        text = (run.BENCH_DIR / "testdata" / "capture-traceability-h4.md").read_text()
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(text, ids)

        # The 22-row traceability table is outside any severity section.
        # No finding should carry a rule_id from that table.
        table_ids = re.findall(r"^\| ([a-z][a-z0-9/-]+) \|", text, re.MULTILINE)
        self.assertEqual(
            len(table_ids), 22,
            f"traceability table must have 22 rows, got: {len(table_ids)}"
        )
        for finding in result.findings:
            if finding.get("rule_id") is not None:
                self.assertNotIn(
                    finding["rule_id"], table_ids,
                    f"rule_id {finding['rule_id']!r} must not come from traceability table"
                )


# ----------------------------------------------------------------------
# Tests for the unattributable-item gate (spec 005 AC11, AC12, AC13)
# ----------------------------------------------------------------------
class TestNiceToHaveBulletsAreReportedUnattributable(unittest.TestCase):
    """AC13: the unattributed items in the real capture are reported as such."""

    def test_nice_to_have_bullets_reported_unattributable(self):
        text = (run.BENCH_DIR / "testdata" / "capture-numbered-findings-h3.md").read_text()
        ids = run.load_rule_ids(run.REPO_ROOT)
        result = run.harvest(text, ids)

        self.assertEqual(
            len(result.unattributable), 2,
            f"expected 2 unattributable items, got: {len(result.unattributable)}"
        )
        for u in result.unattributable:
            self.assertEqual(
                u["section"], "Nice to Have",
                f"section must be 'Nice to Have', got: {u['section']}"
            )

        # Verify verbatim bodies (whitespace-collapsed as harvest does)
        self.assertEqual(
            result.unattributable[0]["body"],
            "Manual Trivy apt-install (update/install/repo-key) duplicates the maintained `aquasecurity/setup-trivy` action — adds ~30-60s/run and maintenance surface with no caching/pinning."
        )
        self.assertEqual(
            result.unattributable[1]["body"],
            "Commit subject `switch build backend to hatchling and add conventional changelog prefixes` is 73 chars (soft cap 50) — FYI only, not in the active rule set."
        )

        # The five Should Fix findings are still present
        expected = [
            ("CHANGELOG.md", 18, "changelog/conventional-prefix-required"),
            ("README.md", 76, "readme/user-facing-not-agent-context"),
            (".github/workflows/ci.yml", 32, None),
            ("Makefile.precommit", None, None),
            ("Makefile.precommit", None, None),
        ]
        observed = [(f["path"], f["line"], f["rule_id"]) for f in result.findings[:5]]
        self.assertEqual(observed, expected)


class TestUnattributableItemFailsThePrLoudly(unittest.TestCase):
    """AC11, amended 2026-08-09: an unattributable item is reported loudly and dropped.

    This asserted that the whole PR failed with no row.  That granularity cost a
    20-PR Opus pass 4 of its 7 lost rows, one of them over a single item among a
    full set of valid findings.  The contract is now: report loudly on stderr,
    drop the item, keep the row, and record the count so the loss is measurable
    rather than silent.  The loud diagnosis below is unchanged and still asserted.
    """

    def test_unattributable_item_is_reported_loudly_and_dropped(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stdout, stderr, results_dir, cache_root = run_one_pr_with_payload(
                td,
                testsupport.review_report(
                    should_fix="- an item with neither a file reference nor a rule tag, so it cannot be keyed."
                ),
            )

            # The run now succeeds — the item is dropped, not the row
            self.assertEqual(rc, 0, "dropping an item must not fail the run")

            # The frozen literal appears in stderr
            self.assertIn("UNATTRIBUTABLE FINDING", stderr)
            self.assertEqual(
                run.UNATTRIBUTABLE_MARKER, "UNATTRIBUTABLE FINDING",
                "UNATTRIBUTABLE_MARKER is a frozen spec invariant"
            )
            # PR id and section name in diagnosis
            self.assertIn("test#1", stderr)
            self.assertIn("Should Fix", stderr)
            # Item text verbatim
            self.assertIn(
                "an item with neither a file reference nor a rule tag",
                stderr,
            )

            # No ledger row
            ledger = run.ledger_path(results_dir)
            if ledger.exists():
                rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
            else:
                rows = []
            self.assertEqual(len(rows), 1, "the row survives an unattributable item")
            self.assertEqual(rows[0]["unattributable_count"], 1,
                             "the dropped item must be counted, never dropped silently")

            # Exactly one file under reviews_root: the raw stdout, no .json marker
            reviews = run.reviews_root(cache_root)
            if reviews.exists():
                stdout_files = list(reviews.glob("*.stdout.txt"))
                json_files = list(reviews.glob("*.json"))
            else:
                stdout_files, json_files = [], []
            self.assertEqual(
                len(stdout_files), 1,
                "exactly one .stdout.txt file expected (the raw capture)"
            )
            self.assertEqual(
                len(json_files), 1,
                "a row marker is written now that the row survives"
            )

            # No failure artifact: the PR did not fail.  The diagnosis lives on
            # stderr (asserted above) and the loss is quantified by
            # unattributable_count on the row (asserted above).  Writing a
            # "failure" artifact for a run that succeeded would misfile it.
            failures = run.failures_root(cache_root)
            failure_files = list(failures.glob("*")) if failures.exists() else []
            self.assertEqual(
                len(failure_files), 0,
                "no failure artifact — the item was dropped, the PR was not"
            )

            # Stdout summary counts the PR as ok
            self.assertIn("1 ok", stdout)


class TestAttributedItemStillProducesARow(unittest.TestCase):
    """AC12: an item with a path reference exits 0 and produces a row and cache marker."""

    def test_attributed_item_still_produces_a_row(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            rc, stdout, stderr, results_dir, cache_root = run_one_pr_with_payload(
                td,
                testsupport.review_report(
                    should_fix="- **`src/x.py:4`** an item with a file reference and no rule tag."
                ),
            )

            # Run must succeed
            self.assertEqual(rc, 0, "run must exit 0 for attributed item")

            # One ledger row with the finding
            ledger = run.ledger_path(results_dir)
            rows = [json.loads(ln) for ln in ledger.read_text().splitlines()]
            self.assertEqual(len(rows), 1, "exactly 1 ledger row expected")
            self.assertEqual(rows[0]["findings"][0]["path"], "src/x.py")
            self.assertEqual(rows[0]["findings"][0]["line"], 4)

            # Two files under reviews_root: raw stdout + one json marker
            reviews = run.reviews_root(cache_root)
            stdout_files = list(reviews.glob("*.stdout.txt"))
            json_files = list(reviews.glob("*.json"))
            self.assertEqual(len(stdout_files), 1, "one .stdout.txt file expected (the raw capture)")
            self.assertEqual(
                len(json_files), 1,
                "exactly one .json row marker for attributed review"
            )


class TestWorktreeReleasedAfterReview(unittest.TestCase):
    """A finished PR leaves no working copy behind, however the review ended.

    The leak these cover is not hypothetical: teardown used to happen only at the
    *start* of the next run for the same PR, so a completed bench left one checkout
    per PR on disk indefinitely — and each checkout accumulated whatever the review
    made the reviewed repo's own tooling produce (.venv, node_modules, build output).
    A five-PR manifest reached 941MB that way, against roughly 1MB of git objects
    per repo.  The failure paths never tore anything down at all.
    """

    def _wt(self, cache_root):
        return run.worktree_dir(cache_root, "testowner", "repo_a", 1)

    def test_failed_review_leaves_no_worktree(self):
        """Review exits non-zero → run_bench raises → the checkout is still gone.

        This is the path that leaked worst: it took the raising branch out of
        process_pr, so no teardown ran until that same PR was reviewed again.
        """
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            manifest_path = testsupport.seed_one_pr_manifest(td, cache_root)

            plugin_src = testsupport.build_coding_repo(td / "repo")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

            bin_dir = td / "bin"
            counter = td / "counter"
            testsupport.stub_claude_failing(bin_dir, counter, exit_code=3)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            old_path = os.environ.get("PATH", "")
            old_home = os.environ.get("HOME", "")
            try:
                os.environ["PATH"] = env["PATH"]
                os.environ["HOME"] = str(td)
                # run_bench absorbs a per-PR failure and reports it in its summary
                # rather than propagating, so this returns normally with 1 failed.
                run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=td / "results",
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )
            finally:
                os.environ["PATH"] = old_path
                os.environ["HOME"] = old_home

            # The stub must actually have been reached — otherwise this test would
            # pass simply because no worktree was ever created.
            self.assertTrue(
                counter.exists() and counter.read_text().strip(),
                "review was never invoked; the assertion below would be vacuous",
            )
            wt = self._wt(cache_root)
            self.assertFalse(
                wt.exists(),
                f"failed review left a working copy behind at {wt}",
            )

    def test_cleanup_removes_untracked_build_artifacts(self):
        """Teardown deletes the directory, not just the files git tracks.

        `git worktree remove` alone refuses or leaves content when the tree carries
        untracked files, which is precisely the shape a review produces.
        """
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            testsupport.seed_one_pr_manifest(td, cache_root)
            repo_dir = cache_root / "repos" / "testowner" / "repo_a"

            entry = json.loads(
                (td / "manifest.json").read_text(encoding="utf-8")
            )["prs"][0]
            checkout = run.resolve_pr(cache_root, entry)
            wt = checkout.worktree
            self.assertTrue(wt.exists(), "fixture failed: no worktree to clean up")

            # Exactly what a Python review leaves behind: an untracked tree git
            # has no knowledge of.
            venv = wt / ".venv" / "lib"
            venv.mkdir(parents=True, exist_ok=True)
            (venv / "payload.bin").write_bytes(b"x" * 4096)

            run.remove_worktree(cache_root, repo_dir, wt, checkout.head_branch)

            self.assertFalse(
                wt.exists(),
                f"untracked build artifacts survived teardown at {wt}",
            )


if __name__ == "__main__":
    unittest.main()


class TestGatesRejectItemsNotRows(unittest.TestCase):
    """A partial defect costs the offending item, never the whole review.

    Both gates used to `raise BenchError` on the whole PR.  A 20-PR Opus pass on
    2026-08-09 lost 7 of 20 rows that way — 4 to attribution, 3 to the sanity
    gate — including `tts-mcp#10`, which lost a full review to ONE unattributable
    item.  The 35% loss rate left a fixture curated for 20 PRs yielding 13, which
    defeated the reason it was curated.
    """

    def _run_one(self, td, review_text):
        """Run the bench over a single seeded PR with a stub emitting review_text."""
        cache_root = td / "cache"
        manifest_path = testsupport.seed_one_pr_manifest(td, cache_root)
        plugin_src = testsupport.build_coding_repo(td / "repo")
        cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)
        bin_dir = td / "bin"
        testsupport.stub_claude(bin_dir, td / "counter", review_text)
        env = testsupport.with_path(bin_dir)
        old_path, old_home = os.environ.get("PATH", ""), os.environ.get("HOME", "")
        try:
            os.environ["PATH"], os.environ["HOME"] = env["PATH"], str(td)
            run.run_bench(
                coding_repo=plugin_src, manifest_path=manifest_path,
                results_dir=td / "results", cache_root=cache_root,
                model="test-model", effort="high", mode="short", config_dir=cfg,
            )
        finally:
            os.environ["PATH"], os.environ["HOME"] = old_path, old_home
        ledger = (td / "results" / "results.jsonl")
        if not ledger.exists():
            return []
        return [json.loads(l) for l in
                ledger.read_text(encoding="utf-8").splitlines() if l.strip()]

    def test_one_unattributable_item_does_not_discard_the_row(self):
        """A review with valid findings plus one unkeyable item still scores.

        Reproduces `tts-mcp#10`: one item among many cost the entire review.
        """
        review = (
            "## Must Fix\n\n"
            "- **`pkg/foo.go:12`** — nil deref on the error path.\n"
            "- Consider tightening the release process generally.\n"
            "\n## Should Fix\n\nNone.\n"
            "\n## Nice to Have\n\nNone.\n"
        )
        with tempfile.TemporaryDirectory() as td:
            rows = self._run_one(pathlib.Path(td), review)
        self.assertEqual(len(rows), 1,
                         "a single unattributable item must not discard the row")
        row = rows[0]
        self.assertEqual(row["unattributable_count"], 1,
                         "the dropped item must be counted, never dropped silently")
        self.assertTrue(row["findings"], "the attributable finding must survive")
        for f in row["findings"]:
            self.assertTrue(f.get("path"),
                            "every scored finding must still carry a matching key")

    def test_partial_section_set_still_scores_and_records_the_gap(self):
        """Two of three severity sections is a real review, not a non-review.

        Reproduces `discord-assistant#5`, discarded for lacking `Must Fix` while
        carrying the other two.
        """
        review = (
            "## Should Fix\n\n"
            "- **`pkg/bar.go:8`** — unchecked type assertion.\n"
            "\n## Nice to Have\n\nNone.\n"
        )
        with tempfile.TemporaryDirectory() as td:
            rows = self._run_one(pathlib.Path(td), review)
        self.assertEqual(len(rows), 1,
                         "a partial section set must not be treated as a non-review")
        self.assertIn("Must Fix", rows[0]["missing_sections"],
                      "the absent section must be recorded on the row")

    def test_output_with_no_sections_at_all_is_still_rejected(self):
        """The D2 case must keep failing: no sections means it is not a review.

        Without this, loosening the sanity gate would re-open the defect it was
        built for — an unknown command whose output read as a clean review.
        """
        with tempfile.TemporaryDirectory() as td:
            rows = self._run_one(pathlib.Path(td), "Unknown command: /coding:pr-review\n")
        self.assertEqual(rows, [],
                         "output carrying no severity section must produce no row")
