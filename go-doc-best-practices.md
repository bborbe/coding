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