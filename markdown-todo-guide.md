# 📋 AI Instructions: Working with Markdown To-Dos

## ✅ Goal

Read, create, and update Markdown files using checkboxes to manage to-do items and their completion status. Use hierarchical task organization with numbered sections and nested subtasks for complex projects.

---

## 📝 1. Markdown Checkbox Format

### Basic Syntax

Markdown uses a special syntax for checkboxes:

```markdown
- [ ] This is an unchecked to-do item  
- [x] This is a checked (completed) to-do item
```

- A task starts with a bullet (`-` or `*`), followed by a space, then:
  - `[ ]` for **incomplete**
  - `[x]` for **complete** (lowercase `x`)

### Hierarchical Task Organization

For complex projects, use numbered sections with nested subtasks:

```markdown
- [x] 1.0 Project Setup and Configuration
  - [x] 1.1 Initialize project with required dependencies
  - [x] 1.2 Configure build system and development environment
  - [x] 1.3 Set up version control and branching strategy
  - [ ] 1.4 Create initial documentation structure

- [ ] 2.0 Core Feature Implementation
  - [ ] 2.1 Design system architecture and interfaces
  - [ ] 2.2 Implement data models and persistence layer
  - [ ] 2.3 Build business logic and service layer
  - [ ] 2.4 Create user interface components
```

**Key benefits of hierarchical organization:**
- Clear progress tracking at both project and task levels
- Easy identification of blocking dependencies
- Logical grouping of related work items
- Professional project management appearance

---

## 🔍 2. Parsing To-Dos

To read and extract tasks:

- Look for lines that match the pattern:
  - `- [ ]` → **To-Do**
  - `- [x]` → **Done**
- Parse nested structure with proper indentation (usually 2 spaces per level)
- Extract numerical identifiers (e.g., "1.0", "2.3") for hierarchical tracking
- Optionally extract the content after the checkbox as the task description

### Advanced Example:

```markdown
## Project: E-commerce Platform

### Relevant Files
- `src/models/` - Data models and database schemas
- `src/services/` - Business logic and API services  
- `src/components/` - React UI components
- `tests/` - Unit and integration tests

### Tasks

- [x] 1.0 Database and Models
  - [x] 1.1 Design database schema for products and users
  - [x] 1.2 Implement Product model with validation
  - [x] 1.3 Create User authentication model
  - [ ] 1.4 Add order history and shopping cart models

- [ ] 2.0 API Development
  - [ ] 2.1 Build RESTful endpoints for product catalog
  - [ ] 2.2 Implement user authentication and session management
  - [ ] 2.3 Create shopping cart and checkout API
  - [ ] 2.4 Add payment processing integration

- [ ] 3.0 Frontend Implementation
  - [ ] 3.1 Design responsive product listing pages
  - [ ] 3.2 Build shopping cart interface
  - [ ] 3.3 Implement user registration and login forms
  - [ ] 3.4 Create checkout flow with payment integration
```

---

## ✍️ 3. Creating To-Do Items

### Adding New Tasks

To add a new task:

- For simple lists: Append with unchecked checkbox syntax
- For hierarchical projects: Use proper numbering and indentation

```markdown
- [ ] New task description
```

### Adding Hierarchical Tasks

Follow the numbering pattern and maintain proper indentation:

```markdown
- [ ] 4.0 New Major Section
  - [ ] 4.1 First subtask of new section
  - [ ] 4.2 Second subtask with specific details
  - [ ] 4.3 Final subtask before section completion
```

**Best practices:**
- Place tasks in logical order of execution
- Use descriptive names that clearly indicate deliverables
- Group related work under numbered sections
- Include file references or technical details when helpful

---

## ✔️ 4. Marking To-Dos as Done

### Basic Completion

To mark a task as completed, replace `[ ]` with `[x]`:

**Before:**
```markdown
- [ ] Deploy update to production
```

**After:**
```markdown
- [x] Deploy update to production
```

### Hierarchical Completion

For nested tasks, mark subtasks complete first, then parent tasks:

**Before:**
```markdown
- [ ] 1.0 Setup Phase
  - [ ] 1.1 Install dependencies
  - [ ] 1.2 Configure environment
```

**After completing subtasks:**
```markdown
- [x] 1.0 Setup Phase
  - [x] 1.1 Install dependencies
  - [x] 1.2 Configure environment
```

**Important:** Only mark parent tasks complete when ALL subtasks are finished.

---

## 🔄 5. Updating and Maintaining

### Organization Principles

- **Maintain hierarchy:** Preserve numbered sections and proper indentation
- **Avoid duplicates:** Check existing tasks before adding new ones
- **Respect dependencies:** Complete prerequisite tasks before dependent ones
- **Update context:** Keep "Relevant Files" sections current with project changes

### Project Structure Maintenance

```markdown
## Relevant Files
- `package.json` - Dependencies and build scripts
- `src/config/` - Application configuration files
- `src/services/` - Business logic implementation
- `tests/` - Automated test suites

### Notes
- Use `npm run dev` for development server
- Run `npm run test` before committing changes
- Deploy with `npm run build && npm run deploy`
```

**Keep project context updated:**
- Add new important files as they're created
- Update notes with new commands or procedures
- Remove obsolete references and outdated information

---

## 🛠 6. Advanced Features

### Metadata and Context

Enhance tasks with additional information:

```markdown
- [ ] 2.3 Implement user authentication (@priority:high, due:Friday)
  - [ ] 2.3.1 Design JWT token strategy
  - [ ] 2.3.2 Build login/logout endpoints  
  - [ ] 2.3.3 Add password reset functionality
```

### Progress Tracking

Use completion percentages for major sections:

```markdown
- [x] 1.0 Database Setup (100% complete)
- [ ] 2.0 API Development (60% complete - 3/5 tasks done)
- [ ] 3.0 Frontend Implementation (0% complete)
```

### File and Technical References

Include specific file paths and technical details:

```markdown
- [ ] 3.2 Implement shopping cart in `src/components/Cart.tsx`
  - [ ] 3.2.1 Add cart state management with Redux
  - [ ] 3.2.2 Create add/remove item functionality
  - [ ] 3.2.3 Build cart summary and checkout button
```

**Key advantages of this approach:**
- Professional project management appearance
- Clear progress visibility for stakeholders  
- Logical work breakdown and dependency tracking
- Easy maintenance and updates throughout project lifecycle
