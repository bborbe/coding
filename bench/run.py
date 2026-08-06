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
import hashlib
import json
import os
import pathlib
import re
import sys

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
REQUIRED_ENTRY_FIELDS = (
    "id", "owner", "repo", "number",
    "merge_strategy", "merge_sha", "base_sha", "head_sha", "changed_files",
)

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


def resolve_plugin_path(config_dir: pathlib.Path) -> pathlib.Path:
    """Resolve the coding plugin path from the isolated config directory.

    If config_dir/plugins/known_marketplaces.json exists and contains a usable
    "coding" entry with a non-empty installLocation, that path is returned.
    Otherwise falls back to config_dir/plugins/marketplaces/coding.
    """
    known = config_dir / "plugins" / "known_marketplaces.json"
    if known.is_file():
        try:
            data = json.loads(known.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise BenchError(f"cannot parse {known}: {err}")
        coding_entry = data.get("coding", {})
        install_location = coding_entry.get("installLocation", "")
        if install_location and isinstance(install_location, str):
            return pathlib.Path(install_location)
    return config_dir / "plugins" / "marketplaces" / "coding"


def check_plugin_resolution(coding_repo: pathlib.Path, config_dir: pathlib.Path,
                            expected_hash: str) -> pathlib.Path:
    """Verify the isolated config dir will load the coding plugin from coding_repo.

    Raises BenchError (PLUGIN RESOLUTION MISMATCH) if the plugin actually
    resolved to a path whose rules/+commands/ content differs from
    expected_hash.  Runs before any review is invoked.
    """
    plugin_path = resolve_plugin_path(config_dir)

    if not plugin_path.is_dir():
        actual = "<missing>"
    else:
        try:
            actual = content_hash(plugin_path)
        except BenchError:
            actual = "<no-rules-or-commands>"

    if actual != expected_hash:
        raise BenchError(
            f"PLUGIN RESOLUTION MISMATCH: config_dir={config_dir} "
            f"plugin_path={plugin_path} actual_hash={actual} "
            f"coding_repo={coding_repo} expected_hash={expected_hash} "
            f"refusing to record a configuration hash that did not run"
        )

    return plugin_path


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
    check_plugin_resolution(coding_repo, config_dir, rc_hash)

    cfg_hash = config_hash(rc_hash, model, effort, mode, manifest["version"])

    print(
        f"config {cfg_hash[:16]} rules+commands {rc_hash[:16]} "
        f"model={model} effort={effort} mode={mode} prs={manifest['version']}"
    )

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
            )
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
               rc_hash: str, prs_version: str) -> tuple[str, str]:
    """Process a single PR — stub for prompt 2 of spec 002.

    PR resolution (prompt 2) and review invocation (prompt 3) are not yet
    implemented.  This stub loudly fails so the gap cannot be mistaken for
    success.
    """
    return ("failed", "pr resolution not yet implemented (prompt 2 of spec 002)")


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
