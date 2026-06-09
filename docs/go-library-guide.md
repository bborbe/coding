
# 📘 Comprehensive Guide: GitHub Project Structure for a Go Library (with Ginkgo & Gomega)

This guide outlines best practices for structuring a GitHub project for a Go (Golang) library, using **Ginkgo** and **Gomega** for testing.

---

## 📁 Project Structure

```
mygolib/
├── .github/
│   └── workflows/
├── cmd/
├── pkg/
├── go.mod
├── go.sum
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .gitignore
```

---

## 📄 Essential Top-Level Files

### ✅ `README.md`
Includes:
- Project purpose
- Installation and usage
- Quickstart example
- API links
- Status badges

### ✅ `LICENSE`
Use standard licenses like MIT or Apache 2.0.

### ✅ `go.mod`
Defines module path and dependencies.

### ✅ `.gitignore`
Ignore common Go build artifacts.

---

## 🧪 Testing with Ginkgo & Gomega

### ✅ Install Ginkgo & Gomega

```bash
go install github.com/onsi/ginkgo/v2/ginkgo@latest
go get github.com/onsi/gomega/...
```

### ✅ Write a Test Suite

Generate a test suite:

```bash
ginkgo bootstrap
ginkgo generate mylib
```

Example `mylib_test.go`:

```go
package mygolib_test

import (
    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"
)

var _ = Describe("Add", func() {
    It("adds two numbers", func() {
        Expect(1 + 2).To(Equal(3))
    })
})
```

### ✅ Run Tests

```bash
ginkgo -v
```

## 📘 Documentation

- Use inline GoDoc comments.
- Host on [pkg.go.dev](https://pkg.go.dev/).

---

## 📦 Versioning

### RULE go-library/semver-vprefix-tag-required (MUST)

**Owner**: go-quality-assistant
**Applies when**: a public Go library repo cuts a release without a `git tag` matching `v<MAJOR>.<MINOR>.<PATCH>` (e.g. `v1.0.0`, `v0.12.3`) — either tagless commits, date-based tags (`2026-06-03`), or non-prefixed semver (`1.0.0` without the leading `v`).
**Enforcement**: `scripts/rule-checks.sh` (`git tag --list` filtered against `^v[0-9]+\.[0-9]+\.[0-9]+$` when `.git` present)
**Why**: Go's module system parses tags as `vMAJOR.MINOR.PATCH` — consumers pin to versions via `go get github.com/x/y@v1.2.3`. A tag without the `v` prefix doesn't resolve as a module version; a date-tag doesn't either. Untagged commits force consumers to depend on pseudo-versions (`v0.0.0-20260403114524-913de8870914`), which work but are unreadable and don't survive Go's MVS upgrade logic predictably. The `v` prefix is a hard requirement of `go.mod`'s grammar; semver is the convention Go's module proxy is built on.

Tag releases using semantic versioning:

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## ✅ Summary Checklist

| Component             | Required | Recommended | Optional |
|----------------------|----------|-------------|----------|
| `README.md`          | ✅        |             |          |
| `LICENSE`            | ✅        |             |          |
| `go.mod`             | ✅        |             |          |
| Ginkgo/Gomega Tests  | ✅        |             |          |
| GitHub Actions       |          | ✅            |          |
| GoDoc                | ✅        |             |          |
| `CHANGELOG.md`       | ✅        | ✅           |          |
| `Makefile` or Lint   |          | ✅           |          |

---

Happy coding! 🎉
