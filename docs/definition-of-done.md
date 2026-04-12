# Definition of Done — Dark Factory Prompts

Rules that every dark-factory prompt execution must satisfy before reporting success.

## Test Coverage

**New code** (new files, new packages):
- Aim for ≥80% statement coverage
- Test all public functions
- Test error paths and edge cases (empty input, nil, invalid values)

**Modified code** (changes to existing files):
- Test all changed/added code paths — every new branch, every new condition
- Existing untested code does NOT need retroactive coverage
- If adding a new field/method to a struct, test the new behavior

**Verification (Go):**
```bash
go test -coverprofile=/tmp/cover.out -mod=vendor ./affected/pkg/...
go tool cover -func=/tmp/cover.out | grep "changed_file"
```

**Verification (Python):**
```bash
pytest --cov=affected_module --cov-report=term-missing
```

## Code Quality

- Follow project CLAUDE.md conventions
- Follow all relevant docs in `~/.claude/plugins/marketplaces/coding/docs/`
- Self-review diff against the checklist in CLAUDE.md before `make precommit`

## Verification

- `make test` after each meaningful change (fast feedback)
- `make precommit` once at the end (full validation)
- **Multi-service repos:** only run in the changed service directory, never at repo root
- **YAML/config-only changes:** skip `make precommit`, use the prompt's `<verification>` commands
- Non-zero exit code from `make precommit` = failed, no exceptions

## Changelog

- Update `CHANGELOG.md` with `## Unreleased` entry if project has one
- See `changelog-guide.md` for format rules

## Completion

- Report honest status: success only if `make precommit` exit code 0
- Include verification command and exit code in report
