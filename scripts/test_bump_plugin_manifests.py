#!/usr/bin/env python3
"""Tests for bump-plugin-manifests.py."""

import contextlib
import importlib.util
import io
import os
import tempfile
import unittest

_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bump-plugin-manifests.py")
_spec = importlib.util.spec_from_file_location("bump_plugin_manifests", _SCRIPT)
bump = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bump)


PLUGIN_JSON = """{
  "name": "widgets",
  "description": "Widget helpers",
  "version": "0.9.12",
  "author": {
    "name": "A User"
  }
}
"""

MARKETPLACE_TWO = """{
  "name": "widgets",
  "metadata": {
    "description": "Widget helpers",
    "version": "0.9.12"
  },
  "plugins": [
    {
      "name": "widgets",
      "source": "./",
      "version": "0.9.12",
      "strict": true
    },
    {
      "name": "widgets-extra",
      "source": "./extra",
      "version": "0.9.12"
    }
  ]
}
"""


def marketplace_with(n):
    """Build a marketplace.json with n plugin entries, all at 0.9.12."""
    entries = []
    for i in range(n):
        entries.append(
            '    {\n      "name": "widgets-%d",\n      "source": "./%d",\n'
            '      "version": "0.9.12"\n    }' % (i, i)
        )
    body = ",\n".join(entries)
    plugins = "[\n%s\n  ]" % body if entries else "[]"
    return (
        '{\n  "name": "widgets",\n  "metadata": {\n'
        '    "description": "Widget helpers",\n    "version": "0.9.12"\n  },\n'
        '  "plugins": %s\n}\n' % plugins
    )


def changed_lines(before, after):
    before_lines = before.decode("utf-8").split("\n")
    after_lines = after.decode("utf-8").split("\n")
    return sum(1 for a, b in zip(before_lines, after_lines) if a != b) + abs(
        len(before_lines) - len(after_lines)
    )


class DetectManifestsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, content):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def test_neither(self):
        self.assertEqual(bump.detect_manifests(self.dir), [])

    def test_plugin_only(self):
        self.write(".claude-plugin/plugin.json", PLUGIN_JSON)
        self.assertEqual(bump.detect_manifests(self.dir), [bump.PLUGIN_JSON])

    def test_marketplace_only(self):
        self.write(".claude-plugin/marketplace.json", MARKETPLACE_TWO)
        self.assertEqual(bump.detect_manifests(self.dir), [bump.MARKETPLACE_JSON])

    def test_both(self):
        self.write(".claude-plugin/plugin.json", PLUGIN_JSON)
        self.write(".claude-plugin/marketplace.json", MARKETPLACE_TWO)
        self.assertEqual(
            bump.detect_manifests(self.dir), [bump.PLUGIN_JSON, bump.MARKETPLACE_JSON]
        )

    def test_manifest_in_subdirectory_is_ignored(self):
        self.write("nested/.claude-plugin/plugin.json", PLUGIN_JSON)
        self.assertEqual(bump.detect_manifests(self.dir), [])


class BumpPluginJsonTest(unittest.TestCase):
    def test_bumps_version(self):
        rewritten, old = bump.bump_plugin_json(PLUGIN_JSON.encode(), "0.10.0")
        self.assertEqual(old, "0.9.12")
        self.assertIn('"version": "0.10.0"', rewritten.decode())
        self.assertEqual(changed_lines(PLUGIN_JSON.encode(), rewritten), 1)

    def test_preserves_missing_trailing_newline(self):
        content = PLUGIN_JSON.rstrip("\n").encode()
        rewritten, _ = bump.bump_plugin_json(content, "0.10.0")
        self.assertFalse(rewritten.endswith(b"\n"))

    def test_preserves_other_bytes(self):
        rewritten, _ = bump.bump_plugin_json(PLUGIN_JSON.encode(), "0.10.0")
        expected = PLUGIN_JSON.replace('"version": "0.9.12"', '"version": "0.10.0"')
        self.assertEqual(rewritten.decode(), expected)

    def test_noop_is_byte_identical(self):
        first, _ = bump.bump_plugin_json(PLUGIN_JSON.encode(), "0.10.0")
        second, _ = bump.bump_plugin_json(first, "0.10.0")
        self.assertEqual(first, second)

    def test_missing_version_field_errors(self):
        content = b'{\n  "name": "widgets"\n}\n'
        with self.assertRaises(bump.ManifestError) as caught:
            bump.bump_plugin_json(content, "0.10.0")
        self.assertIn("version field not found", str(caught.exception))

    def test_non_semver_existing_value_errors(self):
        content = b'{\n  "version": "not-a-version"\n}\n'
        with self.assertRaises(bump.ManifestError) as caught:
            bump.bump_plugin_json(content, "0.10.0")
        self.assertIn("semver-shaped", str(caught.exception))

    def test_non_semver_target_errors(self):
        with self.assertRaises(bump.ManifestError) as caught:
            bump.bump_plugin_json(PLUGIN_JSON.encode(), "v0.10.0")
        self.assertIn("not a semver-shaped string", str(caught.exception))


class BumpMarketplaceJsonTest(unittest.TestCase):
    def test_zero_plugin_entries(self):
        content = marketplace_with(0).encode()
        rewritten, changes = bump.bump_marketplace_json(content, "0.10.0")
        self.assertEqual([label for label, _ in changes], ["metadata.version"])
        self.assertEqual(changed_lines(content, rewritten), 1)

    def test_one_plugin_entry(self):
        content = marketplace_with(1).encode()
        rewritten, changes = bump.bump_marketplace_json(content, "0.10.0")
        self.assertEqual(
            [label for label, _ in changes], ["metadata.version", "plugins[].version"]
        )
        self.assertEqual(changed_lines(content, rewritten), 2)

    def test_three_plugin_entries(self):
        content = marketplace_with(3).encode()
        rewritten, changes = bump.bump_marketplace_json(content, "0.10.0")
        self.assertEqual(
            [label for label, _ in changes],
            ["metadata.version", "plugins[].version", "plugins[].version", "plugins[].version"],
        )
        self.assertEqual(changed_lines(content, rewritten), 4)

    def test_every_old_value_is_the_previous_version(self):
        _, changes = bump.bump_marketplace_json(marketplace_with(3).encode(), "0.10.0")
        self.assertEqual({old for _, old in changes}, {"0.9.12"})

    def test_noop_is_byte_identical(self):
        first, _ = bump.bump_marketplace_json(MARKETPLACE_TWO.encode(), "0.10.0")
        second, _ = bump.bump_marketplace_json(first, "0.10.0")
        self.assertEqual(first, second)

    def test_missing_version_fields_errors(self):
        content = b'{\n  "name": "widgets",\n  "plugins": []\n}\n'
        with self.assertRaises(bump.ManifestError) as caught:
            bump.bump_marketplace_json(content, "0.10.0")
        self.assertIn("version field not found", str(caught.exception))

    def test_non_semver_target_errors(self):
        with self.assertRaises(bump.ManifestError):
            bump.bump_marketplace_json(MARKETPLACE_TWO.encode(), "0.10")


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        os.makedirs(os.path.join(self.dir, ".claude-plugin"))
        with open(os.path.join(self.dir, bump.PLUGIN_JSON), "w", encoding="utf-8") as handle:
            handle.write(PLUGIN_JSON)
        with open(os.path.join(self.dir, bump.MARKETPLACE_JSON), "w", encoding="utf-8") as handle:
            handle.write(MARKETPLACE_TWO)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, rel):
        with open(os.path.join(self.dir, rel), "rb") as handle:
            return handle.read()

    def run_cli(self, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            return bump.main(args)

    def test_paths_prints_each_manifest(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(bump.main(["--paths", "--workdir", self.dir]), 0)
        self.assertEqual(
            out.getvalue().split(), [bump.PLUGIN_JSON, bump.MARKETPLACE_JSON]
        )

    def test_plan_writes_nothing(self):
        before = self.read(bump.PLUGIN_JSON)
        self.assertEqual(self.run_cli(["--plan", "--workdir", self.dir]), 0)
        self.assertEqual(self.read(bump.PLUGIN_JSON), before)

    def test_apply_writes_both_manifests(self):
        self.assertEqual(self.run_cli(["--apply", "0.10.0", "--workdir", self.dir]), 0)
        self.assertIn(b'"version": "0.10.0"', self.read(bump.PLUGIN_JSON))
        self.assertIn(b'"version": "0.10.0"', self.read(bump.MARKETPLACE_JSON))

    def test_apply_rejects_non_semver(self):
        self.assertEqual(self.run_cli(["--apply", "v0.10.0", "--workdir", self.dir]), 1)


if __name__ == "__main__":
    unittest.main()
