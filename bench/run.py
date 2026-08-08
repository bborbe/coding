#!/usr/bin/env python3
#
# run.py — benchmark runner for /coding:pr-review
#
# Executes the real /coding:pr-review slash command against every PR entry in a
# frozen PR manifest, in an isolated Claude config directory, and records a
# machine-readable result row per PR.
#
# Exit semantics:
#   0 — every PR produced a row (ok or cache hit)
#   1 — one or more PRs failed
#   2 — usage error, manifest problem, or preflight failure (e.g. plugin mismatch)
#
# Paths are resolved relative to the script's own location:
#   bench/run.py  →  BENCH_DIR = bench/  →  REPO_ROOT = repo root
#
# Python 3 standard library only — no third-party dependencies.

import argparse
import dataclasses
import datetime
import hashlib
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

# ----------------------------------------------------------------------
# Module constants
# ----------------------------------------------------------------------
RUNNER_VERSION = "1"
REVIEW_TIMEOUT_SECONDS = 45 * 60
BENCH_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent
VERIFY_CONFIG_DIR_NAME = ".claude-verify"
HASHED_SUBDIRS = ("rules", "commands")
VALID_MODES = ("short", "full", "selector")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PR_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*#[0-9]+$")
REQUIRED_SECTION_NAMES = ("Must Fix", "Should Fix", "Nice to Have")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")
SEVERITY_SUFFIX_RE = re.compile(r"\s*\([^)]+\)\s*$")
THEMATIC_BREAK_RE = re.compile(r"^ {0,3}(?:-{3,}|\*{3,}|_{3,}) *$")
FENCE_RE = re.compile(r"^ {0,3}(?:```|~~~)")
BULLET_RE = re.compile(r"^\s{0,3}([-*])\s+(.+)$")
_SECTION_BY_LOWER = {name.lower(): name for name in REQUIRED_SECTION_NAMES}
REQUIRED_ENTRY_FIELDS = (
    "id", "owner", "repo", "number",
    "merge_strategy", "merge_sha", "base_sha", "head_sha", "changed_files",
)

# Ref pruning (frozen invariant — the prepared working copy offers one target branch)
KEEP_REF_NAMESPACE = "refs/bench/keep"
PRUNED_REF_NAMESPACES = ("refs/heads", "refs/remotes", "refs/tags")
DEFAULT_BRANCH_SYMREF = "refs/remotes/origin/HEAD"

# Gate constants (frozen invariants — not configurable)
NON_REVIEW_MARKER = "NOT A REVIEW"
REJECTION_EXCERPT_BYTES = 2000

# Plugin resolution constants
PLUGIN_NAME = "coding"
INSTALLED_PLUGINS_FILENAME = "installed_plugins.json"

# Preflight abort markers (frozen literals — tests and the README quote them)
PLUGIN_RESOLUTION_MISMATCH_MARKER = "PLUGIN RESOLUTION MISMATCH"
NO_INSTALL_RECORD_MARKER = "NO PLUGIN INSTALL RECORD"
UNREADABLE_INSTALL_RECORD_MARKER = "UNREADABLE PLUGIN INSTALL RECORD"
STALE_INSTALL_PATH_MARKER = "STALE PLUGIN INSTALL PATH"
OUT_OF_TREE_INSTALL_PATH_MARKER = "PLUGIN INSTALL PATH OUT OF TREE"
SCOPE_MISMATCH_MARKER = "PLUGIN INSTALL SCOPE MISMATCH"

# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------
class BenchError(Exception):
    """Every abort that maps to exit code 2 (manifest, preflight, lock)."""
    pass


# ----------------------------------------------------------------------
# Content hashing — content-derived, not git-derived
# ----------------------------------------------------------------------
def content_hash(root: pathlib.Path) -> str:
    """Return SHA-256 hex digest of all regular files under root/rules and root/commands.

    Skips any path with a .git component.  Files are ordered by POSIX-relative
    path so the digest is independent of filesystem iteration order.  Each file
    contributes: relative_path_bytes \\0 file_length \\0 raw_bytes — length-
    framing prevents two different layouts from producing the same byte stream.
    Raises BenchError if neither rules nor commands subdirectory exists.
    """
    dirs_to_scan = [root / subdir for subdir in HASHED_SUBDIRS]
    if not any(d.is_dir() for d in dirs_to_scan):
        raise BenchError(
            f"{root} does not look like a coding-plugin checkout: "
            f"neither rules/ nor commands/ found"
        )

    collected: list[pathlib.Path] = []
    for subdir in dirs_to_scan:
        if not subdir.is_dir():
            continue
        for p in subdir.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                collected.append(p)

    collected.sort(key=lambda p: p.relative_to(root).as_posix())

    h = hashlib.sha256()
    for p in collected:
        rel = p.relative_to(root).as_posix()
        size = p.stat().st_size
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(str(size).encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())

    return h.hexdigest()


def config_hash(rules_commands_hash: str, model: str, effort: str,
                mode: str, prs_version: str) -> str:
    """SHA-256 over the five configuration-identity components.

    Mode is a first-class component: changing only mode must produce a different digest.
    """
    payload = "\0".join([rules_commands_hash, model, effort, mode, prs_version])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------
# Manifest loading and validation
# ----------------------------------------------------------------------
def load_manifest(path: pathlib.Path) -> dict:
    """Load and validate a PR manifest JSON file.

    Requires top-level "version" (non-empty str) and "prs" (non-empty list).
    Validates every entry's required fields, character-set restrictions on
    owner/repo/id (path-traversal guard), and SHA format on *_sha fields.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as err:
        raise BenchError(f"cannot read manifest {path}: {err}")
    except json.JSONDecodeError as err:
        raise BenchError(f"manifest {path} is not valid JSON: {err}")

    if not data.get("version"):
        raise BenchError("manifest missing required field: 'version'")
    if not isinstance(data.get("prs"), list) or not data["prs"]:
        raise BenchError("manifest missing required field: 'prs' (must be non-empty list)")

    for index, entry in enumerate(data["prs"]):
        entry_id = entry.get("id", "")
        for field in REQUIRED_ENTRY_FIELDS:
            val = entry.get(field)
            # changed_files must be int (0 is valid); everything else must be non-empty
            if field == "changed_files":
                if not isinstance(val, int):
                    raise BenchError(
                        f"manifest entry {index} (id={entry_id!r}): "
                        f"field {field!r} must be an int, got {type(val).__name__}"
                    )
            else:
                if not val and val != 0:
                    raise BenchError(
                        f"manifest entry {index} (id={entry_id!r}): "
                        f"missing or empty required field {field!r}"
                    )

        # Path-traversal guard: owner/repo must be simple GitHub names
        owner: str = entry.get("owner", "")
        repo: str = entry.get("repo", "")
        if not NAME_RE.match(owner):
            raise BenchError(
                f"manifest entry {entry_id!r}: invalid owner {owner!r} "
                f"(must match {NAME_RE.pattern!r})"
            )
        if not NAME_RE.match(repo):
            raise BenchError(
                f"manifest entry {entry_id!r}: invalid repo {repo!r} "
                f"(must match {NAME_RE.pattern!r})"
            )
        if not PR_ID_RE.match(entry_id):
            raise BenchError(
                f"manifest entry {index}: invalid id {entry_id!r} "
                f"(must match {PR_ID_RE.pattern!r})"
            )
        number: int = entry.get("number", 0)
        if not isinstance(number, int) or number <= 0:
            raise BenchError(
                f"manifest entry {entry_id!r}: invalid number {number!r} "
                f"(must be int > 0)"
            )

        for sha_field in ("merge_sha", "base_sha", "head_sha"):
            sha_val: str = entry.get(sha_field, "")
            if not re.match(r"^[0-9a-f]{7,40}$", sha_val):
                raise BenchError(
                    f"manifest entry {entry_id!r}: {sha_field} {sha_val!r} "
                    f"must match ^[0-9a-f]{{7,40}}$"
                )

    return data


def safe_pr_key(pr_id: str) -> str:
    """Return pr_id with # replaced by _ (safe for use in filenames).

    Assumes pr_id already passed PR_ID_RE validation.
    """
    return pr_id.replace("#", "_")


# ----------------------------------------------------------------------
# Path helpers
# ----------------------------------------------------------------------
def repos_root(cache_root: pathlib.Path) -> pathlib.Path:
    return cache_root / "repos"


def repo_cache_dir(cache_root: pathlib.Path, owner: str, repo: str) -> pathlib.Path:
    return repos_root(cache_root) / owner / repo


def worktree_dir(cache_root: pathlib.Path, owner: str, repo: str, number: int) -> pathlib.Path:
    return repos_root(cache_root) / owner / f"{repo}__pr{number}"


def assert_under(path: pathlib.Path, root: pathlib.Path) -> pathlib.Path:
    """Resolve both paths and verify path is strictly under root.

    Raises BenchError if resolved path equals root or is not a sub-path.
    The message names both path and root and states the runner only touches its own cache.
    """
    resolved = path.resolve()
    root_resolved = root.resolve()
    if resolved == root_resolved or not resolved.is_relative_to(root_resolved):
        raise BenchError(
            f"path {path!r} is not under root {root!r}; "
            f"the runner only ever touches its own cache at {root!r}"
        )
    return resolved


def installed_plugins_path(config_dir: pathlib.Path) -> pathlib.Path:
    return config_dir / "plugins" / INSTALLED_PLUGINS_FILENAME


def plugin_cache_root(config_dir: pathlib.Path) -> pathlib.Path:
    return config_dir / "plugins" / "cache"


def path_is_under(path: pathlib.Path, root: pathlib.Path) -> bool:
    """True when path resolves strictly under root (never equal to it)."""
    resolved = pathlib.Path(path).resolve()
    root_resolved = pathlib.Path(root).resolve()
    return resolved != root_resolved and resolved.is_relative_to(root_resolved)


def keep_ref_name(number: int, label: str) -> str:
    """Full refname under KEEP_REF_NAMESPACE holding one manifest SHA for this PR.

    label is one of "merge", "base", "head".  These refs live outside refs/heads/
    and refs/remotes/, so they keep the manifest's commits reachable without
    appearing in `git branch -a` and without becoming a target-branch candidate.
    """
    return f"{KEEP_REF_NAMESPACE}/{number}/{label}"


def synthetic_ref_names(number: int) -> tuple[str, str, str]:
    """The exact three refs a prepared working copy is allowed to carry.

    Returns (refs/heads/bench-pr-<n>, refs/remotes/origin/bench-base-<n>,
    refs/remotes/origin/bench-pr-<n>) — the checked-out head branch and the two
    synthetic remote-tracking refs prepare_worktree publishes.  The branch names
    must stay byte-identical to the f-strings prepare_worktree already builds
    (`bench-base-{number}`, `bench-pr-{number}`); derive them from one place so
    they cannot drift.
    """
    return (
        f"refs/heads/bench-pr-{number}",
        f"refs/remotes/origin/bench-base-{number}",
        f"refs/remotes/origin/bench-pr-{number}",
    )


# ----------------------------------------------------------------------
# Cache and ledger path helpers
# ----------------------------------------------------------------------
def reviews_root(cache_root: pathlib.Path) -> pathlib.Path:
    return cache_root / "reviews"


def failures_root(cache_root: pathlib.Path) -> pathlib.Path:
    return cache_root / "failures"


def cache_key(cfg_hash: str, pr_id: str) -> str:
    return f"{cfg_hash}__{safe_pr_key(pr_id)}"


def cache_row_path(cache_root: pathlib.Path, cfg_hash: str, pr_id: str) -> pathlib.Path:
    return reviews_root(cache_root) / f"{cache_key(cfg_hash, pr_id)}.json"


def cache_raw_path(cache_root: pathlib.Path, cfg_hash: str, pr_id: str) -> pathlib.Path:
    return reviews_root(cache_root) / f"{cache_key(cfg_hash, pr_id)}.stdout.txt"


def failure_log_path(cache_root: pathlib.Path, cfg_hash: str, pr_id: str) -> pathlib.Path:
    return failures_root(cache_root) / f"{cache_key(cfg_hash, pr_id)}.stderr.txt"


def ledger_path(results_dir: pathlib.Path) -> pathlib.Path:
    return results_dir / "results.jsonl"


def lock_path(results_dir: pathlib.Path) -> pathlib.Path:
    return results_dir / ".lock"


# ----------------------------------------------------------------------
# Single-instance lock
# ----------------------------------------------------------------------
class BenchLock:
    """Single-instance lock that aborts if another bench run is active."""

    def __init__(self, results_dir: pathlib.Path) -> None:
        self._results_dir = results_dir
        self._fd = None

    def __enter__(self) -> "BenchLock":
        lp = lock_path(self._results_dir)
        try:
            self._fd = os.open(
                str(lp),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644,
            )
        except FileExistsError:
            raise BenchError(
                f"another bench run is in progress; "
                f"remove the lock file to clear it: {lp}"
            )
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        os.write(self._fd, f"{os.getpid()} {ts}\n".encode("utf-8"))
        os.close(self._fd)
        self._fd = None
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            os.unlink(lock_path(self._results_dir))
        except FileNotFoundError:
            pass


# ----------------------------------------------------------------------
# Atomic append-only ledger
# ----------------------------------------------------------------------
def atomic_write_bytes(path: pathlib.Path, data: bytes) -> None:
    """Write data atomically to path via rename from a same-directory temp file."""
    tmp = tempfile.NamedTemporaryFile(
        dir=str(path.parent),
        delete=False,
    )
    try:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, str(path))
    except Exception:
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass
        raise


def append_row(results_dir: pathlib.Path, row: dict) -> None:
    """Append one JSON row to the ledger atomically."""
    lp = ledger_path(results_dir)
    existing = b""
    if lp.exists():
        existing = lp.read_bytes()
    encoded = json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    atomic_write_bytes(lp, existing + encoded)


# ----------------------------------------------------------------------
# Git helpers
# ----------------------------------------------------------------------
def fetch_url(owner: str, repo: str) -> str:
    """Build GitHub fetch URL from manifest owner/repo pair.

    The runner never reads or depends on a remote named 'origin'.
    """
    return f"https://github.com/{owner}/{repo}"


def git(args, *, repo_dir: pathlib.Path, cache_root: pathlib.Path,
        check: bool = True, timeout: int = 600) -> subprocess.CompletedProcess:
    """Single git subprocess chokepoint — every git invocation goes through here.

    - Always uses -C <repo_dir>; never cwd= or shell strings.
    - repo_dir must already exist.
    - assert_under runs before subprocess to catch escaped manifest values.
    - subprocess.TimeoutExpired propagates; callers convert it to per-PR failures.
    """
    target = assert_under(repo_dir, repos_root(cache_root))
    cmd = ["git", "-C", str(target), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise BenchError(
            f"git {' '.join(args)} failed in {target} (exit {proc.returncode}): "
            f"{proc.stderr.strip()}"
        )
    return proc


def ensure_refs(cache_root: pathlib.Path, entry: dict) -> pathlib.Path:
    """Prepare repo cache dir so entry's three SHAs are locally reachable.

    Returns the repo directory path.
    """
    repo_dir = repo_cache_dir(cache_root, entry["owner"], entry["repo"])
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Init if not a git repo
    if not (repo_dir / ".git").exists():
        git(["init", "--quiet"], repo_dir=repo_dir, cache_root=cache_root)

    # Offline short-circuit: check if all three SHAs resolve locally
    for sha_field in ("merge_sha", "base_sha", "head_sha"):
        sha = entry[sha_field]
        proc = git(["cat-file", "-e", f"{sha}^{{commit}}"],
                   repo_dir=repo_dir, cache_root=cache_root, check=False)
        if proc.returncode != 0:
            break
    else:
        # All three SHAs resolved — skip fetch
        return repo_dir

    # Fetch from manifest URL (never 'origin')
    url = fetch_url(entry["owner"], entry["repo"])
    git([
        "fetch", "--no-tags", "--force", url,
        f"+pull/{entry['number']}/head:refs/bench/pr{entry['number']}/head",
        "+refs/heads/*:refs/remotes/origin/*",
    ], repo_dir=repo_dir, cache_root=cache_root)

    return repo_dir


def resolve_diff_range(cache_root: pathlib.Path, repo_dir: pathlib.Path,
                       entry: dict) -> tuple[str, str, str, int, list]:
    """Resolve the correct diff range by inspecting the merge commit's parent count.

    Returns (diff_range, base_endpoint, head_endpoint, parent_count, notes).
    """
    out = git(
        ["rev-list", "--parents", "-n", "1", entry["merge_sha"]],
        repo_dir=repo_dir, cache_root=cache_root,
    ).stdout.split()

    if not out:
        raise BenchError(
            f"{entry['id']}: cannot resolve merge commit {entry['merge_sha']}"
        )

    n_parents = len(out) - 1
    notes: list = []

    if n_parents >= 2:
        base = f"{entry['merge_sha']}^1"
        head = f"{entry['merge_sha']}^2"
    elif n_parents == 1:
        base = entry["base_sha"]
        head = entry["head_sha"]
    else:
        raise BenchError(
            f"{entry['id']}: merge commit {entry['merge_sha']} has no parents; "
            f"cannot reconstruct a diff range"
        )

    # Strategy-label mismatch: report but use correct range
    label = entry.get("merge_strategy", "")
    if label == "merge-commit" and n_parents == 1:
        notes.append(f"strategy mismatch (manifest={label}, parents={n_parents})")
    elif label == "squash" and n_parents >= 2:
        notes.append(f"strategy mismatch (manifest={label}, parents={n_parents})")

    return f"{base}..{head}", base, head, n_parents, notes


def changed_files(cache_root: pathlib.Path, repo_dir: pathlib.Path,
                 diff_range: str) -> list[str]:
    """Return sorted list of files changed in the diff range."""
    proc = git(["diff", "--name-only", diff_range],
               repo_dir=repo_dir, cache_root=cache_root)
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


@dataclasses.dataclass
class PrCheckout:
    pr_id: str
    repo_dir: pathlib.Path
    worktree: pathlib.Path
    base_branch: str
    head_branch: str
    diff_range: str
    base_sha: str
    head_sha: str
    changed_files: int
    parent_count: int
    notes: list


@dataclasses.dataclass
class PluginInstallRecord:
    plugin_key: str
    scope: str
    install_path: pathlib.Path
    version: str
    project_path: pathlib.Path | None


@dataclasses.dataclass
class PluginResolution:
    load_path: pathlib.Path
    version: str
    content_hash: str


def prepare_worktree(cache_root: pathlib.Path, repo_dir: pathlib.Path,
                    entry: dict, base_endpoint: str,
                    head_endpoint: str) -> PrCheckout:
    """Resolve endpoints to SHAs, publish remote-tracking refs, create working copy.

    Returns PrCheckout with all resolved fields.
    """
    wt = worktree_dir(cache_root, entry["owner"], entry["repo"], entry["number"])
    base_branch = f"bench-base-{entry['number']}"
    head_branch = f"bench-pr-{entry['number']}"

    base_sha = git(
        ["rev-parse", f"{base_endpoint}^{{commit}}"],
        repo_dir=repo_dir, cache_root=cache_root,
    ).stdout.strip()
    head_sha = git(
        ["rev-parse", f"{head_endpoint}^{{commit}}"],
        repo_dir=repo_dir, cache_root=cache_root,
    ).stdout.strip()

    # Publish remote-tracking refs so /coding:pr-review can resolve origin/<branch>
    git(["update-ref", f"refs/remotes/origin/{base_branch}", base_sha],
        repo_dir=repo_dir, cache_root=cache_root)
    git(["update-ref", f"refs/remotes/origin/{head_branch}", head_sha],
        repo_dir=repo_dir, cache_root=cache_root)

    # Tear down any stale copy from a previous run
    git(["worktree", "remove", "--force", str(wt)],
        repo_dir=repo_dir, cache_root=cache_root, check=False)
    if wt.exists():
        assert_under(wt, repos_root(cache_root))
        shutil.rmtree(wt, ignore_errors=True)
    git(["branch", "-D", head_branch],
        repo_dir=repo_dir, cache_root=cache_root, check=False)
    git(["worktree", "prune"], repo_dir=repo_dir, cache_root=cache_root, check=False)

    # Validate worktree path before creating
    assert_under(wt, repos_root(cache_root))
    git(["worktree", "add", "--force", "-b", head_branch, str(wt), head_sha],
        repo_dir=repo_dir, cache_root=cache_root)

    # Anchor manifest SHAs before pruning, then prune to exactly the synthetic refs
    publish_keep_refs(cache_root, repo_dir, entry)
    prune_refs(cache_root, repo_dir, entry["number"])

    return PrCheckout(
        pr_id=entry["id"],
        repo_dir=repo_dir,
        worktree=wt,
        base_branch=base_branch,
        head_branch=head_branch,
        diff_range="",  # filled by caller
        base_sha=base_sha,
        head_sha=head_sha,
        changed_files=0,  # filled by caller
        parent_count=0,  # filled by caller
        notes=[],  # filled by caller
    )


def publish_keep_refs(cache_root: pathlib.Path, repo_dir: pathlib.Path,
                      entry: dict) -> None:
    """Anchor the manifest's three SHAs under refs/bench/keep/<number>/ before pruning.

    Without these the merge commit becomes unreachable the moment the upstream
    branches are deleted, and a later git gc could discard it — which would break
    ensure_refs' offline short-circuit and force a network fetch on every run.
    """
    number = entry["number"]
    for label, sha_field in [("merge", "merge_sha"), ("base", "base_sha"), ("head", "head_sha")]:
        git(
            ["update-ref", keep_ref_name(number, label), entry[sha_field]],
            repo_dir=repo_dir, cache_root=cache_root, check=False,
        )


def prune_refs(cache_root: pathlib.Path, repo_dir: pathlib.Path,
               number: int) -> list[str]:
    """Reduce repo_dir to exactly the three synthetic refs for this PR.

    Deletes every ref under refs/heads/, refs/remotes/ and refs/tags/ that is not
    one of synthetic_ref_names(number), and unsets the default-branch symref, so
    `git branch -a` in the prepared working copy enumerates exactly one head branch
    and two remote-tracking refs and the reviewer has no alternative target to ask
    about.  Returns the refnames deleted, sorted, for logging and assertions.

    Idempotent: a second call over an already-pruned repository deletes nothing and
    returns [].  Every git invocation goes through git(), so the destructive step
    inherits the safety invariant that repo_dir lies under bench/.cache/repos/.
    """
    # Remove the default-branch symref (absent → exit 128, which is fine)
    git(["symbolic-ref", "-d", DEFAULT_BRANCH_SYMREF],
        repo_dir=repo_dir, cache_root=cache_root, check=False)

    # Enumerate all refs in the namespaces we prune
    proc = git(
        ["for-each-ref", "--format=%(refname)", *PRUNED_REF_NAMESPACES],
        repo_dir=repo_dir, cache_root=cache_root,
    )
    all_refs = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    keep = set(synthetic_ref_names(number))
    to_delete = sorted(r for r in all_refs if r not in keep)

    for refname in to_delete:
        git(["update-ref", "-d", refname],
            repo_dir=repo_dir, cache_root=cache_root, check=False)

    return to_delete


def resolve_pr(cache_root: pathlib.Path, entry: dict) -> PrCheckout:
    """Tie together ensure_refs → resolve_diff_range → changed_files → empty-diff gate → prepare_worktree.

    Raises BenchError (never returns) if diff range is empty.
    """
    repo_dir = ensure_refs(cache_root, entry)
    diff_range, base_endpoint, head_endpoint, n_parents, notes = resolve_diff_range(
        cache_root, repo_dir, entry
    )

    files = changed_files(cache_root, repo_dir, diff_range)
    if not files:
        raise BenchError(
            f"EMPTY DIFF: {entry['id']} resolved range {diff_range} contains zero changed files. "
            f"This is never recorded as a zero-finding review — two independent code paths produce "
            f"this state and both look identical to a genuinely clean PR. "
            f"Re-verify the SHAs with: gh api repos/{entry['owner']}/{entry['repo']}/compare/{entry['base_sha']}...{entry['head_sha']} --jq '.files | length'"
        )

    checkout = prepare_worktree(cache_root, repo_dir, entry, base_endpoint, head_endpoint)
    checkout.diff_range = diff_range
    checkout.changed_files = len(files)
    checkout.parent_count = n_parents
    checkout.notes = notes
    return checkout


# ----------------------------------------------------------------------
# Plugin resolution preflight
# ----------------------------------------------------------------------
def verify_config_dir() -> pathlib.Path:
    """Return pathlib.Path(HOME) / .claude-verify.

    Raises BenchError if HOME is not set or empty.
    """
    home = os.environ.get("HOME", "")
    if not home:
        raise BenchError(
            f"cannot locate isolated Claude config directory ~/{VERIFY_CONFIG_DIR_NAME}: "
            f"HOME environment variable is not set or empty"
        )
    return pathlib.Path(home) / VERIFY_CONFIG_DIR_NAME


def load_install_records(config_dir: pathlib.Path) -> list[PluginInstallRecord]:
    """Read every install record the config dir holds for the coding plugin.

    Records are returned in file order.  Raises BenchError naming the record file
    when the file is absent, unreadable, not JSON, structurally wrong, or holds no
    entry for the plugin.  There is no fallback: an unresolvable record aborts.
    """
    record_file = installed_plugins_path(config_dir)
    if not record_file.is_file():
        raise BenchError(
            f"{NO_INSTALL_RECORD_MARKER}: {record_file} does not exist; "
            f"the isolated config directory {config_dir} holds no install record "
            f"for plugin {PLUGIN_NAME!r}. Install the plugin into that config "
            f"directory and re-run."
        )
    try:
        data = json.loads(record_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise BenchError(
            f"{UNREADABLE_INSTALL_RECORD_MARKER}: cannot read {record_file}: {err}"
        )
    if not isinstance(data, dict) or not isinstance(data.get("plugins"), dict):
        raise BenchError(
            f"{UNREADABLE_INSTALL_RECORD_MARKER}: {record_file} has no 'plugins' object"
        )

    records: list[PluginInstallRecord] = []
    for key, entries in data["plugins"].items():
        if key != PLUGIN_NAME and not key.startswith(PLUGIN_NAME + "@"):
            continue
        if not isinstance(entries, list):
            raise BenchError(
                f"{UNREADABLE_INSTALL_RECORD_MARKER}: "
                f"{record_file}: entry {key!r} is not a list of records"
            )
        for elem in entries:
            if not isinstance(elem, dict):
                raise BenchError(
                    f"{UNREADABLE_INSTALL_RECORD_MARKER}: "
                    f"{record_file}: entry {key!r} is not a list of records"
                )
            install_path_str = str(elem.get("installPath", ""))
            if not install_path_str:
                raise BenchError(
                    f"{UNREADABLE_INSTALL_RECORD_MARKER}: {record_file}: "
                    f"entry {key!r} has no 'installPath'"
                )
            records.append(PluginInstallRecord(
                plugin_key=key,
                scope=str(elem.get("scope", "")),
                install_path=pathlib.Path(install_path_str),
                version=str(elem.get("version", "")),
                project_path=(
                    pathlib.Path(str(elem["projectPath"]))
                    if elem.get("projectPath") else None
                ),
            ))

    if not records:
        raise BenchError(
            f"{NO_INSTALL_RECORD_MARKER}: {record_file} holds no install record "
            f"for plugin {PLUGIN_NAME!r}; the isolated config directory {config_dir} "
            f"will not load it. Install the plugin into that config directory and re-run."
        )
    return records


def record_applies(record: PluginInstallRecord, review_root: pathlib.Path) -> bool:
    """True when this record is one Claude Code would load for the review's cwd.

    A user-scoped record always applies.  A project-scoped record applies only when
    review_root is the recorded project path or lives under it.  Any other scope
    value never applies.
    """
    if record.scope == "user":
        return True
    if record.scope == "project":
        if record.project_path is None:
            return False
        rp = review_root.resolve()
        pp = record.project_path.resolve()
        return rp == pp or rp.is_relative_to(pp)
    return False


def select_install_record(records: list[PluginInstallRecord],
                          *, config_dir: pathlib.Path,
                          review_root: pathlib.Path) -> PluginInstallRecord:
    """Return the first record that applies to this run, or abort naming all of them."""
    for record in records:
        if record_applies(record, review_root):
            return record

    # No record applied — abort with full diagnostics
    lines = []
    for record in records:
        pp = str(record.project_path) if record.project_path else "<none>"
        lines.append(
            f"[scope={record.scope} projectPath={pp} "
            f"version={record.version} installPath={record.install_path}]"
        )
    raise BenchError(
        f"{SCOPE_MISMATCH_MARKER}: no applicable install record for plugin "
        f"{PLUGIN_NAME!r} in {installed_plugins_path(config_dir)}; "
        f"records: {' '.join(lines)}; "
        f"review_root={review_root}; "
        f"install the plugin at user scope in {config_dir}"
    )


def resolve_plugin_load_path(config_dir: pathlib.Path,
                             review_root: pathlib.Path) -> PluginResolution:
    """Resolve and hash the directory the review will really load the plugin from."""
    records = load_install_records(config_dir)
    record = select_install_record(records, config_dir=config_dir, review_root=review_root)

    # Out-of-tree guard — validate before reading anything from the path
    if not path_is_under(record.install_path, plugin_cache_root(config_dir)):
        raise BenchError(
            f"{OUT_OF_TREE_INSTALL_PATH_MARKER}: install path {record.install_path} "
            f"recorded in {installed_plugins_path(config_dir)} is not under "
            f"{plugin_cache_root(config_dir)}; refusing to read a plugin from outside "
            f"the isolated config directory's own plugin tree"
        )

    # Stale-path guard
    if not record.install_path.is_dir():
        raise BenchError(
            f"{STALE_INSTALL_PATH_MARKER}: {installed_plugins_path(config_dir)} records "
            f"version {record.version} at {record.install_path}, which does not exist "
            f"on disk; the plugin will not load and every slash command would be unknown. "
            f"Reinstall the plugin and re-run."
        )

    # Hash the recorded path
    try:
        digest = content_hash(record.install_path)
    except BenchError as err:
        raise BenchError(
            f"{STALE_INSTALL_PATH_MARKER}: {installed_plugins_path(config_dir)} records "
            f"version {record.version} at {record.install_path}, which is not a usable "
            f"plugin directory: {err}"
        )

    return PluginResolution(
        load_path=record.install_path,
        version=record.version,
        content_hash=digest,
    )


def check_plugin_resolution(coding_repo: pathlib.Path, config_dir: pathlib.Path,
                            expected_hash: str,
                            review_root: pathlib.Path) -> PluginResolution:
    """Verify the isolated config dir will load the coding plugin from coding_repo.

    Resolves the load path from the install record, hashes it, and raises
    BenchError (PLUGIN RESOLUTION MISMATCH) when that hash differs from
    expected_hash.  Runs before any PR is resolved and before any review subprocess
    starts.
    """
    resolution = resolve_plugin_load_path(config_dir, review_root)
    if resolution.content_hash != expected_hash:
        raise BenchError(
            f"{PLUGIN_RESOLUTION_MISMATCH_MARKER}: config_dir={config_dir} "
            f"load_path={resolution.load_path} recorded_version={resolution.version} "
            f"actual_hash={resolution.content_hash} "
            f"coding_repo={coding_repo} expected_hash={expected_hash} "
            f"refusing to record a configuration hash that did not run"
        )
    return resolution


def resolution_line(resolution: PluginResolution) -> str:
    """One-line statement of what the preflight resolved, for the operator to cross-check."""
    return (
        f"plugin load path: {resolution.load_path} "
        f"version={resolution.version} hash={resolution.content_hash}"
    )


# ----------------------------------------------------------------------
# Review invocation
# ----------------------------------------------------------------------
def build_review_argv(*, model: str, effort: str, mode: str,
                       base_branch: str) -> list[str]:
    """Build the claude argv for a /coding:pr-review invocation."""
    return [
        "claude",
        "--print",
        "--model", model,
        "--effort", effort,
        "--permission-mode", "bypassPermissions",
        f"/coding:pr-review {base_branch} {mode}",
    ]


def review_env(config_dir: pathlib.Path) -> dict:
    """Build the environment for an isolated review subprocess."""
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    env["DISABLE_AUTOUPDATER"] = "1"
    return env


def invoke_review(*, argv: list[str], worktree: pathlib.Path,
                  cache_root: pathlib.Path,
                  config_dir: pathlib.Path) -> subprocess.CompletedProcess:
    """Run the review subprocess and return the completed process."""
    assert_under(worktree, repos_root(cache_root))
    return subprocess.run(
        argv,
        cwd=str(worktree),
        env=review_env(config_dir),
        capture_output=True,
        text=True,
        timeout=REVIEW_TIMEOUT_SECONDS,
    )


# ----------------------------------------------------------------------
# Harvesting
# ----------------------------------------------------------------------
def load_rule_ids(coding_repo: pathlib.Path) -> set:
    """Load all rule IDs from the rules/index.json file.

    Tries coding_repo first; falls back to REPO_ROOT (for test environments
    where coding_repo is a minimal temp directory without the full index).
    """
    index_path = coding_repo / "rules" / "index.json"
    if not index_path.is_file():
        index_path = REPO_ROOT / "rules" / "index.json"
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise BenchError(f"cannot load rules/index.json from {coding_repo}: {err}")
    if not isinstance(data, list):
        raise BenchError(f"rules/index.json is not a JSON list: {index_path}")
    return {entry["id"] for entry in data if "id" in entry}


def _extract_rule_id(text: str, known_rule_ids: set) -> str | None:
    """Extract the first rule ID token from text, or None."""
    for token in re.split(r"[\s`\(\)\[\],:]+", text):
        if token in known_rule_ids:
            return token
    return None


def _extract_path_line(text: str, known_rule_ids: set) -> tuple[str | None, int | None]:
    """Extract the first path:line reference from text, skipping known rule IDs.

    A path:line is a token containing a dot extension followed by :NN.
    A token that is a known rule ID is never treated as a path.
    """
    # Find all potential path:line matches
    for m in re.finditer(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9_./-]+):(\d+)", text):
        candidate = m.group(1)
        if candidate not in known_rule_ids:
            return candidate, int(m.group(2))
    return None, None


def heading_section_name(line: str) -> str | None:
    """Return the canonical findings-section name a markdown heading line names, or None.

    Matches a heading at any level 1-6, strips a trailing parenthesised severity
    annotation such as "(Critical)", and compares case-insensitively against
    REQUIRED_SECTION_NAMES.  Returns the canonical spelling ("Must Fix",
    "Should Fix", "Nice to Have") or None when the line is not a heading or names
    something else.
    """
    m = HEADING_RE.match(line)
    if not m:
        return None
    stripped = m.group(1).strip()
    stripped = SEVERITY_SUFFIX_RE.sub("", stripped).strip()
    return _SECTION_BY_LOWER.get(stripped.lower())


def iter_report_lines(report_text: str):
    """Yield (line, in_fence) for every line of report_text.

    in_fence is True for the fence delimiter lines themselves and for every line
    between an opening and a closing fence.  A line inside a fence is never a
    heading, never a thematic break and never a bullet; it is ordinary text.
    """
    in_fence = False
    for line in report_text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            yield (line, True)
        else:
            yield (line, in_fence)


def missing_sections(report_text: str) -> list[str]:
    """Return the required findings-section names absent from report_text, in canonical order.

    A section counts as present only when it appears as a markdown heading at any
    level 1-6 outside a fenced code block.  The words appearing in prose, in a
    bold run, or inside a fence do not count.  Returns [] when all three are present.
    """
    present: set[str] = set()
    for line, in_fence in iter_report_lines(report_text):
        if in_fence:
            continue
        name = heading_section_name(line)
        if name is not None:
            present.add(name)
    return [name for name in REQUIRED_SECTION_NAMES if name not in present]


def rejection_excerpt(text: str, limit: int = REJECTION_EXCERPT_BYTES) -> str:
    """Return at most limit bytes of text's UTF-8 prefix, marked when truncated."""
    encoded = text.encode("utf-8")
    total = len(encoded)
    if total <= limit:
        return text
    prefix = encoded[:limit].decode("utf-8", errors="ignore")
    return f"{prefix}\n[... truncated, {total} bytes total]"


def non_review_report(pr_id: str, missing: list[str], stdout_text: str) -> str:
    """Build the multi-line stderr diagnosis for output rejected as a non-review."""
    total = len(stdout_text.encode("utf-8"))
    excerpt = rejection_excerpt(stdout_text)
    return (
        f"{NON_REVIEW_MARKER}: {pr_id}\n"
        f"missing sections: {', '.join(missing)}\n"
        f"no ledger row and no cache entry were written; this PR is retried on the next run\n"
        f"--- rejected output excerpt ({total} bytes total) ---\n"
        f"{excerpt}\n"
        f"--- end excerpt ---"
    )


def _normalize_body(lines: list[str]) -> str:
    """Strip bullet marker and join continuation lines into one whitespace-collapsed string."""
    body = lines[0]
    if body.startswith(("*", "-")):
        body = body[1:].lstrip()
    body = " ".join([body] + lines[1:])
    body = re.sub(r"\s+", " ", body).strip()
    return body


def harvest(report_text: str, known_rule_ids: set) -> list:
    """Normalize a /coding:pr-review Step 5 report into a list of findings.

    Returns a list of dicts, each with keys: path, line, rule_id, body.
    """
    findings: list = []
    current_section: str | None = None
    current_finding_lines: list[str] = []

    def flush_finding():
        nonlocal current_finding_lines, current_section, findings
        if not current_finding_lines or current_section is None:
            return
        text = " ".join(current_finding_lines)
        body = _normalize_body(current_finding_lines)
        # Skip the "None." empty-section sentinel (exact equality only)
        if body.strip() in ("None.", "None"):
            current_finding_lines = []
            return
        rule_id = _extract_rule_id(text, known_rule_ids)
        path, line_num = _extract_path_line(text, known_rule_ids)
        findings.append({
            "path": path,
            "line": line_num,
            "rule_id": rule_id,
            "body": body,
        })
        current_finding_lines = []

    for line, in_fence in iter_report_lines(report_text):
        if not in_fence:
            name = heading_section_name(line)
            if name is not None or HEADING_RE.match(line):
                # Any heading — findings or not — ends whatever section was open
                flush_finding()
                current_section = name  # None for non-findings headings
                current_finding_lines = []
                continue

            if THEMATIC_BREAK_RE.match(line):
                flush_finding()
                current_section = None
                current_finding_lines = []
                continue

        if current_section is None:
            continue

        stripped = line.strip()
        if stripped and BULLET_RE.match(stripped):
            flush_finding()
            current_finding_lines = [BULLET_RE.match(stripped).group(2)]
        elif stripped and current_finding_lines:
            current_finding_lines.append(stripped)

    flush_finding()
    return findings


# ----------------------------------------------------------------------
# Result row assembly
# ----------------------------------------------------------------------
def build_row(*, checkout: PrCheckout, cfg_hash: str, rc_hash: str,
               model: str, effort: str, mode: str, prs_version: str,
               review_command: str, started_at: str,
               duration_seconds: float, findings: list,
               raw_output_ref: str) -> dict:
    """Build a result row from a completed review."""
    return {
        "config_hash": cfg_hash,
        "rules_commands_hash": rc_hash,
        "model": model,
        "effort": effort,
        "mode": mode,
        "prs_version": prs_version,
        "pr_id": checkout.pr_id,
        "base_sha": checkout.base_sha,
        "head_sha": checkout.head_sha,
        "diff_range": checkout.diff_range,
        "changed_files": checkout.changed_files,
        "parent_count": checkout.parent_count,
        "notes": checkout.notes,
        "review_command": review_command,
        "started_at": started_at,
        "duration_seconds": round(duration_seconds, 3),
        "findings": findings,
        "raw_output_ref": raw_output_ref,
        "runner_version": RUNNER_VERSION,
    }


# ----------------------------------------------------------------------
# CLI surface
# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark runner for /coding:pr-review",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--coding-repo",
        type=pathlib.Path,
        default=REPO_ROOT,
        help="Path to the coding plugin repository (default: repo root)",
    )
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=BENCH_DIR / "prs.json",
        help="Path to the PR manifest JSON (default: bench/prs.json)",
    )
    parser.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=BENCH_DIR / "results",
        help="Directory for result ledger (default: bench/results)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model to pass to /coding:pr-review (mandatory, part of config identity)",
    )
    parser.add_argument(
        "--effort",
        type=str,
        default=None,
        help="Effort level (mandatory, part of config identity)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=VALID_MODES,
        default=None,
        help="/coding:pr-review mode (mandatory, part of config identity)",
    )
    parser.add_argument(
        "--golden",
        type=pathlib.Path,
        default=None,
        help="[RESERVED — not implemented; scoring is future work]",
    )
    parser.add_argument(
        "--print-config-hash",
        action="store_true",
        default=False,
        help="Print rules+commands content hash and exit",
    )
    return parser


# ----------------------------------------------------------------------
# Core runner logic
# ----------------------------------------------------------------------
def run_bench(*, coding_repo: pathlib.Path, manifest_path: pathlib.Path,
              results_dir: pathlib.Path, cache_root: pathlib.Path,
              model: str, effort: str, mode: str,
              config_dir: pathlib.Path) -> int:
    """Keyword-only runner: load manifest, verify plugin, process each PR.

    Returns 0 only when every PR produced 'ok' or 'cache hit'.
    """
    manifest = load_manifest(manifest_path)

    rc_hash = content_hash(coding_repo)

    # Abort before any review if the isolated config would load a different plugin
    resolution = check_plugin_resolution(
        coding_repo, config_dir, rc_hash, repos_root(cache_root)
    )
    print(resolution_line(resolution))

    cfg_hash = config_hash(rc_hash, model, effort, mode, manifest["version"])

    results_dir.mkdir(parents=True, exist_ok=True)
    known_rule_ids = load_rule_ids(coding_repo)

    print(
        f"config {cfg_hash[:16]} rules+commands {rc_hash[:16]} "
        f"model={model} effort={effort} mode={mode} prs={manifest['version']}"
    )

    with BenchLock(results_dir):
        outcomes: list[tuple[str, str]] = []
        for entry in manifest["prs"]:
            pr_id = entry["id"]
            try:
                outcome, detail = process_pr(
                    entry=entry,
                    coding_repo=coding_repo,
                    results_dir=results_dir,
                    cache_root=cache_root,
                    model=model,
                    effort=effort,
                    mode=mode,
                    config_dir=config_dir,
                    cfg_hash=cfg_hash,
                    rc_hash=rc_hash,
                    prs_version=manifest["version"],
                    known_rule_ids=known_rule_ids,
                )
            except subprocess.TimeoutExpired as err:
                outcome, detail = "failed", "timeout"
            except OSError as err:
                outcome, detail = "failed", str(err)
            except BenchError as err:
                outcome, detail = "failed", str(err)
            outcomes.append((pr_id, f"{outcome}: {detail}"))

        n_ok = sum(1 for _, d in outcomes if d.startswith("ok:"))
        n_cached = sum(1 for _, d in outcomes if d.startswith("cache hit:"))
        n_failed = sum(1 for _, d in outcomes if d.startswith("failed:"))

        for pr_id, outcome in outcomes:
            print(f"{pr_id}: {outcome}")
        print(f"summary: {n_ok} ok, {n_cached} cache hit, {n_failed} failed")

        return 0 if n_failed == 0 else 1


def process_pr(*, entry: dict, coding_repo: pathlib.Path,
               results_dir: pathlib.Path, cache_root: pathlib.Path,
               model: str, effort: str, mode: str,
               config_dir: pathlib.Path, cfg_hash: str,
               rc_hash: str, prs_version: str,
               known_rule_ids: set) -> tuple[str, str]:
    """Process a single PR: cache check, resolve, review, harvest, ledger."""
    pr_id = entry["id"]

    # 1. Cache check — before any git work
    row_path = cache_row_path(cache_root, cfg_hash, pr_id)
    if row_path.exists():
        try:
            row = json.loads(row_path.read_text(encoding="utf-8"))
            n_findings = len(row.get("findings", []))
            return ("cache hit", f"cached ({row_path.name}): {n_findings} findings")
        except (json.JSONDecodeError, OSError):
            pass  # treat corrupt cache as miss

    # 2. Resolve PR
    checkout = resolve_pr(cache_root, entry)

    # 3. Build argv and invoke review
    argv = build_review_argv(
        model=model,
        effort=effort,
        mode=mode,
        base_branch=checkout.base_branch,
    )
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t0 = time.monotonic()

    try:
        proc = invoke_review(
            argv=argv,
            worktree=checkout.worktree,
            cache_root=cache_root,
            config_dir=config_dir,
        )
    except subprocess.TimeoutExpired as err:
        # Write failure log
        failures_root(cache_root).mkdir(parents=True, exist_ok=True)
        failure_log = failure_log_path(cache_root, cfg_hash, pr_id)
        stderr_bytes = err.stderr or b""
        if isinstance(stderr_bytes, str):
            stderr_bytes = stderr_bytes.encode("utf-8")
        failure_log.write_bytes(stderr_bytes)
        raise

    if proc.returncode != 0:
        failures_root(cache_root).mkdir(parents=True, exist_ok=True)
        failure_log = failure_log_path(cache_root, cfg_hash, pr_id)
        failure_log.write_bytes(proc.stderr.encode("utf-8") if proc.stderr else b"")
        raise BenchError(f"{pr_id}: review invocation failed: exit {proc.returncode}")

    # 4. Sanity gate — reject non-review output before anything is written
    missing = missing_sections(proc.stdout)
    if missing:
        print(non_review_report(pr_id, missing, proc.stdout), file=sys.stderr)
        raise BenchError(
            f"{NON_REVIEW_MARKER}: {pr_id}: missing sections: {', '.join(missing)}"
        )

    duration_seconds = time.monotonic() - t0

    # 5. Write raw stdout verbatim before any parsing
    reviews_root(cache_root).mkdir(parents=True, exist_ok=True)
    raw_path = cache_raw_path(cache_root, cfg_hash, pr_id)
    atomic_write_bytes(raw_path, proc.stdout.encode("utf-8"))

    # 6. Harvest findings
    findings = harvest(proc.stdout, known_rule_ids)

    # 7. Build row and append to ledger
    review_command = shlex.join(argv)
    # raw_output_ref: relative to REPO_ROOT if under it, else absolute
    try:
        raw_output_ref = str(raw_path.relative_to(REPO_ROOT))
    except ValueError:
        raw_output_ref = str(raw_path)

    row = build_row(
        checkout=checkout,
        cfg_hash=cfg_hash,
        rc_hash=rc_hash,
        model=model,
        effort=effort,
        mode=mode,
        prs_version=prs_version,
        review_command=review_command,
        started_at=started_at,
        duration_seconds=duration_seconds,
        findings=findings,
        raw_output_ref=raw_output_ref,
    )
    append_row(results_dir, row)

    # 8. Write cache marker
    atomic_write_bytes(row_path, json.dumps(row, sort_keys=True).encode("utf-8"))

    return ("ok", f"{len(findings)} findings in {duration_seconds:.3f}s")


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------
def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.golden is not None:
            print(
                "--golden is reserved but scoring is not implemented in this runner. "
                "Precision/recall and golden-set matching are future work in a separate spec; "
                "the runner stops at normalized findings.  Re-run without --golden.",
                file=sys.stderr,
            )
            return 2

        if args.print_config_hash:
            print(content_hash(args.coding_repo.resolve()))
            return 0

        missing: list[str] = []
        if args.model is None:
            missing.append("--model")
        if args.effort is None:
            missing.append("--effort")
        if args.mode is None:
            missing.append("--mode")
        if missing:
            print(
                f"missing required argument(s): {', '.join(missing)}. "
                f"These are part of the configuration identity recorded in every result row "
                f"and have no safe default.",
                file=sys.stderr,
            )
            return 2

        return run_bench(
            coding_repo=args.coding_repo.resolve(),
            manifest_path=args.manifest,
            results_dir=args.out_dir,
            cache_root=BENCH_DIR / ".cache",
            model=args.model,
            effort=args.effort,
            mode=args.mode,
            config_dir=verify_config_dir(),
        )

    except BenchError as err:
        print(str(err), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
