#!/usr/bin/env python3
"""Unit tests for bench/run.py — AC6, AC9, AC11 and related container tests."""

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

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
        """load_manifest on the frozen bench/prs.json succeeds and returns dev-1 with 5 entries."""
        m = run.load_manifest(run.BENCH_DIR / "prs.json")
        self.assertEqual(m["version"], "dev-1")
        self.assertEqual(len(m["prs"]), 5)


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
            # Counter file must not exist or have 0 lines — zero reviews invoked
            self.assertFalse(counter.exists() and counter.read_text().strip())

    def test_plugin_resolution_honors_install_location(self):
        """With use_known_marketplaces=True pointing at the same repo,
        resolve_plugin_path returns exactly plugin_src."""
        import pathlib

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            plugin_src = testsupport.build_coding_repo(td / "src")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src,
                                                     use_known_marketplaces=True)
            resolved = run.resolve_plugin_path(cfg)
            self.assertEqual(resolved, plugin_src)

    def test_plugin_resolution_falls_back_to_marketplaces_dir(self):
        """With no known_marketplaces.json, resolve_plugin_path returns
        <cfg>/plugins/marketplaces/coding."""
        import pathlib

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            plugin_src = testsupport.build_coding_repo(td / "src")
            cfg = testsupport.build_verify_config_dir(td / "cfg", plugin_src,
                                                     use_known_marketplaces=False)
            resolved = run.resolve_plugin_path(cfg)
            expected = cfg / "plugins" / "marketplaces" / "coding"
            self.assertEqual(resolved, expected)

    def test_known_marketplaces_invalid_json_raises(self):
        """Malformed known_marketplaces.json raises BenchError naming the file."""
        import pathlib

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cfg = td / ".claude-verify"
            cfg.mkdir(parents=True)
            (cfg / "plugins").mkdir(parents=True)
            (cfg / "plugins" / "known_marketplaces.json").write_text(
                "{ this is not json", encoding="utf-8"
            )
            with self.assertRaises(run.BenchError) as ctx:
                run.resolve_plugin_path(cfg)
            self.assertIn("known_marketplaces.json", str(ctx.exception))

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
        """--golden exits 2 and stderr mentions scoring / future work."""
        result = subprocess.run(
            [sys.executable, str(run.BENCH_DIR / "run.py"),
             "--golden", "bench/golden.json"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("scoring", result.stderr.lower())
        self.assertIn("future", result.stderr.lower())

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
                pathlib.Path(tmpdir) / "cfg", plugin_src, use_known_marketplaces=True
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


if __name__ == "__main__":
    unittest.main()
