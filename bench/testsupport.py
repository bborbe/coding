#!/usr/bin/env python3
#
# testsupport.py — shared test helpers for bench unit tests
#
# Python 3 standard library only — no third-party dependencies.

import json
import os
import pathlib
import shutil
import stat
import subprocess


def build_coding_repo(root: pathlib.Path, *, rules=None, commands=None) -> pathlib.Path:
    """Create a temporary coding-repo structure under root.

    Creates root/"rules" and root/"commands" directories and writes the given
    {relative_path: text} mappings.  Defaults create one small file in each
    subdirectory so the directory is never empty.  Returns root.
    """
    root = pathlib.Path(root)
    rules_dir = root / "rules"
    commands_dir = root / "commands"

    rules = rules or {"go/sample.yml": "id: go/sample\nlevel: MUST\n"}
    commands = commands or {"sample.md": "# Sample command\n"}

    rules_dir.mkdir(parents=True, exist_ok=True)
    for rel_path, content in rules.items():
        (rules_dir / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (rules_dir / rel_path).write_text(content, encoding="utf-8")

    commands_dir.mkdir(parents=True, exist_ok=True)
    for rel_path, content in commands.items():
        (commands_dir / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (commands_dir / rel_path).write_text(content, encoding="utf-8")

    return root


def build_verify_config_dir(root: pathlib.Path, plugin_src: pathlib.Path,
                           *, use_known_marketplaces: bool = False) -> pathlib.Path:
    """Create an isolated .claude-verify directory under root.

    When use_known_marketplaces is False, copies plugin_src to
    <cfg>/plugins/marketplaces/coding.  When True, writes known_marketplaces.json
    pointing at plugin_src instead.  Returns the .claude-verify path.
    """
    root = pathlib.Path(root)
    cfg = root / ".claude-verify"
    cfg.mkdir(parents=True, exist_ok=True)

    if use_known_marketplaces:
        (cfg / "plugins").mkdir(parents=True, exist_ok=True)
        known = {
            "coding": {
                "source": {"source": "github", "repo": "bborbe/coding"},
                "installLocation": str(plugin_src),
            }
        }
        (cfg / "plugins" / "known_marketplaces.json").write_text(
            json.dumps(known), encoding="utf-8"
        )
    else:
        dest = cfg / "plugins" / "marketplaces" / "coding"
        shutil.copytree(plugin_src, dest)

    return cfg


def make_stub_bin(bin_dir: pathlib.Path, name: str, body: str) -> pathlib.Path:
    """Write bin_dir/name as an executable stub script.

    The script starts with #!/bin/sh and contains the provided body.
    chmod 0o755.  Returns the path.
    """
    bin_dir = pathlib.Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / name
    script.write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
    script.chmod(0o755)
    return script


def stub_claude(bin_dir: pathlib.Path, counter_file: pathlib.Path,
                report_text: str = "") -> pathlib.Path:
    """Install a stub `claude` executable that appends its args to counter_file.

    The stub prints report_text to stdout and exits 0.  Returns the stub path.
    """
    counter_file = pathlib.Path(counter_file)
    body = (
        f"printf '%s\\n' \"$*\" >> '{counter_file}'\n"
        f"cat <<'REPORT_EOF'\n{report_text}\nREPORT_EOF"
    )
    return make_stub_bin(bin_dir, "claude", body)


def stub_claude_failing(bin_dir: pathlib.Path, counter_file: pathlib.Path,
                         exit_code: int = 3) -> pathlib.Path:
    """Install a stub `claude` that appends args to counter_file and exits with exit_code."""
    counter_file = pathlib.Path(counter_file)
    body = (
        f"printf '%s\\n' \"$*\" >> '{counter_file}'\n"
        f"printf 'stub failure\\n' >&2\n"
        f"exit {exit_code}"
    )
    return make_stub_bin(bin_dir, "claude", body)


def with_path(bin_dir: pathlib.Path) -> dict:
    """Return a copy of os.environ with bin_dir prepended to PATH."""
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


# ----------------------------------------------------------------------
# Git-repo test helpers
# ----------------------------------------------------------------------
def init_git_repo(path: pathlib.Path) -> pathlib.Path:
    """Initialize a directory as a git repo and configure user identity.

    Creates an initial empty commit so HEAD is valid.
    Returns the path.
    """
    path = pathlib.Path(path)
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True,
                    capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test User"],
        check=True, capture_output=True, text=True,
    )
    # Create initial commit so HEAD is valid
    subprocess.run(
        ["git", "-C", str(path), "commit", "--allow-empty", "-m", "initial"],
        check=True, capture_output=True, text=True,
    )
    return path


def commit_file(repo: pathlib.Path, relpath: str, text: str,
                message: str = "commit") -> str:
    """Write a file, git add, git commit, return the resulting full SHA."""
    repo = pathlib.Path(repo)
    fpath = repo / relpath
    fpath.parent.mkdir(parents=True, exist_ok=True)
    fpath.write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", str(relpath)],
                   check=True, capture_output=True, text=True)
    result = subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", message],
        check=True, capture_output=True, text=True,
    )
    sha = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "-1", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return sha


def make_merge_repo(path: pathlib.Path) -> dict:
    """Build a repo with a real two-parent merge commit.

    Creates:
      - commit 'base' on default branch
      - branch 'feature', commit a change on it (touching a new file)
      - back to default branch, commit another change
      - git merge --no-ff feature (creates two-parent merge)

    Returns {"repo": path, "merge_sha": ..., "base_sha": ..., "head_sha": ...}
    where base_sha/head_sha are the merge's first and second parents.
    """
    path = init_git_repo(path)

    # Detect default branch name
    default_branch = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    # Commit on default branch
    base_sha = commit_file(path, "base.txt", "base content\n", "add base")

    # Branch and commit
    subprocess.run(["git", "-C", str(path), "checkout", "-b", "feature", "-q"],
                   check=True, capture_output=True, text=True)
    head_sha = commit_file(path, "feature.txt", "feature content\n", "add feature")

    # Back to default branch, commit, merge
    subprocess.run(["git", "-C", str(path), "checkout", default_branch, "-q"],
                   check=True, capture_output=True, text=True)
    commit_file(path, "main.txt", "main content\n", "add main")

    subprocess.run(
        ["git", "-C", str(path), "merge", "--no-ff", "feature", "-m", "merge"],
        check=True, capture_output=True, text=True,
    )

    merge_sha = subprocess.run(
        ["git", "-C", str(path), "rev-list", "-1", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

    return {
        "repo": path,
        "merge_sha": merge_sha,
        "base_sha": base_sha,
        "head_sha": head_sha,
    }


def make_squash_repo(path: pathlib.Path) -> dict:
    """Build a single-parent repo where head_sha == merge_sha (squash shape)."""
    path = init_git_repo(path)

    # Parent commit
    parent_sha = commit_file(path, "parent.txt", "parent content\n", "add parent")

    # The squash commit (head == merge)
    merge_sha = commit_file(path, "squash.txt", "squash content\n", "add squash")

    return {
        "repo": path,
        "merge_sha": merge_sha,
        "base_sha": parent_sha,
        "head_sha": merge_sha,
    }


def make_empty_diff_repo(path: pathlib.Path) -> dict:
    """Build a single-parent repo where base_sha == head_sha (empty diff)."""
    path = init_git_repo(path)

    # One commit
    sha = commit_file(path, "file.txt", "content\n", "add file")

    # base_sha == head_sha means the diff range will be sha..sha = empty
    return {
        "repo": path,
        "merge_sha": sha,
        "base_sha": sha,
        "head_sha": sha,
    }


def stub_git(bin_dir: pathlib.Path, log_file: pathlib.Path) -> pathlib.Path:
    """Install a stub `git` on PATH that logs every invocation to log_file.

    Each invocation appends one line: 'cwd=<cwd> args=<args...>'
    Returns the stub path.
    """
    log_file = pathlib.Path(log_file)
    body = f'printf "cwd=%s args=%s\\n" "$(pwd)" "$*" >> "{log_file}"\nexit 0'
    return make_stub_bin(bin_dir, "git", body)


def make_manifest(path: pathlib.Path, entries: list, version: str = "test-1") -> pathlib.Path:
    """Write a minimal valid manifest JSON to path and return it."""
    manifest = {"version": version, "prs": entries}
    path = pathlib.Path(path)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def seed_cached_repo(cache_root: pathlib.Path, owner: str, repo: str,
                     builder) -> dict:
    """Seed a repository under cache_root/repos/owner/repo using the given builder.

    builder is one of: make_merge_repo, make_squash_repo, make_empty_diff_repo.
    Returns the builder's result dict.
    """
    repo_path = cache_root / "repos" / owner / repo
    repo_path.mkdir(parents=True, exist_ok=True)
    return builder(repo_path)
