# Go Doc String Best Practices

This guide describes the best practices for writing Go documentation comments (doc strings), and how to use a Large Language Model (LLM) to improve their clarity, usefulness, and maintainability.

---

## 🧠 General Principles

- **Complete Sentences**: Start with a full sentence that begins with the name of the function, type, or package.
  - ✅ `// Add adds two integers and returns the result.`
- **Third-Person**: Avoid first-person perspective. Use descriptive, instructive tone.
- **No Code Duplication**: Avoid repeating the function signature in the comment.
- **Focus on Behavior and Use**: Explain what it *does* and how it’s used—not how it’s implemented.
- **Markdown-Like Style**: Use formatting like lists or bold when helpful (when using `godoc` renderers that support this).

### RULE go-doc/exported-item-must-have-comment (MUST)

**Owner**: godoc-assistant
**Applies when**: a Go file defines an exported (capitalized) function, method, type, interface, struct, struct field, constant, or variable without a preceding `//` doc comment.
**Enforcement**: judgment (mechanical follow-up: enable `revive`'s `exported` rule or `golangci-lint`'s `revive` linter with `exported` enabled — these flag every exported identifier without a doc comment)
**Trigger**: **/*.go
**Why**: `pkg.go.dev` renders every exported identifier — undocumented items show up as bare signatures with no context. Consumers reading the API page can't tell what `func Process(*Order) error` does without reading the source. Doc comments are a contract surface; missing them shifts the burden from the author (who knows) to every reader (who doesn't).

#### Bad

```go
type Order struct {
	ID       string
	Total    Price
	Customer Customer
}

func (o *Order) Apply(d Discount) Price { ... }
```

#### Good

```go
// Order represents a customer's purchase, holding line items and the
// computed total before any discounts are applied.
type Order struct {
	ID       string
	Total    Price
	Customer Customer
}

// Apply reduces the order's total by the given discount and returns
// the new total. Apply mutates the order in place.
func (o *Order) Apply(d Discount) Price { ... }
```

### RULE go-doc/comment-starts-with-name (MUST)

**Owner**: godoc-assistant
**Applies when**: an exported identifier has a doc comment whose first word does not match the identifier's name exactly (case-sensitive).
**Enforcement**: judgment (mechanical follow-up: no standard linter catches this — `revive`'s `exported` rule only flags *missing* doc comments, not first-word mismatch. Best path is an ast-grep pattern over `func_declaration` / `type_declaration` + adjacent comment text, comparing the first whitespace-delimited word against the identifier name — see PR #11 recipe for the surrounding-comment pattern shape)
**Trigger**: **/*.go
**Why**: `godoc` and `pkg.go.dev` build the docs from the first sentence of each comment and key it by the identifier name. When the comment starts with a different word, the rendered docs read as "X creates a new …" attached to identifier `Y` — confusing and grep-hostile. Starting with the identifier's name also forces the author to think about what the thing *is*, not what they wish it did.

#### Bad

```go
// Creates a new order with the given customer.   // first word ≠ "NewOrder"
func NewOrder(c Customer) *Order { ... }
```

#### Good

```go
// NewOrder returns an order initialised with the given customer
// and a zeroed total.
func NewOrder(c Customer) *Order { ... }
```

### RULE go-doc/package-comment-in-doc-go (SHOULD)

**Owner**: godoc-assistant
**Applies when**: a Go package's package-level comment lives in a regular source file (`<feature>.go`) rather than in a dedicated `doc.go`.
**Enforcement**: judgment (filename presence + first-comment-block check)
**Trigger**: **/*.go
**Why**: When the package comment lives in `order.go`, deleting / refactoring / renaming that file silently strips the package documentation. `doc.go` is a convention — every reader knows where to find package-level docs, and refactors of business-logic files don't accidentally damage the docs.

#### Bad

```go
// order.go
// Package orders manages customer purchases.
package orders

type Order struct { ... }   // delete this file → package comment gone
```

#### Good

```go
// doc.go
// Package orders manages customer purchases, applying discounts and
// computing totals against a Customer's history.
package orders
```

```go
// order.go
package orders

type Order struct { ... }
```

### RULE go-doc/third-person-no-signature-repeat (SHOULD)

**Owner**: godoc-assistant
**Applies when**: a doc comment uses first-person ("I", "we", "our") OR repeats the function signature verbatim in the prose ("takes an `int` and returns a `string`" when the signature already says `func F(int) string`).
**Enforcement**: judgment (prose linters can flag first-person; signature-repeat is semantic and needs review)
**Trigger**: **/*.go
**Why**: First-person breaks the API documentation register — readers want a neutral spec, not the author's internal monologue. Signature-repeat is noise: the type checker already publishes the signature; the comment's job is the *behavior* the signature can't express (preconditions, side effects, error semantics, units).

#### Bad

```go
// I wrote this to take two ints and return their sum as an int.
// We use it in the totals calculator.
func Add(a, b int) int { ... }
```

#### Good

```go
// Add returns the sum of a and b. Overflow wraps per Go's int semantics;
// callers needing checked addition should use math/bits.
func Add(a, b int) int { ... }
```

---

## 🔍 Per Construct Guidelines

### Package Comments

- Should be in a `doc.go` file.
- Begin with `Package <name>` and describe the package's purpose.

```go
// Package calculator provides basic mathematical operations.
package calculator
```

---

### Function/Method Comments

- Start with the name of the function.
- Mention:
  - Purpose
  - Inputs and outputs (brief)
  - Side effects (if any)

```go
// Multiply returns the product of two integers.
func Multiply(a, b int) int
```

If there’s more complexity:

```go
// Merge combines two sorted slices into a single sorted slice.
// It assumes both inputs are sorted in ascending order.
func Merge(a, b []int) []int
```

---

### Struct and Interface Comments

- Explain the role of the struct/interface.

```go
// User represents a user in the system.
type User struct {
    ID    int
    Email string
}
```

---

### Constant and Variable Comments

- Use if the variable/const isn't self-explanatory.

```go
// MaxRetries defines the maximum number of retry attempts.
const MaxRetries = 3
```

---

## 🤖 Using LLMs to Improve Go Comments

An LLM like ChatGPT or Claude can help generate or refine Go doc strings by:

1. **Generating Initial Comments**
   - Paste the function/type and ask:  
     `"Write a Go-style doc comment for this function."`

2. **Reviewing for Clarity**
   - Ask:  
     `"Is this comment clear and idiomatic for Go documentation?"`

3. **Bulk Commenting**
   - Provide a full Go file and prompt:  
     `"Add idiomatic Go comments to all exported types and functions."`

4. **Maintaining Documentation**
   - Prompt it to:  
     `"Update the comments to reflect the latest code changes."`

> ⚠️ Always manually review LLM-generated comments for correctness.

---

## ✅ Summary Checklist

| Best Practice                             | Done? |
|------------------------------------------|-------|
| Starts with the name of the item         | ☐     |
| Uses full sentences                      | ☐     |
| Describes purpose and behavior clearly   | ☐     |
| Avoids redundancy with code              | ☐     |
| Written in third person                  | ☐     |
| Reviewed for clarity and accuracy        | ☐     |

---

## 📚 Resources

- [Effective Go – Commentary](https://golang.org/doc/effective_go#commentary)
- [`golint` rules on comments](https://github.com/golang/lint)
- [Godoc Documentation](https://pkg.go.dev/golang.org/x/tools/cmd/godoc)