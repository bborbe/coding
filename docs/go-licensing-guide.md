# Go Project Licensing Guide

This guide covers how to properly handle licensing in Go projects.

## Public vs Private Repos

Licensing requirements depend on whether the repository is **public** or **private/internal**:

| | Public (GitHub) | Private/Internal (Bitbucket) |
|---|---|---|
| LICENSE file | Required | Not needed |
| README license section | Required | Not needed |
| Source file headers | Required | Not needed |

**How to detect**: If the repo is hosted on `github.com` → public. If hosted on `bitbucket.seibert.tools` or similar internal hosting → private/internal.

The rest of this guide applies to **public repositories only**.

## Overview

Public projects in the Benjamin Borbe ecosystem use **BSD-2-Clause** (BSD-style) licensing with three components:

1. **LICENSE file** in the root directory
2. **License section** in README.md
3. **License headers** in all Go source files

---

## 1. LICENSE File

Place a `LICENSE` file in the root directory with the BSD-2-Clause license text:

```
Copyright (c) 2025, Benjamin Borbe <benjamin.borbe@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

   * Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.
   * Redistributions in binary form must reproduce the above
     copyright notice, this list of conditions and the following
     disclaimer in the documentation and/or other materials provided
     with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

**Copyright year guidance:**
- Use the year when the project was first created
- Don't update years annually just because it's a new year
- Optionally update to a range when making substantial changes (e.g., `2020-2025`)

---

## 2. README License Section

Add this at the end of README.md:

```markdown
---

## License

BSD-style license. See [LICENSE](LICENSE) file for details.
```

Keep it simple - the full text is in the LICENSE file.

---

## 3. Source File License Headers

All `.go` files (excluding `vendor/`) must have license headers:

```go
// Copyright (c) 2025 Benjamin Borbe All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package main
```

### Automated Management with `addlicense`

Use the [`addlicense`](https://github.com/google/addlicense) tool to automatically add headers:

```bash
# Run via Makefile (recommended)
make addlicense

# Or run directly
go run -mod=mod github.com/google/addlicense \
  -c "Benjamin Borbe" \
  -y $(date +'%Y') \
  -l bsd \
  $(find . -name "*.go" -not -path './vendor/*')
```

**What it does:**
- Adds headers to files that are missing them
- Doesn't modify existing headers (safe to run repeatedly)
- Uses current year for NEW files only

**Check-only mode** (verify without modifying):
```bash
go run -mod=mod github.com/google/addlicense \
  -check \
  -c "Benjamin Borbe" \
  -y $(date +'%Y') \
  -l bsd \
  $(find . -name "*.go" -not -path './vendor/*')
```

---

## Copyright Year Practices

**Simple rule:** Don't overthink copyright years.

### For New Files
- Use the current year when creating new files
- Run `make addlicense` to add headers automatically

### For Existing Files
- Keep the original year - it marks when copyright was established
- Optionally update to a range when making substantial changes (e.g., `2020-2025`)
- Not updating years is fine - it's conservative and acceptable

### What NOT to Do
- Don't bulk update all years just because it's a new year
- Don't update years for trivial formatting changes
- Don't use future years or "present"

**Examples:**
```go
// New file created in 2025
// Copyright (c) 2025 Benjamin Borbe All rights reserved.

// Old file from 2020, not modified (keep as-is)
// Copyright (c) 2020 Benjamin Borbe All rights reserved.

// Old file from 2020, substantially modified in 2025 (optional update)
// Copyright (c) 2020-2025 Benjamin Borbe All rights reserved.
```

---

## Workflow Integration

### Pre-Commit Process
The `make precommit` target includes `addlicense`:

```makefile
precommit: ensure format generate test check addlicense
	@echo "ready to commit"
```

Just run `make precommit` before committing - it will add any missing headers automatically.

### New Project Setup

1. Create LICENSE file with current year
2. Add license section to README.md
3. Run `make addlicense` to add headers to source files
4. Add `addlicense` to tools.go:
   ```go
   //go:build tools

   package tools

   import (
       _ "github.com/google/addlicense"
   )
   ```

### Copying Files from Other Projects

When copying files with older copyright years:
- Keep the original year if code is unchanged
- Update to a range if you modify it: `2020-2025`

---

## Common addlicense Flags

```bash
addlicense [flags] pattern [pattern ...]

Useful flags:
  -c string     Copyright holder (e.g., "Benjamin Borbe")
  -y string     Copyright year(s) (e.g., "2025" or "2020-2025")
  -l string     License type: bsd, apache, mit, mpl
  -check        Check-only mode: verify headers without modifying
  -v            Verbose: print modified/skipped files
  -ignore value File patterns to ignore (e.g., -ignore vendor/**)
```

---

## Key Takeaways

1. Three components: LICENSE file, README section, source headers
2. Use `make addlicense` to automate header management
3. Run `make precommit` before every commit
4. Don't overthink copyright years - use current year for new files, keep original for existing
5. Updating years when modifying files is optional, not required

---

## Additional Resources

- [addlicense GitHub](https://github.com/google/addlicense)
- [BSD-2-Clause License Text](https://opensource.org/licenses/BSD-2-Clause)
