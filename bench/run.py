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
ORDERED_ITEM_RE = re.compile(r"^\s{0,3}\d+\.\s+(.+)$")
BOLD_RUN_START_RE = re.compile(r"^\s*\*\*")
# Attribution extraction patterns
RULE_TAG_RE = re.compile(r"\*\(rule:\s*`([^`]+)`\)")
HEAD_RULE_TAG_RE = re.compile(r"^`([^`]+)`")
LEADING_BOLD_RE = re.compile(r"^\*\*(.+?)\*\*")
# A path:line citation.  The final segment need NOT carry a dot extension:
# `Dockerfile:8`, `Makefile:127`, `Jenkinsfile:4` and `LICENSE:1` are real
# citations, and requiring a dot silently dropped every one of them.  Measured
# on the 2026-08-09 curated-1 pass: `backup#15` produced four correctly-formed
# findings, all on Dockerfile/Makefile, and lost ALL FOUR — the row scored 0
# findings and read as a clean PR.
#
# At least one letter is required somewhere in the path, which is what keeps
# `at 12:30` from parsing as path `12` line `30`.  Prose (`see step 3:`) and
# versions (`v1.2.3:`) do not match because the colon must be followed by
# digits and preceded by a path-shaped token with no spaces.
PATH_LINE_RE = re.compile(
    r"((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]*[A-Za-z][A-Za-z0-9_.-]*):(\d+)"
)
BACKTICK_TOKEN_RE = re.compile(r"`([^`\s]+)`")
LINE_MENTION_RE = re.compile(r"(?i)\blines?\s*~?\s*(\d+)")
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
UNATTRIBUTABLE_MARKER = "UNATTRIBUTABLE FINDING"
REJECTION_EXCERPT_BYTES = 2000

# Failure artifact constants (frozen literals — tests grep for them and the README quotes them)
FAILURE_ARTIFACT_SUFFIX = ".failure.txt"
FAILURE_STDOUT_LABEL = "--- subprocess stdout ---"
FAILURE_STDERR_LABEL = "--- subprocess stderr ---"
FAILURE_EMPTY_STREAM_MARKER = "(empty)"

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
# Scoring — frozen marker literals (spec 006 Constraints; not configurable)
# ----------------------------------------------------------------------
GOLDEN_NOT_FOUND_MARKER = "GOLDEN SET NOT FOUND"
INVALID_GOLDEN_MARKER = "INVALID GOLDEN SET"
GOLDEN_VERSION_MISMATCH_MARKER = "GOLDEN VERSION MISMATCH"
PRS_VERSION_SKIP_MARKER = "PRS VERSION SKIP"
EMPTY_LEDGER_MARKER = "EMPTY LEDGER"
CORRUPT_LEDGER_MARKER = "CORRUPT LEDGER"
INVALID_CONFIG_HASH_MARKER = "INVALID CONFIG HASH"

STATE_ACCEPTED = "accepted"
STATE_REJECTED = "rejected"
STATE_UNREVIEWED = "unreviewed"
GOLDEN_STATES = (STATE_ACCEPTED, STATE_REJECTED, STATE_UNREVIEWED)
REQUIRED_GOLDEN_KEYS = ("entries", "match_rule", "states")
RATIO_NA = "n/a"

# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------
class BenchError(Exception):
    """Every abort that maps to exit code 2 (manifest, preflight, lock)."""
    pass


# ----------------------------------------------------------------------
# Golden-set and ledger loaders — spec 006 prompt 4
# ----------------------------------------------------------------------
def load_golden(path: pathlib.Path) -> dict:
    """Read and validate a golden set.  Raises BenchError with a frozen literal."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchError(f"{GOLDEN_NOT_FOUND_MARKER}: {path}") from exc

    if not isinstance(data, dict):
        raise BenchError(
            f"{INVALID_GOLDEN_MARKER}: not a JSON object at {path}"
        )

    missing = [k for k in REQUIRED_GOLDEN_KEYS if k not in data]
    if missing:
        raise BenchError(
            f"{INVALID_GOLDEN_MARKER}: missing {missing} in {path}"
        )

    if "prs_version" not in data or not isinstance(data.get("prs_version"), str):
        raise BenchError(
            f"{INVALID_GOLDEN_MARKER}: missing or non-string 'prs_version' in {path}"
        )

    if not isinstance(data.get("entries"), list):
        raise BenchError(
            f"{INVALID_GOLDEN_MARKER}: 'entries' is not a list in {path}"
        )

    for i, entry in enumerate(data["entries"], 1):
        if not isinstance(entry, dict):
            raise BenchError(
                f"{INVALID_GOLDEN_MARKER}: entry {i} is not an object in {path}"
            )
        for field in ("pr_id", "path", "signature", "state"):
            if field not in entry:
                raise BenchError(
                    f"{INVALID_GOLDEN_MARKER}: entry {i} missing '{field}' in {path}"
                )

    return data


def load_ledger(path: pathlib.Path) -> list:
    """Read a JSONL ledger.  Raises BenchError with a frozen literal."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BenchError(f"{EMPTY_LEDGER_MARKER}: {path}") from exc

    if not text.strip():
        raise BenchError(f"{EMPTY_LEDGER_MARKER}: {path}")

    rows: list = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BenchError(
                f"{CORRUPT_LEDGER_MARKER}: {path}:{lineno}: {exc}"
            ) from exc
        if not isinstance(obj, dict):
            raise BenchError(
                f"{CORRUPT_LEDGER_MARKER}: {path}:{lineno}: not a JSON object"
            )
        for field in ("config_hash", "pr_id", "prs_version", "findings"):
            if field not in obj:
                raise BenchError(
                    f"{CORRUPT_LEDGER_MARKER}: {path}:{lineno}: missing '{field}'"
                )
        rows.append(obj)

    if not rows:
        raise BenchError(f"{EMPTY_LEDGER_MARKER}: {path}")

    return rows


def partition_by_prs_version(
    rows: list, golden_prs_version: str
) -> tuple[list, list]:
    """Return (kept, skipped): rows whose prs_version equals the golden set's, and the rest."""
    kept: list = []
    skipped: list = []
    for row in rows:
        if row["prs_version"] == golden_prs_version:
            kept.append(row)
        else:
            skipped.append(row)
            print(
                f"PRS VERSION SKIP: config {row['config_hash'][:16]}… "
                f"row prs_version {row['prs_version']!r} != "
                f"golden prs_version {golden_prs_version!r} "
                f"(pr {row['pr_id']})",
                file=sys.stderr,
            )
    return kept, skipped


def score_ledger(
    *,
    rows: list,
    golden: dict,
    reports_dir: pathlib.Path,
    coding_repo: pathlib.Path,
    only_config_hash: str | None = None,
) -> int:
    """Score every configuration in rows and write one page each.  Returns an exit code."""
    golden_prs_version = golden["prs_version"]
    kept, skipped = partition_by_prs_version(rows, golden_prs_version)

    by_config: dict[str, list] = {}
    for row in kept:
        cfg = row["config_hash"]
        if cfg not in by_config:
            by_config[cfg] = []
        by_config[cfg].append(row)

    coding_version = coding_plugin_version(coding_repo)
    exit_code = 0

    for cfg_hash, cfg_rows in by_config.items():
        if only_config_hash is not None and cfg_hash != only_config_hash:
            continue
        # skipped rows with this config_hash (per-row filter — some configs mix versions)
        skipped_count = sum(
            1 for r in skipped
            if r["config_hash"] == cfg_hash
        )
        try:
            config_score = score_config(
                rows=cfg_rows, golden=golden, rows_skipped=skipped_count
            )
        except BenchError as err:
            print(str(err), file=sys.stderr)
            exit_code = 1
            continue

        try:
            written = write_report(
                reports_dir=reports_dir,
                config_score=config_score,
                golden=golden,
                coding_version=coding_version,
            )
            print(f"wrote {written}")
        except BenchError as err:
            print(str(err), file=sys.stderr)
            exit_code = 1
            continue

    return exit_code


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


AMBIENT_MEMORY_PATH = pathlib.Path.home() / ".claude" / "CLAUDE.md"


def ambient_memory_hash(path: pathlib.Path = None) -> str:
    """Digest of `$HOME/.claude/CLAUDE.md` if present, else "none".

    DEFENSIVE, not corrective.  No leak has been demonstrated.  This component
    was added on the belief that ambient operator memory steers the reviewer,
    and that belief was **disproven the same day** — see the retraction below.
    It is kept because operator memory is a plausible influence that costs one
    file read to pin, and an unpinned influence is the failure mode this bench
    exists to avoid.  The cost of keeping it is a spurious cache invalidation
    whenever the operator edits their own CLAUDE.md.

    Retraction, recorded so the wrong claim is not reconstructed from the code:
    an opus/xhigh/full review of `quant#109` ended with a state-closer panel
    (`📌`, `👤 You:`, `⏰ Next:`) resembling the operator's personal convention.
    That was taken as proof of a memory leak.  It is not.  A review at the same
    configuration with **no CLAUDE.md reachable in either HOME or
    CLAUDE_CONFIG_DIR produced the panel anyway**, and the remaining candidates
    were each eliminated: the reviewed repo's own CLAUDE.md (0 marker matches),
    `commands/pr-review.md` (0), and this module's `build_review_argv` (no
    system prompt, no --add-dir).  The reviewing model generates that shape by
    itself at high effort.

    An artifact resembling a known convention is not evidence of its provenance.

    Still true and worth keeping: credentials resolve from CLAUDE_CONFIG_DIR
    when it is set and from `$HOME/.claude` otherwise, and on macOS `~/.claude`
    holds no credentials file at all (Keychain), which is why a naive HOME
    redirect returns `Not logged in`.  Isolation IS achievable with a file-based
    token; it simply is not needed.
    """
    p = AMBIENT_MEMORY_PATH if path is None else path
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return "none"


def config_hash(rules_commands_hash: str, model: str, effort: str,
                mode: str, prs_version: str, ambient_hash: str = None) -> str:
    """SHA-256 over the configuration-identity components.

    Mode is a first-class component: changing only mode must produce a different digest.
    Ambient operator memory is a component for the reason given in
    ambient_memory_hash — it demonstrably steers the reviewer, so leaving it out
    made the digest a promise the runner could not keep.
    """
    amb = ambient_memory_hash() if ambient_hash is None else ambient_hash
    payload = "\0".join([rules_commands_hash, model, effort, mode, prs_version, amb])
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


def failure_artifact_path(cache_root: pathlib.Path, cfg_hash: str,
                          pr_id: str) -> pathlib.Path:
    """Path of the both-stream diagnostic for one failed (PR, configuration) pair."""
    return failures_root(cache_root) / f"{cache_key(cfg_hash, pr_id)}{FAILURE_ARTIFACT_SUFFIX}"


def stream_text(value) -> str:
    """Return a captured subprocess stream as text, whatever shape it arrived in.

    A stream is str (CompletedProcess under text=True), bytes (TimeoutExpired,
    which ignores text mode) or None (never captured).  bytes are decoded as UTF-8
    with errors="replace" so a truncated multi-byte sequence from a killed process
    still produces a readable artifact instead of raising.  None becomes "".
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def failure_artifact_text(*, pr_id: str, reason: str, stdout, stderr) -> str:
    """Render both captured streams into one labelled diagnostic document.

    Layout, in this order: a first line naming the PR and the reason it failed,
    then FAILURE_STDOUT_LABEL followed by the stdout text, then
    FAILURE_STDERR_LABEL followed by the stderr text.  A stream that is empty or
    whitespace-only is rendered as FAILURE_EMPTY_STREAM_MARKER under its own label
    rather than omitted — an omitted section is indistinguishable from a section
    the writer forgot, which is the ambiguity that made the observed misdiagnosis
    possible.  Neither stream is truncated: the bounded excerpt belongs to the
    v0.35.2 gate's stderr report, and the artifact is the unbounded copy.
    """
    lines = [f"failure: {pr_id} — {reason}"]

    stdout_text = stream_text(stdout)
    lines.append(FAILURE_STDOUT_LABEL)
    if stdout_text.strip():
        lines.append(stdout_text)
    else:
        lines.append(FAILURE_EMPTY_STREAM_MARKER)

    stderr_text = stream_text(stderr)
    lines.append(FAILURE_STDERR_LABEL)
    if stderr_text.strip():
        lines.append(stderr_text)
    else:
        lines.append(FAILURE_EMPTY_STREAM_MARKER)

    return "\n".join(lines) + "\n"


def write_failure_artifact(cache_root: pathlib.Path, cfg_hash: str, pr_id: str,
                           *, reason: str, stdout, stderr) -> pathlib.Path:
    """Write the both-stream diagnostic for a failed review and return its path.

    Creates failures_root(cache_root) when absent and writes through
    atomic_write_bytes.  Writes nothing under bench/.cache/reviews/, appends no
    ledger row, and never makes a failed PR look cached on the next run — the
    artifact is a diagnostic, not a cache entry.
    """
    failures_root(cache_root).mkdir(parents=True, exist_ok=True)
    path = failure_artifact_path(cache_root, cfg_hash, pr_id)
    text = failure_artifact_text(pr_id=pr_id, reason=reason, stdout=stdout, stderr=stderr)
    atomic_write_bytes(path, text.encode("utf-8"))
    return path


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


def remove_worktree(cache_root: pathlib.Path, repo_dir: pathlib.Path,
                    wt: pathlib.Path, head_branch: str) -> None:
    """Delete a prepared working copy and the branch that anchored it.

    Removes the directory outright, not just the tracked files: a review runs the
    reviewed repo's own tooling inside the checkout, so the tree routinely picks up
    .venv / node_modules / build output that git does not know about and that dwarfs
    the git objects (a five-PR manifest reached 941MB this way, against ~1MB of packs
    per repo).  Idempotent and best-effort — every step passes check=False so calling
    it on an already-removed worktree is a no-op.

    The git objects under repo_dir are deliberately left alone: they are what makes
    ensure_refs' offline short-circuit work, and they are small.
    """
    git(["worktree", "remove", "--force", str(wt)],
        repo_dir=repo_dir, cache_root=cache_root, check=False)
    if wt.exists():
        assert_under(wt, repos_root(cache_root))
        shutil.rmtree(wt, ignore_errors=True)
    git(["branch", "-D", head_branch],
        repo_dir=repo_dir, cache_root=cache_root, check=False)
    git(["worktree", "prune"], repo_dir=repo_dir, cache_root=cache_root, check=False)


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
    remove_worktree(cache_root, repo_dir, wt, head_branch)

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
        # stream-json is the ONLY format that yields the whole transcript.
        # Plain --print and --output-format json both return the reviewer's
        # FINAL message only, so a review followed by any further message —
        # an addendum after running precommit, a delta after a late sub-agent
        # — loses its body and reads as "not a review".  Verified directly:
        # a prompt emitting FIRST-MESSAGE, a tool call, then SECOND-MESSAGE
        # returns only SECOND-MESSAGE under both, and both under stream-json.
        # --verbose is required by the CLI when pairing stream-json with --print.
        "--output-format", "stream-json",
        "--verbose",
        "--model", model,
        "--effort", effort,
        "--permission-mode", "bypassPermissions",
        f"/coding:pr-review {base_branch} {mode}",
    ]


def transcript_text(stdout: str) -> str:
    """Concatenate every assistant text block from a stream-json transcript.

    Returns the joined text in emission order.  Lines that are not JSON, and
    events that are not assistant messages, are skipped — the stream carries
    system/user/result events too, and a partial line can appear if the
    process was killed mid-write.

    Falls back to returning `stdout` unchanged when it parses as no transcript
    at all.  That keeps a stubbed binary (every test fakes `claude`) and any
    older cached raw output working: plain text in, same text out.
    """
    chunks: list[str] = []
    saw_event = False

    for line in stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        saw_event = True
        if event.get("type") != "assistant":
            continue
        content = (event.get("message") or {}).get("content") or []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text") or ""
                if text.strip():
                    chunks.append(text)

    if not saw_event:
        return stdout
    return "\n\n".join(chunks)


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


def _path_line_in(text: str, known_rule_ids: set):
    """First path:line in `text` that is not a known rule id, else None.

    The rule-id guard has to apply at EVERY call site, not just the whole-item
    scan.  Rule ids are slash-separated and dotless (`test-pyramid/push-down-
    when-unsure`), so while the path pattern demanded a dot they could never
    match it and the leading-bold-ref path got away without the check.  Widening
    the pattern to accept `Dockerfile:8` made them match, and a rule id cited
    with a line number would have been recorded as a file path.
    """
    for m in PATH_LINE_RE.finditer(text):
        if m.group(1) not in known_rule_ids:
            return m.group(1), int(m.group(2))
    return None


def _extract_path_line(text: str, known_rule_ids: set) -> tuple[str | None, int | None]:
    """Extract the first path:line reference from text, skipping known rule IDs.

    A path:line is a path-shaped token followed by :NN.  The token may be
    extensionless (`Dockerfile:8`, `Makefile:127`) — requiring a dot used to
    drop those findings entirely.  A token that is a known rule ID is never
    treated as a path.
    """
    # Find all potential path:line matches
    for m in PATH_LINE_RE.finditer(text):
        candidate = m.group(1)
        if candidate not in known_rule_ids:
            return candidate, int(m.group(2))
    return None, None


def extract_attribution(body: str, known_rule_ids: set) -> tuple[str | None, int | None, str | None]:
    """Return (path, line, rule_id) for one finding item, read from the item's own markers.

    rule_id, in priority order:
      1. the item's own inline `*(rule: `<id>`)*` marker — recorded as the literal
         string the reviewer wrote, whether or not it appears in rules/index.json;
      2. otherwise a backticked token at the very head of the item that is a member
         of known_rule_ids (the shape the review template emits when it tags a
         finding by leading its body with the rule id);
      3. otherwise None.
    An id named anywhere else in the item, or anywhere outside it, is never used.

    path/line, in priority order:
      1. the bold run at the head of the item, when it names a path;
      2. otherwise the first path:line reference anywhere in the item that is not
         a known rule id;
      3. otherwise (None, None).
    When the leading bold run supplies a path, line is taken from that bold run and
    from nowhere else — a line number appearing only in the item's trailing prose is
    not used.  No path is ever inferred by searching the repository and no line is
    ever guessed from surrounding text.
    """
    # rule_id — source 1: inline *(rule: `id`)* tag, verbatim, no index check
    m = RULE_TAG_RE.search(body)
    if m:
        rule_id = m.group(1)
        # path/line from bold run at head of item
        bold_m = LEADING_BOLD_RE.match(body)
        if bold_m:
            ref = bold_m.group(1)
            path_m = PATH_LINE_RE.search(ref)
            if path_m:
                return path_m.group(1), int(path_m.group(2)), rule_id
            # try backtick token with dot as path
            tok_m = BACKTICK_TOKEN_RE.search(ref)
            if tok_m:
                token = tok_m.group(1)
                if "." in token:
                    line_m = LINE_MENTION_RE.search(ref)
                    line = int(line_m.group(1)) if line_m else None
                    return token, line, rule_id
        # fall through to step 2 for path/line
    else:
        rule_id = None
        # rule_id — source 2: head-anchored backtick token, index-gated
        head_m = HEAD_RULE_TAG_RE.match(body)
        if head_m:
            token = head_m.group(1)
            if token in known_rule_ids:
                rule_id = token

    # path/line — source 1: bold run at head of item
    bold_m = LEADING_BOLD_RE.match(body)
    if bold_m:
        ref = bold_m.group(1)
        path_m = _path_line_in(ref, known_rule_ids)
        if path_m:
            return path_m[0], path_m[1], rule_id
        tok_m = BACKTICK_TOKEN_RE.search(ref)
        if tok_m:
            token = tok_m.group(1)
            if "." in token:
                line_m = LINE_MENTION_RE.search(ref)
                line = int(line_m.group(1)) if line_m else None
                return token, line, rule_id

    # path/line — source 2: whole-item scan (existing _extract_path_line logic)
    path, line = _extract_path_line(body, known_rule_ids)
    return path, line, rule_id


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


def unattributable_report(pr_id: str, items: list, stdout_text: str) -> str:
    """Build the multi-line stderr diagnosis for a review carrying unkeyable items.

    Names the PR, then each offending item's severity section and its text
    verbatim.  The item block is passed through the same bounded excerpt the
    NOT A REVIEW gate uses, so a runaway subprocess cannot flood the terminal.
    """
    total = len(stdout_text.encode("utf-8"))
    item_blocks = []
    for item in items:
        item_text = f"[{item['section']}] {item['body']}"
        item_blocks.append(rejection_excerpt(item_text))

    return (
        f"{UNATTRIBUTABLE_MARKER}: {pr_id}\n"
        f"{len(items)} unattributable item(s)\n"
        + "\n\n".join(item_blocks) + "\n"
        f"the row was KEPT and scored; these items were dropped from it and "
        f"counted in unattributable_count\n"
        f"--- subprocess stdout ({total} bytes total) ---\n"
        f"{rejection_excerpt(stdout_text)}\n"
        f"--- end excerpt ---"
    )


def list_item_body(stripped_line: str) -> str | None:
    """Return the item text when stripped_line opens a list item, else None.

    Both list styles the reviewer uses open a finding: an unordered item
    (`-` or `*` followed by whitespace) and an ordered item (a run of digits
    followed by `.` and whitespace).  The marker is removed; nothing else about
    the text is changed, so a leading bold run survives intact.
    """
    m = BULLET_RE.match(stripped_line)
    if m:
        return m.group(2)
    m = ORDERED_ITEM_RE.match(stripped_line)
    if m:
        return m.group(1)
    return None


def _normalize_body(lines: list[str]) -> str:
    """Join an item's lines into one whitespace-collapsed string.

    The list marker was already removed by list_item_body; nothing else is
    stripped, so the item's leading bold run is preserved verbatim.
    """
    body = " ".join(lines)
    return re.sub(r"\s+", " ", body).strip()


@dataclasses.dataclass
class HarvestResult:
    """The two-part outcome of harvesting one review report.

    findings       — items inside a severity section that carry a path or rule_id.
    unattributable — items inside a severity section that carry neither.  Only
                     items inside a severity section are ever classified; content
                     outside one (positive notes, traceability table, etc.) opens
                     no item at all and appears in neither component.
    """
    findings: list
    unattributable: list


def harvest(report_text: str, known_rule_ids: set) -> HarvestResult:
    """Normalize a /coding:pr-review Step 5 report into a HarvestResult.

    Returns a HarvestResult with two lists: findings (attributed items) and
    unattributable (items with no path and no rule_id).  Each finding dict
    has keys: path, line, rule_id, body.
    """
    findings: list = []
    unattributable: list = []
    current_section: str | None = None
    current_finding_lines: list[str] = []

    def flush_finding():
        nonlocal current_finding_lines, current_section, findings, unattributable
        if not current_finding_lines or current_section is None:
            return
        body = _normalize_body(current_finding_lines)
        # Skip the "None." empty-section sentinel (exact equality only)
        if body.strip() in ("None.", "None"):
            current_finding_lines = []
            return
        path, line_num, rule_id = extract_attribution(body, known_rule_ids)
        if path is None and rule_id is None:
            unattributable.append({
                "section": current_section,
                "body": body,
            })
        else:
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

            if BOLD_RUN_START_RE.match(line):
                flush_finding()
                current_section = None
                current_finding_lines = []
                continue

        if current_section is None:
            continue

        stripped = line.strip()
        item = list_item_body(stripped) if (stripped and not in_fence) else None
        if item is not None:
            flush_finding()
            current_finding_lines = [item]
        elif stripped and current_finding_lines:
            current_finding_lines.append(stripped)

    flush_finding()
    return HarvestResult(findings=findings, unattributable=unattributable)


# ----------------------------------------------------------------------
# Result row assembly
# ----------------------------------------------------------------------
def build_row(*, checkout: PrCheckout, cfg_hash: str, rc_hash: str,
               model: str, effort: str, mode: str, prs_version: str,
               review_command: str, started_at: str,
               duration_seconds: float, findings: list,
               raw_output_ref: str,
               unattributable_count: int = 0,
               missing_sections_names: list = None) -> dict:
    """Build a result row from a completed review.

    unattributable_count and missing_sections record what the gates dropped or
    tolerated.  Both used to be fatal — the PR produced no row at all — which
    cost a 20-PR pass 7 of 20 rows on 2026-08-09.  They are kept as row fields so
    the loss is measurable per PR instead of binary, and so a row built from a
    partially-rejected review is visibly lower-confidence rather than silently
    equal to a clean one.
    """
    return {
        "config_hash": cfg_hash,
        "unattributable_count": unattributable_count,
        "missing_sections": list(missing_sections_names or []),
        "rules_commands_hash": rc_hash,
        # Recorded on its own line, not just folded into config_hash: a reader
        # comparing two rows must be able to see WHICH input differed, and
        # ambient operator memory is the one input that changes without any
        # commit to this repo.
        "ambient_memory_hash": ambient_memory_hash(),
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
        help="Golden set JSON; scores the run (or the ledger, with --score) and writes report pages",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        default=False,
        help="Score an existing ledger and exit; invokes no review. Requires --golden",
    )
    parser.add_argument(
        "--reports-dir",
        type=pathlib.Path,
        default=BENCH_DIR / "reports",
        help="Directory for report pages (default: bench/reports)",
    )
    parser.add_argument(
        "--print-config-hash",
        action="store_true",
        default=False,
        help="Print rules+commands content hash and exit",
    )
    parser.add_argument(
        "--reharvest",
        action="store_true",
        default=False,
        help=(
            "Re-parse cached transcripts and rewrite each row's findings; "
            "invokes no review. Use after a harvester fix to correct an "
            "existing pass without paying for it again"
        ),
    )
    return parser


def reharvest_ledger(*, results_dir: pathlib.Path, cache_root: pathlib.Path,
                     coding_repo: pathlib.Path, out=sys.stdout) -> int:
    """Re-parse every row's cached transcript and rewrite its harvested fields.

    A harvester fix — a widened path pattern, a new attribution source — leaves
    every already-scored row wrong, and the config identity deliberately does
    NOT cover `bench/run.py`, so a re-run would serve the same stale rows from
    cache.  Re-running live costs the price of the whole pass.

    This is only possible because the stored transcript is complete: reviews are
    captured with `--output-format stream-json`, so the raw file holds every
    assistant message rather than the last one.  Before that, replaying stored
    output could not recover what was never captured.

    Rows whose transcript is missing are left untouched and reported — silently
    zeroing them would look like a reviewer that found nothing.
    """
    path = ledger_path(results_dir)
    rows = load_ledger(path)
    if not rows:
        print("reharvest: ledger is empty", file=out)
        return 0

    known_rule_ids = load_rule_ids(coding_repo)
    rewritten, unchanged, missing = 0, 0, []
    lines = []

    for row in rows:
        cfg_hash, pr_id = row.get("config_hash", ""), row.get("pr_id", "")
        raw_path = cache_raw_path(cache_root, cfg_hash, pr_id)
        if not raw_path.exists():
            missing.append(pr_id)
            lines.append(json.dumps(row, sort_keys=True))
            continue

        harvested = harvest(
            transcript_text(raw_path.read_text(encoding="utf-8")), known_rule_ids
        )
        before_n = len(row.get("findings", []))
        before_u = row.get("unattributable_count", 0)
        after_n = len(harvested.findings)
        after_u = len(harvested.unattributable)

        if (after_n, after_u) != (before_n, before_u):
            print(
                f"  {pr_id}: findings {before_n} -> {after_n}, "
                f"unattributable {before_u} -> {after_u}",
                file=out,
            )
            rewritten += 1
        else:
            unchanged += 1

        row["findings"] = harvested.findings
        row["unattributable_count"] = after_u
        lines.append(json.dumps(row, sort_keys=True))

    atomic_write_bytes(path, ("\n".join(lines) + "\n").encode("utf-8"))

    if missing:
        print(
            f"reharvest: {len(missing)} row(s) had no cached transcript and were "
            f"left as-is: {', '.join(missing)}",
            file=out,
        )
    print(
        f"reharvest: {rewritten} row(s) rewritten, {unchanged} unchanged, "
        f"{len(missing)} skipped",
        file=out,
    )
    return 0


# ----------------------------------------------------------------------
# Core runner logic
# ----------------------------------------------------------------------
def run_bench(*, coding_repo: pathlib.Path, manifest_path: pathlib.Path,
              results_dir: pathlib.Path, cache_root: pathlib.Path,
              model: str, effort: str, mode: str,
              config_dir: pathlib.Path,
              golden: dict | None = None,
              reports_dir: pathlib.Path | None = None) -> int:
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

        run_rc = 0 if n_failed == 0 else 1

        if golden is not None and reports_dir is not None:
            rows = load_ledger(ledger_path(results_dir))
            score_rc = score_ledger(
                rows=rows,
                golden=golden,
                reports_dir=reports_dir,
                coding_repo=coding_repo,
                only_config_hash=cfg_hash,
            )
            # Run failure takes precedence over a scoring pass.
            return run_rc if run_rc != 0 else score_rc

        return run_rc


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
        write_failure_artifact(cache_root, cfg_hash, pr_id,
                              reason="timeout", stdout=err.stdout, stderr=err.stderr)
        raise
    finally:
        # The working copy has served its only purpose; everything below reads
        # proc.stdout.  Release it here rather than at the start of the next run
        # for this PR, so a finished bench leaves no checkouts behind — including
        # on the timeout and non-zero-exit paths, which previously leaked one
        # tree per failed PR.  The git objects stay cached.
        remove_worktree(cache_root, checkout.repo_dir,
                        checkout.worktree, checkout.head_branch)

    if proc.returncode != 0:
        write_failure_artifact(cache_root, cfg_hash, pr_id,
                              reason=f"exit {proc.returncode}",
                              stdout=proc.stdout, stderr=proc.stderr)
        raise BenchError(f"{pr_id}: review invocation failed: exit {proc.returncode}")

    # 4. Sanity gate — reject output that is not a review at all.
    #
    #    Rejects only when EVERY severity section is absent.  This gate exists for
    #    D2, where an unknown command returned "ok: 0 findings" and read as a clean
    #    review; that case has no sections whatsoever.  Requiring all three was
    #    stricter than the purpose needs and discarded substantive reviews over
    #    heading shape — a 20-PR Opus pass on 2026-08-09 lost `discord-assistant#5`
    #    for carrying Should Fix and Nice to Have but not Must Fix.  Partial sets
    #    are kept and the absent names recorded on the row.
    # The reviewer's full text, not just its last message.  Everything below
    # this line grades `report_text`; only the cache still stores raw stdout.
    report_text = transcript_text(proc.stdout)

    missing = missing_sections(report_text)
    if len(missing) == len(REQUIRED_SECTION_NAMES):
        write_failure_artifact(
            cache_root, cfg_hash, pr_id,
            reason=f"{NON_REVIEW_MARKER}: missing sections: {', '.join(missing)}",
            stdout=proc.stdout, stderr=proc.stderr,
        )
        print(non_review_report(pr_id, missing, report_text), file=sys.stderr)
        raise BenchError(
            f"{NON_REVIEW_MARKER}: {pr_id}: missing sections: {', '.join(missing)}"
        )

    duration_seconds = time.monotonic() - t0

    # 5. Write raw stdout verbatim before any parsing
    reviews_root(cache_root).mkdir(parents=True, exist_ok=True)
    raw_path = cache_raw_path(cache_root, cfg_hash, pr_id)
    atomic_write_bytes(raw_path, proc.stdout.encode("utf-8"))

    # 6. Harvest findings
    harvested = harvest(report_text, known_rule_ids)
    findings = harvested.findings

    # 6a. Unattributable items — dropped from the row, never silently.
    #
    #     A finding that cannot be keyed does not invalidate its siblings, which
    #     can.  This used to raise and discard the whole PR: a 20-PR Opus pass on
    #     2026-08-09 lost 4 reviews that way, one of them (`tts-mcp#10`) over a
    #     SINGLE unattributable item among a full set of valid findings — a 35%
    #     loss rate that left a 20-PR fixture yielding 13 rows.
    #
    #     The count is recorded on the row rather than dropped quietly.  Silent
    #     removal would make precision improve for a reason nothing records,
    #     which is the exact defect class this bench exists to catch.  The
    #     guarantee that every *scored* finding carries a usable matching key is
    #     unchanged — this is a change of granularity, not of contract.
    unattributable_count = len(harvested.unattributable)
    if unattributable_count:
        print(unattributable_report(pr_id, harvested.unattributable, report_text),
              file=sys.stderr)

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
        unattributable_count=unattributable_count,
        missing_sections_names=missing,
    )
    append_row(results_dir, row)

    # 8. Write cache marker
    atomic_write_bytes(row_path, json.dumps(row, sort_keys=True).encode("utf-8"))

    return ("ok", f"{len(findings)} findings in {duration_seconds:.3f}s")


# ----------------------------------------------------------------------
# Scoring — pure functions (spec 006 prompt 1)
# ----------------------------------------------------------------------
def format_ratio(numerator: int, denominator: int) -> str:
    """Render a ratio as three fixed decimals, or the literal 'n/a' on a zero denominator."""
    if denominator == 0:
        return RATIO_NA
    return format(numerator / denominator, ".3f")


def finding_matches_entry(entry: dict, finding: dict) -> bool:
    """True when this finding and this golden entry describe the same issue.

    rule_id exact when BOTH sides carry a non-null one; otherwise path string
    equality plus EVERY signature keyword present case-insensitively in body.
    `line` is read from neither side.
    """
    entry_rule = entry.get("rule_id")
    finding_rule = finding.get("rule_id")
    # Case 1: both carry a non-null rule_id — exact match required
    if entry_rule is not None and entry_rule != "" and finding_rule is not None and finding_rule != "":
        return entry_rule == finding_rule
    # Case 2: path match + every signature keyword case-insensitively in body
    if entry.get("path") != finding.get("path"):
        return False
    body = (finding.get("body") or "").lower()
    for kw in entry.get("signature") or []:
        if kw.lower() not in body:
            return False
    return True


@dataclasses.dataclass(frozen=True)
class ScoreResult:
    entries_in_scope: int
    accepted_in_scope: int
    accepted_hits: int
    misses: int
    matched_rejected: int
    excluded_unreviewed: int
    findings: int
    gap_candidates: tuple
    recall: str
    precision: str


def score_findings(*, entries: list, findings: list) -> ScoreResult:
    """Score an already-scoped list of golden entries against a list of findings.

    `entries` are golden entries already restricted to the PRs under consideration.
    Each element of `findings` is a dict carrying 'pr_id', 'path', 'line', 'body'
    and 'rule_id'.  Pure: no I/O, no mutation of either argument.
    """
    matched_entry_indices: set[int] = set()
    matched_finding_indices: set[int] = set()

    for ei, entry in enumerate(entries):
        for fi, finding in enumerate(findings):
            if entry.get("pr_id") != finding.get("pr_id"):
                continue
            if finding_matches_entry(entry, finding):
                matched_entry_indices.add(ei)
                matched_finding_indices.add(fi)

    entries_in_scope = len(entries)
    accepted_in_scope = sum(1 for e in entries if e.get("state") == STATE_ACCEPTED)
    accepted_hits = sum(
        1 for i in matched_entry_indices if entries[i].get("state") == STATE_ACCEPTED
    )
    misses = accepted_in_scope - accepted_hits
    matched_rejected = sum(
        1 for i in matched_entry_indices if entries[i].get("state") == STATE_REJECTED
    )
    excluded_unreviewed = sum(
        1 for e in entries if e.get("state") == STATE_UNREVIEWED
    )
    findings_count = len(findings)
    gap_candidates = tuple(
        {"pr_id": f["pr_id"], "path": f["path"], "line": f["line"], "body": f["body"]}
        for i, f in enumerate(findings)
        if i not in matched_finding_indices
    )
    recall = format_ratio(accepted_hits, accepted_in_scope)
    precision = format_ratio(accepted_hits, accepted_hits + matched_rejected)

    return ScoreResult(
        entries_in_scope=entries_in_scope,
        accepted_in_scope=accepted_in_scope,
        accepted_hits=accepted_hits,
        misses=misses,
        matched_rejected=matched_rejected,
        excluded_unreviewed=excluded_unreviewed,
        findings=findings_count,
        gap_candidates=gap_candidates,
        recall=recall,
        precision=precision,
    )


def iter_findings(rows: list) -> list:
    """Flatten ledger rows into findings, each carrying its row's pr_id.

    Returns dicts with 'pr_id', 'path', 'line', 'body', 'rule_id' in row order,
    then finding order within a row.  The input rows are not mutated.
    """
    result = []
    for row in rows:
        pr_id = row.get("pr_id")
        for finding in row.get("findings") or []:
            result.append({
                "pr_id": pr_id,
                "path": finding.get("path"),
                "line": finding.get("line"),
                "body": finding.get("body"),
                "rule_id": finding.get("rule_id"),
            })
    return result


def entries_in_scope(golden: dict, pr_ids) -> list:
    """The golden entries whose pr_id is in pr_ids, in golden-file order."""
    pr_set = set(pr_ids)
    return [e for e in golden.get("entries") or [] if e.get("pr_id") in pr_set]


# ----------------------------------------------------------------------
# Run chunking — spec 006 prompt 2
# ----------------------------------------------------------------------
def chunk_runs(rows: list) -> list:
    """Split one configuration's ledger rows into runs by per-PR occurrence index.

    Within a config, the k-th row for a given pr_id — in ledger file order —
    belongs to run k.  Returns a list of lists, run 1 first.  Input not mutated.
    """
    from collections import Counter, defaultdict

    counter = Counter()
    runs: dict[int, list] = defaultdict(list)
    for row in rows:
        pr_id = row["pr_id"]
        counter[pr_id] += 1
        runs[counter[pr_id]].append(row)
    return [runs[k] for k in sorted(runs)]


# ----------------------------------------------------------------------
# Aggregation dataclasses — spec 006 prompt 2
# ----------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class PrBreakdown:
    pr_id: str
    entries_in_scope: int
    hits: int
    misses: int
    findings: int
    gap_candidates: int
    duration_seconds: int
    # What the gates removed before scoring. Carried onto the page so a row's
    # score can be read next to the reason it might flatter: a finding dropped
    # for lacking a matching key never reached precision, and a review missing a
    # severity section was graded on the sections it did carry.
    unattributable: int = 0
    missing_sections: tuple = ()


@dataclasses.dataclass(frozen=True)
class RunScore:
    index: int
    pr_ids: tuple
    expected_pr_count: int
    complete: bool
    span_start: str
    span_end: str
    wall_time_seconds: int
    score: ScoreResult
    per_pr: tuple


@dataclasses.dataclass(frozen=True)
class ConfigScore:
    config_hash: str
    model: str
    effort: str
    mode: str
    rules_commands_hash: str
    prs_version: str
    runner_versions: tuple
    rows_skipped: int
    runs: tuple


# ----------------------------------------------------------------------
# Per-run scoring — spec 006 prompt 2
# ----------------------------------------------------------------------
def score_run(*, rows: list, golden: dict, expected_pr_ids: frozenset, index: int) -> RunScore:
    """Score one run's rows, scoped to the PRs it actually covers."""
    pr_ids_in_run = tuple(dict.fromkeys(r["pr_id"] for r in rows))
    complete = set(pr_ids_in_run) == expected_pr_ids

    # span_start / span_end — display only
    timestamps = [r["started_at"] for r in rows if r.get("started_at")]
    span_start = min(timestamps) if timestamps else ""
    span_end = max(timestamps) if timestamps else ""

    # wall_time: round of the unrounded sum
    raw_wall = sum(r.get("duration_seconds", 0.0) or 0.0 for r in rows)
    wall_time_seconds = round(raw_wall)

    # Scope: only the PRs this run actually covers
    scoped_entries = entries_in_scope(golden, pr_ids_in_run)
    findings = iter_findings(rows)
    score = score_findings(entries=scoped_entries, findings=findings)

    # Per-PR breakdown: re-score each PR individually
    per_pr_list: list[PrBreakdown] = []
    for pr_id in pr_ids_in_run:
        pr_rows = [r for r in rows if r["pr_id"] == pr_id]
        pr_entries = entries_in_scope(golden, (pr_id,))
        pr_findings = iter_findings(pr_rows)
        pr_score = score_findings(entries=pr_entries, findings=pr_findings)
        raw_dur = sum(r.get("duration_seconds", 0.0) or 0.0 for r in pr_rows)
        # Older ledgers predate both fields; absent means "nothing was dropped",
        # which is what a run before the item-level gates actually recorded.
        dropped = sum(r.get("unattributable_count", 0) or 0 for r in pr_rows)
        absent_sections = []
        for r in pr_rows:
            for name in r.get("missing_sections") or ():
                if name not in absent_sections:
                    absent_sections.append(name)
        per_pr_list.append(PrBreakdown(
            pr_id=pr_id,
            entries_in_scope=pr_score.entries_in_scope,
            hits=pr_score.accepted_hits,
            misses=pr_score.misses,
            findings=pr_score.findings,
            gap_candidates=len(pr_score.gap_candidates),
            duration_seconds=round(raw_dur),
            unattributable=dropped,
            missing_sections=tuple(absent_sections),
        ))

    return RunScore(
        index=index,
        pr_ids=pr_ids_in_run,
        expected_pr_count=len(expected_pr_ids),
        complete=complete,
        span_start=span_start,
        span_end=span_end,
        wall_time_seconds=wall_time_seconds,
        score=score,
        per_pr=tuple(per_pr_list),
    )


def score_config(*, rows: list, golden: dict, rows_skipped: int = 0) -> ConfigScore:
    """Score every run of one configuration's ledger rows."""
    if not rows:
        raise ValueError("score_config called with empty rows")

    first = rows[0]
    config_hash = first["config_hash"]
    model = first["model"]
    effort = first["effort"]
    mode = first["mode"]
    rules_commands_hash = first["rules_commands_hash"]
    prs_version = first["prs_version"]

    expected_pr_ids = frozenset(e["pr_id"] for e in golden["entries"])

    runs = tuple(
        score_run(rows=chunk, golden=golden, expected_pr_ids=expected_pr_ids, index=i)
        for i, chunk in enumerate(chunk_runs(rows), 1)
    )

    runner_versions = tuple(sorted(
        {str(r.get("runner_version", "1")) for r in rows}
    ))

    return ConfigScore(
        config_hash=config_hash,
        model=model,
        effort=effort,
        mode=mode,
        rules_commands_hash=rules_commands_hash,
        prs_version=prs_version,
        runner_versions=runner_versions,
        rows_skipped=rows_skipped,
        runs=runs,
    )


# ----------------------------------------------------------------------
# Report rendering — spec 006 prompt 3
# ----------------------------------------------------------------------
CONFIG_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_config_hash(value: str) -> str:
    """Return value when it is 64 lowercase hex characters; raise BenchError otherwise."""
    if not isinstance(value, str) or not CONFIG_HASH_RE.fullmatch(value):
        raise BenchError(f"{INVALID_CONFIG_HASH_MARKER}: {value!r}")
    return value


def report_path(reports_dir: pathlib.Path, config_hash: str) -> pathlib.Path:
    """<reports_dir>/<64-hex config_hash>.md, with the hash validated first."""
    validated = validate_config_hash(config_hash)
    path = reports_dir / f"{validated}.md"
    assert_under(path, reports_dir.resolve())
    return path


def coding_plugin_version(coding_repo: pathlib.Path) -> str:
    """The `version` from <coding_repo>/.claude-plugin/plugin.json, or 'unavailable'."""
    try:
        plugin_path = coding_repo / ".claude-plugin" / "plugin.json"
        data = json.loads(plugin_path.read_text(encoding="utf-8"))
        return str(data["version"])
    except (OSError, json.JSONDecodeError, KeyError):
        return "unavailable"


def _precision_caveat(golden: dict) -> str:
    """Describe what precision can and cannot mean on THIS golden set.

    Counted from the entries, never asserted: the previous version hardcoded
    "carries zero rejected entries", which would have kept printing after the
    first rejected entry was adjudicated in — a false claim in the primary
    output artifact, published under a config hash.
    """
    version = golden["version"]
    n_rejected = sum(1 for e in golden["entries"] if e.get("state") == "rejected")
    if n_rejected == 0:
        return (
            f"*{version}* carries zero `rejected` entries, so precision "
            "cannot be lost by any configuration. "
            "A precision of `1.000` is a property of the golden set's adjudication "
            "state and is not yet a result."
        )
    return (
        f"*{version}* carries {n_rejected} `rejected` "
        f"{'entry' if n_rejected == 1 else 'entries'}, so precision is measurable: "
        "reporting one costs precision. With so few adjudicated, a single hit still "
        "moves the number a long way — read it as directional, not calibrated."
    )


def _coverage_caveat(config_score: "ConfigScore") -> str:
    """State the effective fixture size and what the gates removed from it.

    Every number is counted from the scored rows.  Without this line the page
    shows a recall figure whose denominator lives only in stderr, and a reader
    cannot tell a configuration that reviewed twenty PRs from one whose reviews
    were mostly rejected on shape — the two render identically.
    """
    scored_prs = sum(len(rs.pr_ids) for rs in config_score.runs)
    expected = sum(rs.expected_pr_count for rs in config_score.runs)
    dropped = sum(pr.unattributable for rs in config_score.runs for pr in rs.per_pr)
    partial = sum(
        1 for rs in config_score.runs for pr in rs.per_pr if pr.missing_sections
    )

    if not expected:
        return "*Effective fixture: no runs scored.*"

    parts = [
        f"*Effective fixture: **{scored_prs} of {expected}** PRs produced a "
        f"scored row.*"
    ]
    if scored_prs < expected:
        parts.append(
            f" The {expected - scored_prs} absent "
            f"{'row is' if expected - scored_prs == 1 else 'rows are'} not a "
            "zero-finding result — they were rejected before scoring, so they "
            "lower confidence without lowering recall."
        )
    if dropped:
        parts.append(
            f" **{dropped}** finding{'' if dropped == 1 else 's'} carried no "
            "matching key and never reached scoring."
        )
    if partial:
        parts.append(
            f" **{partial}** row{'' if partial == 1 else 's'} came from a review "
            "missing at least one severity section."
        )
    return "".join(parts)


def _recall_caveat(golden: dict) -> str:
    """Describe how much of recall is line-citation rather than issue-detection.

    Both numbers are counted from the entries.  They were hardcoded as
    "36 of the 42" and would have gone stale the moment the set changed size.
    """
    entries = golden["entries"]
    total = len(entries)
    with_line = sum(
        1 for e in entries
        if any(re.search(r":\d+", kw) for kw in e.get("signature", []))
    )
    if with_line == 0:
        return (
            "No signature embeds a line reference, so a re-report of the same issue "
            "at a different line still matches. `recall` measures issue detection."
        )
    return (
        f"{with_line} of the {total} signatures embed a line reference, so a "
        "re-report of the same issue at a different line does not match and is "
        "surfaced as a gap-triage candidate rather than a hit. "
        "On this golden set, `recall` measures whether a configuration cited the "
        "same line, not whether it found the issue."
    )


def _escape_pipe(s: str) -> str:
    """Escape a literal pipe so it cannot add a markdown table column."""
    return s.replace("|", "\\|")


def render_report(*, config_score: ConfigScore, golden: dict, coding_version: str) -> str:
    """Render one configuration's scored result as the full page text.

    No generation timestamp, no wall clock, no host name — purely a function of
    the result object and the frozen golden set.
    """
    lines: list[str] = []

    # ── Page header ──────────────────────────────────────────────────────────
    lines.append(config_score.config_hash)
    lines.append("")  # blank after h1

    # ── ## Configuration ────────────────────────────────────────────────────
    lines.append("## Configuration")
    lines.append(f"- model: {config_score.model}")
    lines.append(f"- effort: {config_score.effort}")
    lines.append(f"- mode: {config_score.mode}")
    lines.append(f"- config_hash: {config_score.config_hash}")
    lines.append(f"- rules_commands_hash: {config_score.rules_commands_hash}")
    lines.append(f"- prs_version: {config_score.prs_version}")
    lines.append(f"- coding version: {coding_version}")
    lines.append(
        f"- golden baseline coding version: {golden['baseline']['coding_version']}"
    )
    lines.append(f"- golden version: {golden['version']}")
    lines.append(
        f"- runner_version: {', '.join(config_score.runner_versions)}"
    )
    lines.append(f"- rows skipped: {config_score.rows_skipped}")
    lines.append("- cost: not recorded — the ledger carries no cost field.")
    lines.append("")
    lines.append(_precision_caveat(golden))
    lines.append("")
    lines.append(_recall_caveat(golden))
    lines.append("")

    # ── ## Runs ─────────────────────────────────────────────────────────────
    lines.append("## Runs")
    lines.append(
        "| run | span | PRs | complete | golden in scope | findings | hits | "
        "misses | matched rejected | gap candidates | recall | precision | "
        "wall time (s) |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
        "--- | --- |"
    )
    for run_score in config_score.runs:
        span = f"{run_score.span_start} … {run_score.span_end}"
        complete_word = "complete" if run_score.complete else "partial"
        r = run_score.score
        lines.append(
            f"| {run_score.index} "
            f"| {_escape_pipe(span)} "
            f"| {len(run_score.pr_ids)}/{run_score.expected_pr_count} "
            f"| {complete_word} "
            f"| {r.entries_in_scope} "
            f"| {r.findings} "
            f"| {r.accepted_hits} "
            f"| {r.misses} "
            f"| {r.matched_rejected} "
            f"| {len(r.gap_candidates)} "
            f"| {r.recall} "
            f"| {r.precision} "
            f"| {run_score.wall_time_seconds} |"
        )
    lines.append("")

    # ── ## Per-PR ───────────────────────────────────────────────────────────
    lines.append("## Per-PR")
    lines.append(
        "| run | pr_id | golden in scope | hits | misses | findings | "
        "gap candidates | dropped items | missing sections | duration (s) |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    for run_score in config_score.runs:
        for pr in run_score.per_pr:
            absent = ", ".join(pr.missing_sections) if pr.missing_sections else "—"
            lines.append(
                f"| {run_score.index} "
                f"| {_escape_pipe(pr.pr_id)} "
                f"| {pr.entries_in_scope} "
                f"| {pr.hits} "
                f"| {pr.misses} "
                f"| {pr.findings} "
                f"| {pr.gap_candidates} "
                f"| {pr.unattributable} "
                f"| {_escape_pipe(absent)} "
                f"| {pr.duration_seconds} |"
            )
    lines.append("")
    lines.append(_coverage_caveat(config_score))
    lines.append("")

    # ── ## Gap-triage candidates ─────────────────────────────────────────────
    lines.append("## Gap-triage candidates")
    lines.append(
        "These findings matched no golden entry. They are **not a precision "
        "failure** — the golden set is a bootstrap from one strong-model run, and "
        "a finding it does not describe is evidence the set is incomplete."
    )
    lines.append("")

    total_gap = sum(
        len(rs.score.gap_candidates) for rs in config_score.runs
    )
    if total_gap == 0:
        lines.append("None.")
    else:
        for run_score in config_score.runs:
            for gc in run_score.score.gap_candidates:
                line_suffix = f":{gc['line']}" if gc["line"] is not None else ""
                lines.append(
                    f"### run {run_score.index} — {gc['pr_id']} — "
                    f"{gc['path']}{line_suffix}"
                )
                lines.append("")
                lines.append(gc["body"])  # verbatim, no wrapping
                lines.append("")

    return "\n".join(lines)


def write_report(
    *,
    reports_dir: pathlib.Path,
    config_score: ConfigScore,
    golden: dict,
    coding_version: str,
) -> pathlib.Path:
    """Render and atomically write one configuration's page.  Returns the path."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = report_path(reports_dir, config_score.config_hash)
    text = render_report(
        config_score=config_score,
        golden=golden,
        coding_version=coding_version,
    )
    atomic_write_bytes(path, text.encode("utf-8"))
    return path


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------
def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.print_config_hash:
            print(content_hash(args.coding_repo.resolve()))
            return 0

        # Re-harvest mode — re-parses cached transcripts, invokes no review
        if args.reharvest:
            return reharvest_ledger(
                results_dir=args.out_dir,
                cache_root=BENCH_DIR / ".cache",
                coding_repo=args.coding_repo.resolve(),
            )

        # Score mode — reads ledger, writes pages, invokes no review
        if args.score:
            if args.golden is None:
                print(
                    "--score requires --golden to specify the golden set",
                    file=sys.stderr,
                )
                return 2
            identity_flags = [f for f in (args.model, args.effort, args.mode) if f]
            if identity_flags:
                print(
                    f"identity flags (--model / --effort / --mode) have no meaning "
                    f"when scoring an existing ledger; its config_identity comes from "
                    f"the ledger rows",
                    file=sys.stderr,
                )
                return 2
            golden = load_golden(args.golden)
            rows = load_ledger(ledger_path(args.out_dir))
            return score_ledger(
                rows=rows,
                golden=golden,
                reports_dir=args.reports_dir,
                coding_repo=args.coding_repo.resolve(),
            )

        # Live mode — existing argument checks
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

        # Live mode with --golden — check prs_version match before any review
        golden = None
        if args.golden is not None:
            golden = load_golden(args.golden)
            manifest = load_manifest(args.manifest)
            if golden["prs_version"] != manifest["version"]:
                print(
                    f"{GOLDEN_VERSION_MISMATCH_MARKER}: "
                    f"golden prs_version {golden['prs_version']!r} != "
                    f"manifest version {manifest['version']!r}",
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
            golden=golden,
            reports_dir=args.reports_dir,
        )

    except BenchError as err:
        print(str(err), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
