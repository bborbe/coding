# 🧪 AI TDD Development Guide

This guide enables an AI agent to develop features using **Test-Driven Development (TDD)**. It emphasizes correctness, maintainability, and minimal code design.

---

## ✅ Step 1: Verify Current Functionality

1. **Identify existing functionality.**
2. **Write test cases** that verify how the current system behaves.
3. **Run the tests** to ensure that the current functionality is fully covered and passes.

💡 *Purpose:* Ensure a clean test baseline and guard against regressions during development.

---

## ➕ Step 2: Add Test for New Functionality

1. **Understand the new feature or behavior.**
2. **Write a failing test** that describes the expected outcome of the new functionality.
3. Do **not** implement the new functionality yet.

🟥 *Red phase:* This test must fail because the feature is not yet implemented.

---

## 🛠️ Step 3: Implement the New Functionality

1. **Write the minimal code** necessary to make the new test pass.
2. Keep the implementation as simple as possible—refactor later.

🟩 *Green phase:* Run the test suite. The new test should now pass.

---

## 🔁 Step 4: Refactor and Clean Up

1. **Refactor the implementation** to improve structure, readability, and efficiency.
2. **Ensure all tests still pass** after refactoring.

⚪ *Refactor phase:* Improve code without changing behavior.

---

## 🔄 Step 5: Repeat

- For every new piece of functionality:
  - Add a new failing test.
  - Implement just enough code to make it pass.
  - Refactor.

---

## 🧠 Notes for the AI Agent

- **Always run the full test suite** after each change.
- **Do not skip writing tests**—they define the behavior.
- **Use descriptive test names** to explain the feature or expected outcome.
- **Avoid writing unnecessary code**—let tests guide development.
