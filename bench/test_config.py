#!/usr/bin/env python3
"""Unit tests for bench/run.py — AC6, AC9, AC11 and related container tests."""

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


class TestContentHash(unittest.TestCase):
    """AC6: content hash is content-derived, not commit-derived."""

    def test_content_hash_ignores_git_history_and_dirty_tree(self):
        """Two dirs with byte-identical rules/+commands/ but different git history
        produce the same hash.  Mutating one byte produces a different hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_a = testsupport.build_coding_repo(
                pathlib.Path(tmpdir) / "a",
                rules={"go/sample.yml": "id: go/sample\nlevel: MUST\n"},
                commands={"sample.md": "# Sample\n"},
            )
            # Build a second directory that is byte-identical in rules/+commands/
            b_root = pathlib.Path(tmpdir) / "b"
            b_root.mkdir()
            (b_root / ".git").mkdir()
            (b_root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (b_root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
            (b_root / "junk.txt").write_text("untracked garbage\n", encoding="utf-8")
            testsupport.build_coding_repo(
                b_root,
                rules={"go/sample.yml": "id: go/sample\nlevel: MUST\n"},
                commands={"sample.md": "# Sample\n"},
            )

            h_a = run.content_hash(repo_a)
            h_b = run.content_hash(b_root)
            print(f"hash_a={h_a}")
            print(f"hash_b={h_b}")
            self.assertEqual(h_a, h_b)

            # Mutate one byte — hash must change
            rules_file = repo_a / "rules" / "go" / "sample.yml"
            original = rules_file.read_bytes()
            mutated = original.replace(b"MUST", b"WONT")
            rules_file.write_bytes(mutated)
            h_mutated = run.content_hash(repo_a)
            print(f"hash_mutated={h_mutated}")
            self.assertNotEqual(h_a, h_mutated)

    def test_content_hash_is_order_independent(self):
        """Files created in reverse order produce the same hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_a = testsupport.build_coding_repo(
                pathlib.Path(tmpdir) / "a",
                rules={"go/a.yml": "id: go/a\n", "go/b.yml": "id: go/b\n"},
                commands={"x.md": "# x\n", "y.md": "# y\n"},
            )
            repo_b = pathlib.Path(tmpdir) / "b"
            # Create in opposite order
            (repo_b / "commands").mkdir(parents=True)
            (repo_b / "commands" / "y.md").write_text("# y\n", encoding="utf-8")
            (repo_b / "commands" / "x.md").write_text("# x\n", encoding="utf-8")
            (repo_b / "rules").mkdir(parents=True)
            (repo_b / "rules" / "go").mkdir(parents=True)
            (repo_b / "rules" / "go" / "b.yml").write_text("id: go/b\n", encoding="utf-8")
            (repo_b / "rules" / "go" / "a.yml").write_text("id: go/a\n", encoding="utf-8")

            h_a = run.content_hash(repo_a)
            h_b = run.content_hash(repo_b)
            self.assertEqual(h_a, h_b)


class TestConfigHash(unittest.TestCase):
    """Config hash discriminates mode and is stable for identical inputs."""

    def test_config_hash_distinguishes_mode(self):
        """Same rc_hash/model/effort/version but different mode → different digest."""
        rc = "a" * 64
        model, effort, ver = "claude-opus-5", "high", "dev-1"
        h_selector = run.config_hash(rc, model, effort, "selector", ver)
        h_full = run.config_hash(rc, model, effort, "full", ver)
        self.assertNotEqual(h_selector, h_full)

    def test_config_hash_identical_inputs(self):
        """Identical inputs produce identical digests."""
        args = ("a" * 64, "claude-opus-5", "high", "short", "dev-1")
        self.assertEqual(run.config_hash(*args), run.config_hash(*args))

    def test_config_hash_distinguishes_ambient_memory(self):
        """Same five components but different operator memory → different digest.

        Ambient `~/.claude/CLAUDE.md` demonstrably steers the reviewer (an
        opus/xhigh/full review ended with the operator's personal state-closer
        panel), so a digest that ignored it would claim to identify a
        configuration it does not determine.  Without this test the component
        could be dropped from the payload and every other test would still pass.
        """
        args = ("a" * 64, "claude-opus-5", "high", "short", "dev-1")
        self.assertNotEqual(
            run.config_hash(*args, ambient_hash="memory-A"),
            run.config_hash(*args, ambient_hash="memory-B"),
            "config hash must change when operator memory changes",
        )

    def test_ambient_memory_hash_reports_none_when_absent(self):
        """A machine with no operator memory hashes to the literal "none".

        Not an empty string and not a crash: an absent file is a real, nameable
        configuration state, and it must be distinguishable from a present one.
        """
        import pathlib
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            missing = pathlib.Path(td) / "CLAUDE.md"
            self.assertEqual(run.ambient_memory_hash(missing), "none")
            present = pathlib.Path(td) / "present.md"
            present.write_text("some operator rule\n", encoding="utf-8")
            self.assertNotEqual(run.ambient_memory_hash(present), "none")


class TestLoadManifest(unittest.TestCase):
    """Manifest loading and validation."""

    def test_load_manifest_rejects_missing_field(self):
        """An entry missing head_sha raises BenchError naming the entry id and field."""
        import json
        import pathlib

        with tempfile.TemporaryDirectory() as td:
            bad_manifest = pathlib.Path(td) / "bad.json"
            bad_manifest.write_text(
                json.dumps({
                    "version": "dev-1",
                    "prs": [{
                        "id": "owner#1", "owner": "owner", "repo": "repo",
                        "number": 1, "merge_strategy": "merge-commit",
                        "merge_sha": "a" * 7, "base_sha": "b" * 7,
                        # "head_sha" deliberately absent
                        "changed_files": 1,
                    }]
                }),
                encoding="utf-8",
            )
            with self.assertRaises(run.BenchError) as ctx:
                run.load_manifest(bad_manifest)
            msg = str(ctx.exception)
            self.assertIn("owner#1", msg)
            self.assertIn("head_sha", msg)

    def test_load_manifest_rejects_invalid_json(self):
        """A non-JSON manifest raises BenchError naming the path."""
        import pathlib

        with tempfile.TemporaryDirectory() as td:
            bad = pathlib.Path(td) / "not-json.json"
            bad.write_text("this is not json {", encoding="utf-8")
            with self.assertRaises(run.BenchError) as ctx:
                run.load_manifest(bad)
            self.assertIn(str(bad), str(ctx.exception))

    def test_load_manifest_rejects_traversal_owner(self):
        """owner="../evil" and repo="a/b" each raise BenchError."""
        import json
        import pathlib

        cases = [
            {"owner": "../evil", "repo": "repo"},
            {"owner": "owner", "repo": "a/b"},
        ]
        for case in cases:
            with tempfile.TemporaryDirectory() as td:
                m = pathlib.Path(td) / "m.json"
                base = {
                    "version": "dev-1",
                    "prs": [{
                        "id": "owner#1", "owner": "owner", "repo": "repo",
                        "number": 1, "merge_strategy": "merge-commit",
                        "merge_sha": "a" * 7, "base_sha": "b" * 7,
                        "head_sha": "c" * 7, "changed_files": 1,
                    }]
                }
                base["prs"][0].update(case)
                m.write_text(json.dumps(base), encoding="utf-8")
                with self.assertRaises(run.BenchError) as ctx:
                    run.load_manifest(m)
                self.assertIn(case.get("owner") or case.get("repo"), str(ctx.exception))

    def test_load_manifest_accepts_real_fixture(self):
        """load_manifest on the shipped bench/prs.json returns curated-1 with 20 entries.

        Pinned on purpose: the version and count are part of the config identity,
        so a manifest change must be a conscious edit here rather than something
        a scored run discovers.  `dev-1`/5 was the 5-PR development fixture; its
        3-sigma was ~119% of the mean, which is why it could not carry a score.
        """
        m = run.load_manifest(run.BENCH_DIR / "prs.json")
        self.assertEqual(m["version"], "curated-1")
        self.assertEqual(len(m["prs"]), 20)

    def test_curated_manifest_holds_the_spread_it_was_curated_for(self):
        """The fixture's whole purpose is spread; assert it rather than trust it."""
        m = run.load_manifest(run.BENCH_DIR / "prs.json")

        sizes = [p["additions"] + p["deletions"] for p in m["prs"]]
        self.assertLessEqual(min(sizes), 20, "no small PR in the set")
        self.assertGreaterEqual(max(sizes), 1000, "no large PR in the set")

        repos = {p["repo"] for p in m["prs"]}
        self.assertGreaterEqual(len(repos), 10, f"too few distinct repos: {repos}")

        strategies = {p["merge_strategy"] for p in m["prs"]}
        # Both diff-reconstruction paths must be exercised: a merge-commit uses
        # `<merge>^1..<merge>^2`, a squash has one parent and needs the manifest's
        # base_sha..head_sha.  A fixture carrying only one shape leaves the other
        # branch untested.
        self.assertIn("squash", strategies)
        self.assertIn("merge-commit", strategies)


class TestPluginResolution(unittest.TestCase):
    """Plugin-resolution preflight (AC9 and related)."""

    def test_plugin_resolution_mismatch_aborts_before_any_review(self):
        """When resolved plugin differs from --coding-repo, BenchError is raised
        before any claude invocation (counter file has 0 lines)."""
        import pathlib
        import os

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            # Two coding repos with different content
            repo_a = testsupport.build_coding_repo(
                td / "repo_a",
                rules={"go/a.yml": "id: go/a\n"},
                commands={"a.md": "# a\n"},
            )
            repo_b = testsupport.build_coding_repo(
                td / "repo_b",
                rules={"go/b.yml": "id: go/b\n"},  # different content
                commands={"b.md": "# b\n"},
            )
            cfg = testsupport.build_verify_config_dir(td / "cfg", repo_b)

            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, "fake review output")
            env = testsupport.with_path(bin_dir)

            # HOME must point at our temp dir so verify_config_dir finds .claude-verify
            env["HOME"] = str(td)

            with self.assertRaises(run.BenchError) as ctx:
                run.run_bench(
                    coding_repo=repo_a,
                    manifest_path=run.BENCH_DIR / "prs.json",
                    results_dir=td / "results",
                    cache_root=td / "cache",
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )
            msg = str(ctx.exception)
            self.assertTrue(msg.startswith("PLUGIN RESOLUTION MISMATCH"), msg)
            self.assertIn("actual_hash=", msg)
            self.assertIn("expected_hash=", msg)
            # The message must name the resolved load path
            self.assertIn("load_path=", msg)
            # Counter file must not exist or have 0 lines — zero reviews invoked
            self.assertFalse(counter.exists() and counter.read_text().strip())

    def test_verify_config_dir_without_home_raises(self):
        """Without HOME set, verify_config_dir raises BenchError naming .claude-verify.

        Call main() in the subprocess so the top-level try/except BenchError
        converts the exception to exit code 2.  We pass --model/--effort/--mode
        so we get past the missing-argument check and hit verify_config_dir().
        """
        script = (
            "import sys; sys.path.insert(0, 'bench'); "
            "import run; "
            "sys.exit(run.main(['--model','m','--effort','e','--mode','short']))"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True,
            env={k: v for k, v in os.environ.items() if k != "HOME"},
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(".claude-verify", result.stderr)


class TestCliContract(unittest.TestCase):
    """CLI exit-code contract tests (AC11 and mandatory flag enforcement)."""

    def test_golden_flag_exits_two(self):
        """--golden without identity flags exits 2, naming --model."""
        result = subprocess.run(
            [sys.executable, str(run.BENCH_DIR / "run.py"),
             "--golden", "bench/golden.json"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("--model", result.stderr)
        self.assertNotIn("future work", result.stderr)
        self.assertNotIn("not implemented", result.stderr)

    def test_print_config_hash_matches_content_hash(self):
        """--print-config-hash exits 0 and its stdout equals content_hash()."""
        import pathlib
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            repo = testsupport.build_coding_repo(td / "repo")
            result = subprocess.run(
                [sys.executable, str(run.BENCH_DIR / "run.py"),
                 "--print-config-hash", "--coding-repo", str(repo)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), run.content_hash(repo))

    def test_missing_required_flag_exits_two(self):
        """Missing --mode exits 2 and names --mode in stderr."""
        result = subprocess.run(
            [sys.executable, str(run.BENCH_DIR / "run.py"),
             "--model", "m", "--effort", "e"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("--mode", result.stderr)

    def test_missing_model_and_effort_flags_exit_two(self):
        """Each mandatory flag exits 2 individually when missing.

        Override HOME to a temp dir with a matching plugin so the plugin-resolution
        preflight does not fire and mask the missing-argument check.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up an isolated config dir whose plugin matches --coding-repo
            plugin_src = testsupport.build_coding_repo(pathlib.Path(tmpdir) / "repo")
            cfg = testsupport.build_verify_config_dir(
                pathlib.Path(tmpdir) / "cfg", plugin_src
            )
            for flag in ["--model", "--effort"]:
                args = [
                    sys.executable, str(run.BENCH_DIR / "run.py"),
                    "--coding-repo", str(plugin_src),
                    # --model and --effort NOT set for the flag being tested
                    "--mode", "short",
                ]
                result = subprocess.run(
                    args,
                    capture_output=True, text=True,
                    env={**os.environ, "HOME": tmpdir},
                )
                self.assertEqual(
                    result.returncode, 2,
                    f"flag={flag} returncode={result.returncode} stderr={result.stderr}",
                )
                self.assertIn(flag, result.stderr)


class TestPluginLoadPathResolution(unittest.TestCase):
    """Plugin load-path resolution preflight tests (AC2-AC7, AC13)."""

    def test_recorded_install_path_is_the_load_path(self):
        """AC2 Case A: marketplace path identical, recorded load path mutated → mismatch."""
        import pathlib
        import os

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)

            repo_good = testsupport.build_coding_repo(td / "repo_good")
            repo_mutated = testsupport.build_coding_repo(
                td / "repo_mutated",
                rules={"go/sample.yml": "id: go/sample\nlevel: WONT\n"},
            )

            # Marketplace copy = good; recorded load path = mutated
            cfg = testsupport.build_verify_config_dir(
                td / "cfg", repo_mutated,
                marketplace_src=repo_good,
            )

            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            with mock.patch.dict(os.environ, env):
                with self.assertRaises(run.BenchError) as ctx:
                    run.run_bench(
                        coding_repo=repo_good,
                        manifest_path=run.BENCH_DIR / "prs.json",
                        results_dir=td / "results",
                        cache_root=td / "cache",
                        model="test-model",
                        effort="high",
                        mode="short",
                        config_dir=cfg,
                    )
            msg = str(ctx.exception)
            self.assertTrue(msg.startswith("PLUGIN RESOLUTION MISMATCH"), msg)
            expected_path = str(cfg / "plugins" / "cache" / "coding" / "coding" / "0.35.2")
            self.assertIn(expected_path, msg)
            self.assertIn("actual_hash=", msg)
            self.assertIn("expected_hash=", msg)
            # Zero reviews invoked
            self.assertFalse(counter.exists() and counter.read_text().strip())

    def test_marketplace_path_mismatch_does_not_block_the_run(self):
        """AC2 Case B: load path matches, marketplace path mutated → run proceeds."""
        import pathlib
        import os

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)

            repo_good = testsupport.build_coding_repo(td / "repo_good")
            repo_mutated = testsupport.build_coding_repo(
                td / "repo_mutated",
                rules={"go/sample.yml": "id: go/sample\nlevel: WONT\n"},
            )

            # Recorded load path = good; marketplace = mutated
            cfg = testsupport.build_verify_config_dir(
                td / "cfg", repo_good,
                marketplace_src=repo_mutated,
            )

            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            cache_root = td / "cache"
            manifest_path = testsupport.seed_one_pr_manifest(td, cache_root)

            with mock.patch.dict(os.environ, env):
                rc = run.run_bench(
                    coding_repo=repo_good,
                    manifest_path=manifest_path,
                    results_dir=td / "results",
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )
            self.assertEqual(rc, 0)
            # One review invoked
            self.assertTrue(counter.exists() and counter.read_text().strip())

    def test_recorded_version_is_hashed_not_the_newest_on_disk(self):
        """AC3: record naming lower version proceeds; record naming wrong version mismatches."""
        import pathlib
        import os

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)

            repo_low = testsupport.build_coding_repo(
                td / "repo_low",
                rules={"go/low.yml": "id: go/low\n"},
            )
            repo_high = testsupport.build_coding_repo(
                td / "repo_high",
                rules={"go/high.yml": "id: go/high\n"},
            )

            # Config names 0.16.0 but 9.99.0 is also on disk
            bin_dir_a = td / "bin_a"
            counter_a = td / "counter_a"
            stub_a = testsupport.stub_claude(bin_dir_a, counter_a, testsupport.CLEAN_REVIEW_REPORT)
            env_a = testsupport.with_path(bin_dir_a)
            env_a["HOME"] = str(td)

            cache_root_a = td / "cache_a"
            cfg_a = testsupport.build_verify_config_dir(
                td / "cfg_a", repo_low,
                version="0.16.0",
                extra_versions={"9.99.0": repo_high},
            )
            manifest_path_a = testsupport.seed_one_pr_manifest(td, cache_root_a)

            with mock.patch.dict(os.environ, env_a):
                rc_a = run.run_bench(
                    coding_repo=repo_low,
                    manifest_path=manifest_path_a,
                    results_dir=td / "results_a",
                    cache_root=cache_root_a,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg_a,
                )
            self.assertEqual(rc_a, 0)
            self.assertTrue(counter_a.exists() and counter_a.read_text().strip())

            # Config names 0.16.0 but --coding-repo matches 9.99.0 → mismatch
            bin_dir_b = td / "bin_b"
            counter_b = td / "counter_b"
            stub_b = testsupport.stub_claude(bin_dir_b, counter_b, testsupport.CLEAN_REVIEW_REPORT)
            env_b = testsupport.with_path(bin_dir_b)
            env_b["HOME"] = str(td)

            cache_root_b = td / "cache_b"
            cfg_b = testsupport.build_verify_config_dir(
                td / "cfg_b", repo_low,
                version="0.16.0",
                extra_versions={"9.99.0": repo_high},
            )
            manifest_path_b = testsupport.seed_one_pr_manifest(td, cache_root_b)

            with mock.patch.dict(os.environ, env_b):
                with self.assertRaises(run.BenchError) as ctx:
                    run.run_bench(
                        coding_repo=repo_high,
                        manifest_path=manifest_path_b,
                        results_dir=td / "results_b",
                        cache_root=cache_root_b,
                        model="test-model",
                        effort="high",
                        mode="short",
                        config_dir=cfg_b,
                    )
            msg = str(ctx.exception)
            self.assertTrue(msg.startswith("PLUGIN RESOLUTION MISMATCH"), msg)
            self.assertIn("0.16.0", msg)

    def test_stale_install_path_aborts_before_any_review(self):
        """AC4: record pointing to a non-existent directory aborts with STALE_INSTALL_PATH_MARKER."""
        import pathlib
        import os

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)

            plugin_src = testsupport.build_coding_repo(td / "src")
            cfg_base = td / "cfg"
            # stale_path must be under cfg's plugin tree but not exist
            stale_path = cfg_base / ".claude-verify" / "plugins" / "cache" / "coding" / "coding" / "0.16.0-missing"

            cfg = testsupport.build_verify_config_dir(
                cfg_base, plugin_src,
                version="0.16.0",
                install_path=stale_path,
            )

            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            with mock.patch.dict(os.environ, env):
                with self.assertRaises(run.BenchError) as ctx:
                    run.run_bench(
                        coding_repo=plugin_src,
                        manifest_path=run.BENCH_DIR / "prs.json",
                        results_dir=td / "results",
                        cache_root=td / "cache",
                        model="test-model",
                        effort="high",
                        mode="short",
                        config_dir=cfg,
                    )
            msg = str(ctx.exception)
            self.assertIn(run.STALE_INSTALL_PATH_MARKER, msg)
            self.assertIn("0.16.0", msg)
            # Counter file 0 lines
            self.assertFalse(counter.exists() and counter.read_text().strip())
            # Results file unchanged
            results_file = td / "results" / "results.jsonl"
            self.assertFalse(results_file.exists())

    def test_project_scoped_record_for_another_directory_aborts(self):
        """AC5 Case A: project-scoped record for wrong directory aborts with SCOPE_MISMATCH_MARKER."""
        import pathlib
        import os

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)

            plugin_src = testsupport.build_coding_repo(td / "src")
            elsewhere = td / "elsewhere"

            cfg = testsupport.build_verify_config_dir(
                td / "cfg", plugin_src,
                scope="project",
                project_path=elsewhere,
            )

            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            cache_root = td / "cache"
            manifest_path = testsupport.seed_one_pr_manifest(td, cache_root)

            with mock.patch.dict(os.environ, env):
                with self.assertRaises(run.BenchError) as ctx:
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
            msg = str(ctx.exception)
            self.assertIn(run.SCOPE_MISMATCH_MARKER, msg)
            self.assertIn(str(elsewhere), msg)
            self.assertIn(str(run.repos_root(cache_root)), msg)
            # Counter file 0 lines
            self.assertFalse(counter.exists() and counter.read_text().strip())

    def test_user_scoped_record_alongside_a_project_scoped_one_is_used(self):
        """AC5 Case B: project-scoped first, user-scoped second → run proceeds."""
        import pathlib
        import os

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)

            plugin_src = testsupport.build_coding_repo(td / "src")
            elsewhere = td / "elsewhere"
            cfg_base = td / "cfg"

            # Primary record: project-scoped (wrong), extra: user-scoped (valid)
            cfg = testsupport.build_verify_config_dir(
                cfg_base, plugin_src,
                scope="project",
                project_path=elsewhere,
                extra_records=[{
                    "scope": "user",
                    "installPath": str(cfg_base / ".claude-verify" / "plugins" / "cache" / "coding" / "coding" / "0.35.2"),
                    "version": "0.35.2",
                    "installedAt": "2026-08-08T00:00:00.000Z",
                    "lastUpdated": "2026-08-08T00:00:00.000Z",
                }],
            )

            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            cache_root = td / "cache"
            manifest_path = testsupport.seed_one_pr_manifest(td, cache_root)

            with mock.patch.dict(os.environ, env):
                rc = run.run_bench(
                    coding_repo=plugin_src,
                    manifest_path=manifest_path,
                    results_dir=td / "results",
                    cache_root=cache_root,
                    model="test-model",
                    effort="high",
                    mode="short",
                    config_dir=cfg,
                )
            self.assertEqual(rc, 0)
            self.assertTrue(counter.exists() and counter.read_text().strip())

    def test_missing_install_record_aborts_without_marketplace_fallback(self):
        """AC6 case 1: no install record → NO_INSTALL_RECORD_MARKER; marketplace NOT in msg."""
        import pathlib
        import os

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)

            plugin_src = testsupport.build_coding_repo(td / "src")
            # Write marketplace copy so we can prove it was NOT used as fallback
            repo_good = testsupport.build_coding_repo(td / "repo_good")

            cfg = testsupport.build_verify_config_dir(
                td / "cfg", plugin_src,
                marketplace_src=repo_good,
                write_record=False,
            )

            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            with mock.patch.dict(os.environ, env):
                with self.assertRaises(run.BenchError) as ctx:
                    run.run_bench(
                        coding_repo=repo_good,
                        manifest_path=run.BENCH_DIR / "prs.json",
                        results_dir=td / "results",
                        cache_root=td / "cache",
                        model="test-model",
                        effort="high",
                        mode="short",
                        config_dir=cfg,
                    )
            msg = str(ctx.exception)
            self.assertIn(run.NO_INSTALL_RECORD_MARKER, msg)
            record_file = run.installed_plugins_path(cfg)
            self.assertIn(str(record_file), msg)
            self.assertNotIn("marketplaces", msg.lower())
            # Counter file 0 lines
            self.assertFalse(counter.exists() and counter.read_text().strip())

    def test_malformed_install_record_aborts_without_marketplace_fallback(self):
        """AC6 case 2: malformed record → UNREADABLE_INSTALL_RECORD_MARKER; marketplace NOT in msg."""
        import pathlib
        import os

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)

            plugin_src = testsupport.build_coding_repo(td / "src")
            repo_good = testsupport.build_coding_repo(td / "repo_good")

            cfg = testsupport.build_verify_config_dir(
                td / "cfg", plugin_src,
                marketplace_src=repo_good,
                record_text="{ this is not json",
            )

            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            with mock.patch.dict(os.environ, env):
                with self.assertRaises(run.BenchError) as ctx:
                    run.run_bench(
                        coding_repo=repo_good,
                        manifest_path=run.BENCH_DIR / "prs.json",
                        results_dir=td / "results",
                        cache_root=td / "cache",
                        model="test-model",
                        effort="high",
                        mode="short",
                        config_dir=cfg,
                    )
            msg = str(ctx.exception)
            self.assertIn(run.UNREADABLE_INSTALL_RECORD_MARKER, msg)
            record_file = run.installed_plugins_path(cfg)
            self.assertIn(str(record_file), msg)
            self.assertNotIn("marketplaces", msg.lower())
            # Counter file 0 lines
            self.assertFalse(counter.exists() and counter.read_text().strip())

    def test_out_of_tree_install_path_is_refused(self):
        """AC6 case 3: install path outside plugin tree → OUT_OF_TREE_INSTALL_PATH_MARKER."""
        import pathlib
        import os

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)

            outside = td / "outside-plugin-tree"
            testsupport.build_coding_repo(outside)
            repo_good = testsupport.build_coding_repo(td / "repo_good")

            cfg = testsupport.build_verify_config_dir(
                td / "cfg", repo_good,
                install_path=outside,
                marketplace_src=repo_good,
            )

            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            with mock.patch.dict(os.environ, env):
                with self.assertRaises(run.BenchError) as ctx:
                    run.run_bench(
                        coding_repo=outside,
                        manifest_path=run.BENCH_DIR / "prs.json",
                        results_dir=td / "results",
                        cache_root=td / "cache",
                        model="test-model",
                        effort="high",
                        mode="short",
                        config_dir=cfg,
                    )
            msg = str(ctx.exception)
            self.assertIn(run.OUT_OF_TREE_INSTALL_PATH_MARKER, msg)
            self.assertIn(str(outside), msg)
            self.assertIn(str(run.plugin_cache_root(cfg)), msg)
            self.assertNotIn("marketplaces", msg.lower())
            # Counter file 0 lines
            self.assertFalse(counter.exists() and counter.read_text().strip())

    def test_passing_preflight_prints_one_resolution_line(self):
        """AC7: successful run prints exactly one line with load path, version, and full hash."""
        import pathlib
        import os
        import io
        import contextlib

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)

            plugin_src = testsupport.build_coding_repo(td / "src")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src)

            bin_dir = td / "bin"
            counter = td / "counter"
            stub = testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)
            env = testsupport.with_path(bin_dir)
            env["HOME"] = str(td)

            cache_root = td / "cache"
            manifest_path = testsupport.seed_one_pr_manifest(td, cache_root)

            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                with mock.patch.dict(os.environ, env):
                    rc = run.run_bench(
                        coding_repo=plugin_src,
                        manifest_path=manifest_path,
                        results_dir=td / "results",
                        cache_root=cache_root,
                        model="test-model",
                        effort="high",
                        mode="short",
                        config_dir=cfg,
                    )

            self.assertEqual(rc, 0)
            output = captured.getvalue()
            expected_path = str(cfg / "plugins" / "cache" / "coding" / "coding" / "0.35.2")
            expected_hash = run.content_hash(plugin_src)
            matching_lines = [
                ln for ln in output.splitlines()
                if expected_path in ln and "0.35.2" in ln and expected_hash in ln
            ]
            self.assertEqual(
                len(matching_lines), 1,
                f"expected exactly 1 resolution line, got {len(matching_lines)}: {output!r}"
            )


if __name__ == "__main__":
    unittest.main()
