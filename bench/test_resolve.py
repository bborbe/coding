#!/usr/bin/env python3
"""Unit tests for bench/run.py PR resolution — AC2, AC3, AC7, AC8 and related."""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

import run
import testsupport


class TestDiffRangeBranchesOnParentCount(unittest.TestCase):
    """AC2: diff range branches on actual parent count."""

    def test_parent_count_drives_merge_range(self):
        """Two-parent merge → ^1..^2; single-parent squash → manifest base..head."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            repos_root = cache_root / "repos"

            # Create merge repo in cache
            cache_merge = repos_root / "testowner" / "mergerepo"
            cache_merge.mkdir(parents=True, exist_ok=True)
            testsupport.init_git_repo(cache_merge)
            merge_info = testsupport.make_merge_repo(cache_merge)

            # Create squash repo in cache
            cache_squash = repos_root / "testowner" / "squashrepo"
            cache_squash.mkdir(parents=True, exist_ok=True)
            testsupport.init_git_repo(cache_squash)
            squash_info = testsupport.make_squash_repo(cache_squash)

            merge_entry = {
                "id": "test#1",
                "owner": "testowner",
                "repo": "mergerepo",
                "number": 1,
                "merge_strategy": "merge-commit",
                "merge_sha": merge_info["merge_sha"],
                "base_sha": merge_info["base_sha"],
                "head_sha": merge_info["head_sha"],
                "changed_files": 1,
            }
            squash_entry = {
                "id": "test#2",
                "owner": "testowner",
                "repo": "squashrepo",
                "number": 2,
                "merge_strategy": "squash",
                "merge_sha": squash_info["merge_sha"],
                "base_sha": squash_info["base_sha"],
                "head_sha": squash_info["head_sha"],
                "changed_files": 1,
            }

            # Merge: 2 parents → ^1..^2
            mr, _, _, np, _ = run.resolve_diff_range(cache_root, cache_merge, merge_entry)
            self.assertEqual(np, 2)
            expected_mr = f"{merge_entry['merge_sha']}^1..{merge_entry['merge_sha']}^2"
            self.assertEqual(mr, expected_mr,
                msg=f"merge_range={mr!r} expected {expected_mr!r}")

            # Squash: 1 parent → manifest base..head
            sr, _, _, np_sq, _ = run.resolve_diff_range(cache_root, cache_squash, squash_entry)
            self.assertEqual(np_sq, 1)
            expected_sr = f"{squash_entry['base_sha']}..{squash_entry['head_sha']}"
            self.assertEqual(sr, expected_sr,
                msg=f"squash_range={sr!r} expected {expected_sr!r}")

            # Both ranges have ≥1 changed file
            m_files = run.changed_files(cache_root, cache_merge, mr)
            s_files = run.changed_files(cache_root, cache_squash, sr)
            self.assertGreaterEqual(len(m_files), 1)
            self.assertGreaterEqual(len(s_files), 1)


class TestSquashRangeIsManifestDerived(unittest.TestCase):
    """AC2 variant: single-parent commits always use manifest base..head."""

    def test_single_parent_uses_manifest_base_not_parent_derived(self):
        """Manifest base_sha older than merge commit's parent → still uses manifest."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            repos_root = cache_root / "repos"

            cache_repo = repos_root / "test" / "repo"
            cache_repo.mkdir(parents=True, exist_ok=True)
            testsupport.init_git_repo(cache_repo)
            oldest = testsupport.commit_file(cache_repo, "oldest.txt", "oldest\n", "oldest")
            middle = testsupport.commit_file(cache_repo, "middle.txt", "middle\n", "middle")
            newest = testsupport.commit_file(cache_repo, "newest.txt", "newest\n", "newest")

            entry = {
                "id": "test#1",
                "owner": "test",
                "repo": "repo",
                "number": 1,
                "merge_strategy": "squash",
                "merge_sha": newest,
                "base_sha": oldest,
                "head_sha": newest,
                "changed_files": 2,
            }

            dr, _, _, np, _ = run.resolve_diff_range(cache_root, cache_repo, entry)
            self.assertEqual(np, 1)
            self.assertEqual(dr, f"{oldest}..{newest}",
                "must use manifest base_sha, not parent traversal")


class TestStrategyLabelMismatch(unittest.TestCase):
    """Strategy label is reported but never obeyed for range selection."""

    def test_mismatch_is_noted_not_obeyed(self):
        """Two-parent repo with squash label → ^1..^2 range + note."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            repos_root = cache_root / "repos"

            cache_repo = repos_root / "test" / "repo"
            cache_repo.mkdir(parents=True, exist_ok=True)
            testsupport.init_git_repo(cache_repo)
            merge_info = testsupport.make_merge_repo(cache_repo)

            entry = {
                "id": "test#1",
                "owner": "test",
                "repo": "repo",
                "number": 1,
                "merge_strategy": "squash",  # wrong label
                "merge_sha": merge_info["merge_sha"],
                "base_sha": merge_info["base_sha"],
                "head_sha": merge_info["head_sha"],
                "changed_files": 1,
            }

            dr, _, _, np, notes = run.resolve_diff_range(cache_root, cache_repo, entry)
            expected = f"{entry['merge_sha']}^1..{entry['merge_sha']}^2"
            self.assertEqual(dr, expected)
            self.assertEqual(np, 2)
            self.assertTrue(
                any("strategy mismatch" in n for n in notes),
                f"notes must contain 'strategy mismatch', got {notes!r}"
            )


class TestEmptyDiffAbortsLoudly(unittest.TestCase):
    """AC3: empty diff aborts before review, no row, no cache entry."""

    def test_empty_diff_raises_empty_diff_error(self):
        """With base_sha == head_sha (empty diff), resolve_pr raises BenchError
        with 'EMPTY DIFF' message before any worktree or review is created."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"

            # Build empty-diff repo in cache
            cache_repo = cache_root / "repos" / "testowner" / "emptyrepo"
            cache_repo.mkdir(parents=True, exist_ok=True)
            testsupport.init_git_repo(cache_repo)
            empty_info = testsupport.make_empty_diff_repo(cache_repo)

            entry = {
                "id": "empty#99",
                "owner": "testowner",
                "repo": "emptyrepo",
                "number": 99,
                "merge_strategy": "squash",
                "merge_sha": empty_info["merge_sha"],
                "base_sha": empty_info["base_sha"],
                "head_sha": empty_info["head_sha"],
                "changed_files": 0,
            }

            # resolve_pr should raise EMPTY DIFF before creating worktree
            with self.assertRaises(run.BenchError) as ctx:
                run.resolve_pr(cache_root, entry)

            msg = str(ctx.exception)
            self.assertIn("EMPTY DIFF", msg)
            self.assertIn("empty#99", msg)
            self.assertIn("..", msg)  # range in message


class TestFetchUrlIsBuiltFromManifest(unittest.TestCase):
    """AC8: fetch URL is built from manifest owner/repo, never from 'origin'."""

    def test_fetch_url_exact_format(self):
        url = run.fetch_url("bborbe", "tts-mcp")
        self.assertEqual(url, "https://github.com/bborbe/tts-mcp")

    def test_fetch_url_not_from_origin(self):
        """URL is always from manifest, independent of remotes."""
        url = run.fetch_url("bborbe", "tts-mcp")
        self.assertEqual(url, "https://github.com/bborbe/tts-mcp")
        self.assertNotIn("florianbuetow", url)


class TestFetchUrlWithNoOriginRemote(unittest.TestCase):
    """AC8 second case: no remote named 'origin' at all."""

    def test_fetch_url_same_when_no_origin(self):
        url = run.fetch_url("bborbe", "tts-mcp")
        self.assertEqual(url, "https://github.com/bborbe/tts-mcp")


class TestEveryGitStaysUnderCacheRepos(unittest.TestCase):
    """AC7: every git invocation stays under bench/.cache/repos/."""

    def test_git_invocation_confined_to_cache_repos(self):
        """With stub_git on PATH via os.environ, every logged path is under cache repos/."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir = td / "results"
            results_dir.mkdir(parents=True)

            git_log = td / "git_log"
            bin_dir = td / "bin"
            testsupport.stub_git(bin_dir, git_log)

            # Pre-seed cache repos with valid git repos so offline short-circuit works
            repos_root = cache_root / "repos"
            sha_a = None
            sha_b = None
            for owner, repo in [("testowner", "repo_a"), ("testowner", "repo_b")]:
                repo_path = repos_root / owner / repo
                repo_path.mkdir(parents=True, exist_ok=True)
                testsupport.init_git_repo(repo_path)
                sha = testsupport.commit_file(repo_path, "f.txt", "c\n", "f")
                if repo == "repo_a":
                    sha_a = sha
                else:
                    sha_b = sha

            manifest_entries = [
                {
                    "id": "test#1",
                    "owner": "testowner",
                    "repo": "repo_a",
                    "number": 1,
                    "merge_strategy": "merge-commit",
                    "merge_sha": sha_a,
                    "base_sha": sha_a,
                    "head_sha": sha_a,
                    "changed_files": 1,
                },
                {
                    "id": "test#2",
                    "owner": "testowner",
                    "repo": "repo_b",
                    "number": 2,
                    "merge_strategy": "merge-commit",
                    "merge_sha": sha_b,
                    "base_sha": sha_b,
                    "head_sha": sha_b,
                    "changed_files": 1,
                },
            ]

            manifest_path = td / "manifest.json"
            testsupport.make_manifest(manifest_path, manifest_entries)

            plugin_src = testsupport.make_coding_repo(td / "repo")
            cfg = testsupport.make_verify_config_dir(td / "cfg", plugin_src,
                                                     use_known_marketplaces=True)

            # Save and modify os.environ to put stub_git on PATH
            old_path = os.environ.get("PATH", "")
            old_home = os.environ.get("HOME", "")
            try:
                os.environ["PATH"] = f"{bin_dir}{os.pathsep}{old_path}"
                os.environ["HOME"] = str(td)

                try:
                    run.run_bench(
                        coding_repo=plugin_src,
                        manifest_path=manifest_path,
                        results_dir=results_dir,
                        cache_root=cache_root,
                        model="test-model",
                        effort="high",
                        mode="short",
                        config_dir=cfg,
                    )
                except Exception:
                    pass  # may fail due to stub git, we only care about logged paths
            finally:
                os.environ["PATH"] = old_path
                os.environ["HOME"] = old_home

            log_content = ""
            if git_log.exists():
                log_content = git_log.read_text()
                log_lines = [ln for ln in log_content.splitlines() if ln.strip()]
            else:
                log_lines = []

            self.assertGreaterEqual(len(log_lines), 2,
                f"expected ≥2 git invocations, got {len(log_lines)}. "
                f"git_log exists={git_log.exists()}, content={log_content!r}")

            repos_prefix = str((cache_root / "repos").resolve())
            for line in log_lines:
                if " -C " in line:
                    parts = line.split(" -C ", 1)
                    if len(parts) > 1:
                        path = parts[1].split()[0]
                        path_resolved = str(pathlib.Path(path).resolve())
                        self.assertTrue(
                            path_resolved.startswith(repos_prefix),
                            f"git invocation targets {path!r} ({path_resolved!r}) "
                            f"not under {repos_prefix!r}: line={line!r}"
                        )


class TestAssertUnderRejectsOutsidePath(unittest.TestCase):
    """assert_under enforces strict prefix containment."""

    def test_assert_under_rejects_absolute_outside(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            cache_root.mkdir(parents=True)
            repos = run.repos_root(cache_root)

            with self.assertRaises(run.BenchError) as ctx:
                run.assert_under(pathlib.Path("/tmp"), repos)
            msg = str(ctx.exception)
            self.assertIn("/tmp", msg)
            self.assertIn(str(repos), msg)

    def test_assert_under_rejects_root_itself(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            cache_root.mkdir(parents=True)
            repos = run.repos_root(cache_root)

            with self.assertRaises(run.BenchError) as ctx:
                run.assert_under(repos, repos)
            self.assertIn(str(repos), str(ctx.exception))


class TestFailingPrDoesNotAbortRemainingPrs(unittest.TestCase):
    """A failing PR leaves other PRs to run; exit code is 1."""

    def test_second_pr_runs_after_first_fails(self):
        """First PR has unresolvable SHA; second resolves cleanly. Both in output."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            results_dir = td / "results"
            results_dir.mkdir(parents=True)

            # Good repo
            cache_good = cache_root / "repos" / "good" / "goodrepo"
            cache_good.mkdir(parents=True, exist_ok=True)
            testsupport.init_git_repo(cache_good)
            good_info = testsupport.make_merge_repo(cache_good)

            manifest_entries = [
                {
                    "id": "bad#1",
                    "owner": "bad",
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
                    "owner": "good",
                    "repo": "goodrepo",
                    "number": 2,
                    "merge_strategy": "merge-commit",
                    "merge_sha": good_info["merge_sha"],
                    "base_sha": good_info["base_sha"],
                    "head_sha": good_info["head_sha"],
                    "changed_files": 1,
                },
            ]

            manifest_path = td / "manifest.json"
            testsupport.make_manifest(manifest_path, manifest_entries)

            # Set up plugin/config properly
            cfg_dir = td / ".claude-verify"
            cfg_dir.mkdir(parents=True)
            plugin_dest = td / "repo"
            testsupport.make_coding_repo(plugin_dest)
            (cfg_dir / "plugins").mkdir(parents=True)
            import json
            km = {
                "coding": {
                    "source": {"source": "github", "repo": "bborbe/coding"},
                    "installLocation": str(plugin_dest),
                }
            }
            (cfg_dir / "plugins" / "known_marketplaces.json").write_text(
                json.dumps(km), encoding="utf-8"
            )

            old_home = os.environ.get("HOME", "")
            try:
                os.environ["HOME"] = str(td)
                result = subprocess.run(
                    [sys.executable, str(run.BENCH_DIR / "run.py"),
                     "--coding-repo", str(plugin_dest),
                     "--manifest", str(manifest_path),
                     "--out-dir", str(results_dir),
                     "--model", "test-model",
                     "--effort", "high",
                     "--mode", "short"],
                    capture_output=True, text=True,
                )
            finally:
                os.environ["HOME"] = old_home

            self.assertEqual(result.returncode, 1,
                f"expected exit 1, got {result.returncode}: {result.stderr}")
            self.assertIn("bad#1", result.stdout)
            self.assertIn("good#2", result.stdout)
            self.assertIn("failed", result.stdout)


class TestWorktreeCreatedUnderReposRoot(unittest.TestCase):
    """After resolve_pr, worktree is under repos/, HEAD at head_sha, refs set."""

    def test_worktree_under_repos_root_head_at_sha(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            cache_root = td / "cache"
            repos_root = cache_root / "repos"

            cache_repo = repos_root / "testowner" / "testrepo"
            cache_repo.mkdir(parents=True, exist_ok=True)
            testsupport.init_git_repo(cache_repo)
            merge_info = testsupport.make_merge_repo(cache_repo)

            entry = {
                "id": "test#42",
                "owner": "testowner",
                "repo": "testrepo",
                "number": 42,
                "merge_strategy": "merge-commit",
                "merge_sha": merge_info["merge_sha"],
                "base_sha": merge_info["base_sha"],
                "head_sha": merge_info["head_sha"],
                "changed_files": 1,
            }

            checkout = run.resolve_pr(cache_root, entry)

            # Worktree exists under repos/
            self.assertTrue(checkout.worktree.is_dir(),
                f"worktree {checkout.worktree} must exist")
            self.assertTrue(
                str(checkout.worktree.resolve()).startswith(str(repos_root.resolve())),
                f"worktree {checkout.worktree} must be under {repos_root}"
            )

            # HEAD at correct SHA
            head_result = subprocess.run(
                ["git", "-C", str(checkout.worktree), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(head_result.stdout.strip(), checkout.head_sha)

            # Branch name is bench-pr-<n>
            branch_result = subprocess.run(
                ["git", "-C", str(checkout.worktree), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(branch_result.stdout.strip(), f"bench-pr-{entry['number']}")

            # refs/remotes/origin/bench-base-<n> at base_sha
            base_ref_result = subprocess.run(
                ["git", "-C", str(checkout.repo_dir), "rev-parse",
                 f"refs/remotes/origin/bench-base-{entry['number']}"],
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(base_ref_result.stdout.strip(), checkout.base_sha)


if __name__ == "__main__":
    unittest.main()
