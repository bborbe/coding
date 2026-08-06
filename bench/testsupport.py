#!/usr/bin/env python3
#
# testsupport.py — shared test helpers for bench unit tests
#
# Python 3 standard library only — no third-party dependencies.

import os
import pathlib
import shutil
import stat
import subprocess


def make_coding_repo(root: pathlib.Path, *, rules=None, commands=None) -> pathlib.Path:
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


def make_verify_config_dir(root: pathlib.Path, plugin_src: pathlib.Path,
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
        import json as _json
        (cfg / "plugins" / "known_marketplaces.json").write_text(
            _json.dumps(known), encoding="utf-8"
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
        f"printf '%s\\n' '$*' >> '{counter_file}'\n"
        f"cat <<'REPORT_EOF'\n{report_text}\nREPORT_EOF"
    )
    return make_stub_bin(bin_dir, "claude", body)


def with_path(bin_dir: pathlib.Path) -> dict:
    """Return a copy of os.environ with bin_dir prepended to PATH."""
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    return env
