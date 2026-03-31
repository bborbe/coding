---
description: Open VSCode in directory
allowed-tools: Bash
argument-hint: [directory]
---

Open Visual Studio Code in the specified directory or current directory.

Usage:
- `/coding:vscode` — open current directory
- `/coding:vscode src` — open subdirectory

```bash
DIR="${ARGUMENTS:-$(pwd)}"
[[ ! "$DIR" = /* ]] && DIR="$(pwd)/$DIR"
open -a "/Applications/Visual Studio Code.app" "$DIR"
```
