#!/usr/bin/env python3
"""Detect and bump Claude Code plugin manifest versions.

Port of bborbe/github-releaser-agent pkg/plugin/manifest.go
(DetectManifests, BumpPluginJSON, BumpMarketplaceJSON). The rewrite is
line-anchored and byte-preserving: only the located version value changes,
so the release commit's diff is one line per version field.

Modes:
  --paths            print the detected manifest paths, one per line; writes
                     nothing (empty output when the repo has no manifests)
  --plan             print the detected manifests and the version fields a
                     bump would rewrite; writes nothing
  --apply VERSION    rewrite the version fields to VERSION (unprefixed
                     semver, e.g. 1.2.3); print one line per field

Exit 0 on success, 1 on any error.
"""

import argparse
import os
import re
import sys

PLUGIN_JSON = ".claude-plugin/plugin.json"
MARKETPLACE_JSON = ".claude-plugin/marketplace.json"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
PLUGINS_ARRAY_LINE_RE = re.compile(r'^\s*"plugins"\s*:\s*\[')
OPEN_SCOPE_KEY_RE = re.compile(r'^\s*"[^"]+"\s*:\s*\{')


class ManifestError(Exception):
    """A manifest could not be bumped; the message names the file and reason."""


# --------------------------------------------------------------------------
# line helpers
# --------------------------------------------------------------------------


def trim_line(line):
    return line.strip(" \t\r")


def get_indent(line):
    return line[: len(line) - len(line.lstrip(" \t"))]


def count_open(line):
    return sum(1 for ch in line if ch in "{[")


def count_close(line):
    return sum(1 for ch in line if ch in "}]")


def is_close_brace(line):
    return "}" in line


def is_close_bracket(line):
    return "]" in line


def line_has_version_key(trimmed):
    """True when the trimmed line opens a "version" key.

    Distinguishes the key from the word "version" appearing inside another
    string value by requiring a JSON structural character before the quote.
    """
    idx = trimmed.find('"version":')
    if idx < 0:
        idx = trimmed.find('"version" :')
    if idx < 0:
        return False
    if idx == 0:
        return True
    return trimmed[idx - 1] in ",{[" or trimmed[idx - 1] in " \t"


def split_lines(content):
    """Split bytes into lines, reporting whether the last one ends in a newline."""
    text = content.decode("utf-8")
    lines = text.split("\n")
    trailing_newline = lines[-1] == ""
    if trailing_newline:
        lines.pop()
    lines = [line[:-1] if line.endswith("\r") else line for line in lines]
    return lines, trailing_newline


def join_lines(lines, trailing_newline):
    text = "\n".join(lines)
    if trailing_newline and lines:
        text += "\n"
    return text.encode("utf-8")


# --------------------------------------------------------------------------
# version value rewrite
# --------------------------------------------------------------------------


def rewrite_version_value(line, version, file_type):
    """Replace the value of a "version" key on `line`.

    Returns (new_line, old_value). Every other byte of the line is preserved,
    except that the key/value separator is normalized to one space, matching
    the reference implementation.
    """
    trimmed = trim_line(line)

    key_idx = trimmed.find('"version":')
    if key_idx < 0:
        key_idx = trimmed.find('"version" :')
    if key_idx < 0:
        raise ManifestError("%s version line has no version key" % file_type)

    colon_idx = trimmed.find(":", key_idx)
    if colon_idx < 0:
        raise ManifestError("%s version line has no colon" % file_type)

    rest = trimmed[colon_idx + 1 :].lstrip(" \t")
    if not rest:
        raise ManifestError(
            '%s existing version field is not a semver-shaped string: ""' % file_type
        )

    if rest[0] in "\"'":
        quote = rest[0]
        body = rest[1:]
        close_idx = -1
        for i, ch in enumerate(body):
            if ch == quote:
                backslashes = 0
                j = i - 1
                while j >= 0 and body[j] == "\\":
                    backslashes += 1
                    j -= 1
                if backslashes % 2 == 0:
                    close_idx = i
                    break
        if close_idx < 0:
            raise ManifestError(
                '%s existing version field is not a semver-shaped string: ""' % file_type
            )
        old_value = body[:close_idx]
        trailing = body[close_idx + 1 :]
    else:
        end = 0
        while end < len(rest) and rest[end] not in ",} \t":
            end += 1
        old_value = rest[:end]
        trailing = rest[end:]

    if not SEMVER_RE.match(old_value):
        raise ManifestError(
            '%s existing version field is not a semver-shaped string: "%s"'
            % (file_type, old_value)
        )

    key_part = trimmed[: colon_idx + 1]
    return '%s%s "%s"%s' % (get_indent(line), key_part, version, trailing), old_value


def require_semver(version, file_type):
    if not SEMVER_RE.match(version):
        raise ManifestError(
            '%s bump rejected: version parameter "%s" is not a semver-shaped string'
            % (file_type, version)
        )


# --------------------------------------------------------------------------
# plugin.json
# --------------------------------------------------------------------------


def bump_plugin_json(content, version):
    """Rewrite the first top-level "version" value. Returns (bytes, old_value)."""
    require_semver(version, "plugin.json")
    if not content:
        raise ManifestError("plugin.json version field not found")

    lines, trailing_newline = split_lines(content)
    out = []
    old_value = None
    for line in lines:
        if old_value is None and line_has_version_key(trim_line(line)):
            rewritten, old_value = rewrite_version_value(line, version, "plugin.json")
            out.append(rewritten)
            continue
        out.append(line)

    if old_value is None:
        raise ManifestError("plugin.json version field not found")
    return join_lines(out, trailing_newline), old_value


# --------------------------------------------------------------------------
# marketplace.json
# --------------------------------------------------------------------------


class ScopeTracker:
    """Depth + scope flags for the marketplace.json streaming state machine.

    The zero value is the initial state (depth 0, all scopes False).
    """

    def __init__(self):
        self.depth = 0
        self.in_metadata = False
        self.in_plugin = False
        self.in_plugins_array = False

    def update(self, line, trimmed):
        old_depth = self.depth

        # Handle closing at old_depth BEFORE we update depth.
        if old_depth == 2 and is_close_brace(line):
            self.in_metadata = False
            self.in_plugin = False

        # "plugins": [ opens the array when we are already inside the root object.
        if old_depth >= 1 and PLUGINS_ARRAY_LINE_RE.match(trimmed):
            self.in_plugins_array = True

        depth_delta = count_open(line) - count_close(line)
        self.depth = old_depth + depth_delta

        if depth_delta > 0 and old_depth == 1 and OPEN_SCOPE_KEY_RE.match(trimmed):
            if extract_scope_key(trimmed) == "metadata":
                self.in_metadata = True
                self.in_plugin = False
                self.in_plugins_array = False

        if self.in_plugins_array and trimmed.startswith("{"):
            if old_depth in (2, 1, 0):
                self.in_plugin = True
                self.in_metadata = False

        if old_depth == 2 and is_close_bracket(line) and self.in_plugins_array:
            self.in_plugins_array = False
            self.in_plugin = False

        if self.depth == 0:
            self.in_metadata = False
            self.in_plugin = False
            self.in_plugins_array = False

    def in_version_scope(self):
        return self.in_metadata or self.in_plugin

    def scope_label(self):
        return "metadata.version" if self.in_metadata else "plugins[].version"


def extract_scope_key(trimmed):
    start = trimmed.find('"')
    if start < 0:
        return ""
    end = trimmed.find('"', start + 1)
    if end > start:
        return trimmed[start + 1 : end]
    return ""


def marketplace_version_scopes(content):
    """Yield the scope label of every version key in the marketplace stream."""
    lines, _ = split_lines(content)
    tracker = ScopeTracker()
    for line in lines:
        trimmed = trim_line(line)
        tracker.update(line, trimmed)
        if line_has_version_key(trimmed) and tracker.in_version_scope():
            yield tracker.scope_label()


def bump_marketplace_json(content, version):
    """Rewrite metadata.version and every plugins[].version.

    Returns (bytes, [(scope_label, old_value), ...]).
    """
    require_semver(version, "marketplace.json")
    if not content:
        raise ManifestError("marketplace.json version field not found")

    lines, trailing_newline = split_lines(content)
    tracker = ScopeTracker()
    out = []
    changes = []
    for line in lines:
        trimmed = trim_line(line)
        tracker.update(line, trimmed)
        if line_has_version_key(trimmed) and tracker.in_version_scope():
            rewritten, old_value = rewrite_version_value(line, version, "marketplace.json")
            out.append(rewritten)
            changes.append((tracker.scope_label(), old_value))
            continue
        out.append(line)

    if not changes:
        raise ManifestError("marketplace.json version field not found")
    return join_lines(out, trailing_newline), changes


# --------------------------------------------------------------------------
# detection + CLI
# --------------------------------------------------------------------------


def detect_manifests(workdir):
    """Return the known manifest paths that exist as regular files, in order."""
    found = []
    for rel in (PLUGIN_JSON, MARKETPLACE_JSON):
        if os.path.isfile(os.path.join(workdir, rel)):
            found.append(rel)
    return found


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def write_bytes(path, content):
    with open(path, "wb") as handle:
        handle.write(content)


def run_paths(workdir):
    for rel in detect_manifests(workdir):
        print(rel)
    return 0


def run_plan(workdir):
    manifests = detect_manifests(workdir)
    if not manifests:
        print("no plugin manifests in %s — release commit touches CHANGELOG.md only" % workdir)
        return 0

    print("plugin manifests in %s:" % workdir)
    for rel in manifests:
        content = read_bytes(os.path.join(workdir, rel))
        if rel == PLUGIN_JSON:
            fields = ["version"]
        else:
            fields = []
            for label in marketplace_version_scopes(content):
                if label not in fields:
                    fields.append(label)
        print("  %-34s %s" % (rel, ", ".join(fields) if fields else "(no version field)"))
    return 0


def run_apply(workdir, version):
    manifests = detect_manifests(workdir)
    if not manifests:
        print("no plugin manifests in %s — nothing to bump" % workdir)
        return 0

    for rel in manifests:
        path = os.path.join(workdir, rel)
        content = read_bytes(path)
        if rel == PLUGIN_JSON:
            new_content, old_value = bump_plugin_json(content, version)
            changes = [("version", old_value)]
        else:
            new_content, changes = bump_marketplace_json(content, version)

        if new_content == content:
            for field, _ in changes:
                print("%s: %s unchanged (already %s)" % (rel, field, version))
            continue

        write_bytes(path, new_content)
        for field, old_value in changes:
            print("%s: %s %s -> %s" % (rel, field, old_value, version))
    return 0


def main(argv):
    parser = argparse.ArgumentParser(
        description="Detect and bump Claude Code plugin manifest versions."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--paths", action="store_true", help="print detected manifest paths")
    mode.add_argument("--plan", action="store_true", help="print the bump plan; write nothing")
    mode.add_argument("--apply", metavar="VERSION", help="rewrite version fields to VERSION")
    parser.add_argument("--workdir", default=".", help="repo root (default: cwd)")
    args = parser.parse_args(argv)

    workdir = os.path.abspath(args.workdir)
    try:
        if args.paths:
            return run_paths(workdir)
        if args.plan:
            return run_plan(workdir)
        return run_apply(workdir, args.apply)
    except ManifestError as error:
        print("ERROR: %s" % error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
