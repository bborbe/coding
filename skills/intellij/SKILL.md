---
description: Open IntelliJ IDEA in directory
allowed-tools: Bash
argument-hint: [directory]
---

Open IntelliJ IDEA in the specified directory or current directory.

Usage:
- `/coding:intellij` — open current directory
- `/coding:intellij src` — open subdirectory

```bash
DIR="${ARGUMENTS:-$(pwd)}"
[[ ! "$DIR" = /* ]] && DIR="$(pwd)/$DIR"
open -na "IntelliJ IDEA.app" --args "$DIR"
```
