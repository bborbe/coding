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


def build_verify_config_dir(
    root: pathlib.Path,
    plugin_src: pathlib.Path,
    *,
    version: str = "0.35.2",
    scope: str = "user",
    project_path: pathlib.Path | None = None,
    install_path: pathlib.Path | None = None,
    extra_versions: dict | None = None,
    extra_records: list | None = None,
    marketplace_src: pathlib.Path | None = None,
    record_text: str | None = None,
    write_record: bool = True,
) -> pathlib.Path:
    """Create an isolated .claude-verify directory shaped like a real Claude Code config dir.

    Copies plugin_src to <cfg>/plugins/cache/coding/coding/<version> and writes
    <cfg>/plugins/installed_plugins.json with one record for "coding@coding".

    version         version string recorded and used as the cache directory name
    scope           "user" or "project"
    project_path    written as projectPath; required shape for scope="project"
    install_path    overrides the recorded installPath (used to record a path that is
                    stale, or one outside the config dir's plugin tree)
    extra_versions  {version: source_dir} copied to additional cache version dirs
    extra_records   raw record dicts appended after the primary record, in order
    marketplace_src copied to <cfg>/plugins/marketplaces/coding when given, so a test
                    can prove the marketplace path is not what gets hashed
    record_text     when given, written verbatim as installed_plugins.json instead of
                    the JSON structure (malformed-record cases)
    write_record    when False, installed_plugins.json is not written at all
    Returns the .claude-verify path.
    """
    cfg = pathlib.Path(root) / ".claude-verify"
    cfg.mkdir(parents=True, exist_ok=True)

    # Build the cache directory structure
    cache_root = cfg / "plugins" / "cache" / "coding" / "coding"
    default_install_path = cache_root / version

    # Copy plugin_src to the default version directory
    shutil.copytree(plugin_src, default_install_path)

    # Copy extra versions
    for extra_ver, extra_src in (extra_versions or {}).items():
        extra_dest = cache_root / extra_ver
        if extra_dest.exists():
            shutil.rmtree(extra_dest)
        shutil.copytree(extra_src, extra_dest)

    # Copy marketplace source if given
    if marketplace_src is not None:
        mkt_dir = cfg / "plugins" / "marketplaces" / "coding"
        if mkt_dir.exists():
            shutil.rmtree(mkt_dir)
        shutil.copytree(marketplace_src, mkt_dir)

    # Write installed_plugins.json
    if write_record and record_text is not None:
        record_file = cfg / "plugins" / "installed_plugins.json"
        record_file.write_text(record_text, encoding="utf-8")
    elif write_record:
        records = []
        # Primary record
        primary = {
            "scope": scope,
            "installPath": str(install_path) if install_path is not None else str(default_install_path),
            "version": version,
            "installedAt": "2026-08-08T00:00:00.000Z",
            "lastUpdated": "2026-08-08T00:00:00.000Z",
        }
        if project_path is not None:
            primary["projectPath"] = str(project_path)
        records.append(primary)
        # Extra records
        for extra in (extra_records or []):
            records.append(extra)

        record_file = cfg / "plugins" / "installed_plugins.json"
        record_file.write_text(
            json.dumps({"version": 2, "plugins": {"coding@coding": records}}, indent=2),
            encoding="utf-8",
        )

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


def review_report(*, must_fix: str | None = "None.", should_fix: str | None = "None.",
                  nice_to_have: str | None = "None.", heading_level: int = 2,
                  preamble: str = "", trailing: str = "") -> str:
    """Build a review-shaped stub payload.

    Renders the three mandatory sections at heading_level, in the order Must Fix,
    Should Fix, Nice to Have, each carrying the given body.  Passing None for a
    section omits that section entirely, which is how a non-review payload is
    built.  preamble is emitted before the first section and trailing after the
    last one, both verbatim and both empty by default.
    """
    hashes = "#" * heading_level
    parts = [preamble]
    for name, body in [
        ("Must Fix", must_fix),
        ("Should Fix", should_fix),
        ("Nice to Have", nice_to_have),
    ]:
        if body is not None:
            annotation = "(Critical)" if name == "Must Fix" else "(Important)" if name == "Should Fix" else "(Optional)"
            parts.append(f"{hashes} {name} {annotation}")
            parts.append(body)
    parts.append(trailing)
    return "\n".join(parts)


# Module-level clean review for common use
CLEAN_REVIEW_REPORT = review_report()


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


def seed_one_pr_manifest(td: pathlib.Path, cache_root: pathlib.Path) -> pathlib.Path:
    """Seed one merge repo under cache_root and write a one-entry manifest.

    Creates <cache_root>/repos/testowner/repo_a via make_merge_repo and writes
    <td>/manifest.json with a single entry id "test#1", number 1, merge_strategy
    "merge-commit" and that repo's three SHAs.  Returns the manifest path.
    """
    repos_root = cache_root / "repos"
    repos_root.mkdir(parents=True, exist_ok=True)
    repo_a = repos_root / "testowner" / "repo_a"
    repo_a.mkdir(parents=True, exist_ok=True)
    info_a = make_merge_repo(repo_a)

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
    make_manifest(manifest_path, manifest_entries)
    return manifest_path


def seed_cached_repo(cache_root: pathlib.Path, owner: str, repo: str,
                     builder) -> dict:
    """Seed a repository under cache_root/repos/owner/repo using the given builder.

    builder is one of: make_merge_repo, make_squash_repo, make_empty_diff_repo.
    Returns the builder's result dict.
    """
    repo_path = cache_root / "repos" / owner / repo
    repo_path.mkdir(parents=True, exist_ok=True)
    return builder(repo_path)
