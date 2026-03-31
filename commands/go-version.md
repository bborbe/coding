---
description: Check and optionally update Go version across project files (go.mod, Dockerfile, CI configs)
argument-hint: [check|update] [optional: directory...]
allowed-tools:
  - Task
---

# Go Version

This command checks or updates the Go version across all project files using the coding:go-version-manager agent. Supports multiple directories for batch processing.

## Usage

**Single Directory:**
- `/coding:go-version` - Check Go version in current directory (report only)
- `/coding:go-version check` - Check Go version (report only)
- `/coding:go-version update` - Update Go version to latest stable
- `/coding:go-version check .` - Check current directory
- `/coding:go-version update .` - Update current directory

**Multiple Directories (Batch Mode):**
- `/coding:go-version update commerce golden jira` - Update all 3 directories in single pass
- `/coding:go-version check atlassian hubspot google` - Check multiple directories

## Workflow

1. **Parse Arguments**: Determine mode (check/update) and directory(s) from $ARGUMENTS
2. **Invoke Agent**: Call coding:go-version-manager agent with appropriate instructions
3. **Report Results**: Agent provides detailed version check or update report

## Implementation

Execute the following steps:

1. Parse arguments:
   - First argument (if provided): mode (`check` or `update`)
   - Remaining arguments: directory paths (one or more)
   - Default: `check` mode in current directory

2. Invoke the coding:go-version-manager agent using the Task tool:

   **For single directory (original behavior)**:

   Check mode:
   ```
   Use Task tool with subagent_type=coding:go-version-manager
   Prompt: "Check the Go version in [directory]. Fetch the latest stable Go version from go.dev/dl/?mode=json. Scan all relevant files (go.mod, Dockerfile, *.dockerfile, .github/workflows/*.yml, .gitlab-ci.yml, .circleci/config.yml, .travis.yml, Makefile, README.md, go.work) for Go version declarations. Report current versions, latest stable version, consistency status, and update recommendations. This is a read-only check - do not make any modifications."
   ```

   Update mode:
   ```
   Use Task tool with subagent_type=coding:go-version-manager
   Prompt: "Update the Go version in [directory] to the latest stable version. Fetch the latest stable Go version from go.dev/dl/?mode=json. Scan and update all relevant files (go.mod, Dockerfile, *.dockerfile, .github/workflows/*.yml, .gitlab-ci.yml, .circleci/config.yml, .travis.yml, Makefile, README.md, go.work). Ensure all files are updated consistently. Verify the updates with go list -m and go version. Provide a detailed report of all changes made."
   ```

   **For multiple directories (batch mode)**:

   Check mode:
   ```
   Use Task tool with subagent_type=coding:go-version-manager
   Prompt: "Check the Go version in multiple directories: [dir1, dir2, dir3]. Fetch the latest stable Go version from go.dev/dl/?mode=json ONCE (cache it for all directories). For each directory, scan all relevant files (go.mod, Dockerfile, *.dockerfile, .github/workflows/*.yml, .gitlab-ci.yml, .circleci/config.yml, .travis.yml, Makefile, README.md, go.work) for Go version declarations. Report current versions per directory, latest stable version, consistency status across all directories, and update recommendations. Provide a summary table at the end. This is a read-only check - do not make any modifications."
   ```

   Update mode:
   ```
   Use Task tool with subagent_type=coding:go-version-manager
   Prompt: "Update the Go version in multiple directories: [dir1, dir2, dir3]. Fetch the latest stable Go version from go.dev/dl/?mode=json ONCE (cache it for all directories). For each directory, scan and update all relevant files (go.mod, Dockerfile, *.dockerfile, .github/workflows/*.yml, .gitlab-ci.yml, .circleci/config.yml, .travis.yml, Makefile, README.md, go.work). Ensure all files are updated consistently within each directory. Verify updates with go list -m. Provide a comprehensive report showing files updated per directory and summary statistics."
   ```

3. The coding:go-version-manager agent will handle:
   - Fetching latest stable Go version from https://go.dev/dl/?mode=json (once for batch mode)
   - Discovering all files with Go version declarations in each directory
   - Comparing current vs latest versions
   - Checking consistency across files
   - Reporting update urgency and recommendations
   - (Update mode only) Modifying files to latest version
   - (Update mode only) Verifying changes

## Files Checked/Updated

The agent scans and updates these file types:
- `go.mod` - Go module directive
- `Dockerfile`, `*.dockerfile` - Container base images
- `.github/workflows/*.yml` - GitHub Actions workflows
- `.gitlab-ci.yml` - GitLab CI configuration
- `.circleci/config.yml` - CircleCI configuration
- `.travis.yml` - Travis CI configuration
- `Makefile` - Build configuration
- `README.md` - Documentation
- `go.work` - Go workspace files

## Latest Version Source

Latest stable Go version is fetched from:
```bash
curl -s "https://go.dev/dl/?mode=json" | jq -r '.[] | select(.stable == true) | .version' | head -n 1
```

## Notes

- **Check mode** is read-only and safe to run anytime
- **Update mode** modifies files - review changes before committing
- Agent ensures all files are updated consistently
- Version format: `1.X.Y` (e.g., `1.25.3`)
- After updates, run `make precommit` to verify compatibility
