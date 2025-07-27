# Vue 3 + TypeScript Frontend Application Guide

This guide provides comprehensive patterns for building frontend applications using Vue 3 with TypeScript, based on Benjamin Borbe's development ecosystem standards.

## 1. Project Setup and Architecture

### Core Technology Stack

**Key Technologies:**
- **Vue 3** with Composition API and `<script setup>` syntax
- **TypeScript** with strict type checking
- **Vite** as build tool and development server
- **Vue Router** for client-side navigation
- **Vitest** + Vue Test Utils for testing
- **ESLint** with Vue and TypeScript rules

### Project Structure

```
src/
├── components/           # Reusable Vue components
├── pages/               # Route-specific page components  
├── lib/                 # TypeScript utilities and types
├── assets/              # Static assets (CSS, images)
├── plugins/             # Custom Vite/Vue plugins
├── router.ts            # Vue Router configuration
├── main.ts              # Application entry point
└── vite-env.d.ts        # Vite type declarations
```

**Key Points:**
- Components use PascalCase naming (e.g., `InvoiceComponent.vue`)
- Pages represent route destinations (e.g., `InvoiceListPage.vue`)
- Business logic and types go in `lib/` directory
- Maintain clear separation between components and pages

### Package.json Configuration

```json
{
  "name": "your-app",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "lint:analyse": "eslint src --ext .ts,.vue",
    "lint:fix": "eslint src --fix --ext .ts,.vue",
    "update": "npm-check-updates -u",
    "test": "vitest"
  },
  "dependencies": {
    "vue": "^3.5.17",
    "vue-router": "^4.5.1",
    "axios": "^1.10.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.0",
    "@vue/test-utils": "^2.4.6",
    "typescript": "~5.8.3",
    "vite": "^7.0.4",
    "vitest": "^3.2.4",
    "vue-tsc": "^3.0.1",
    "eslint": "^9.31.0",
    "eslint-plugin-vue": "^10.3.0",
    "@typescript-eslint/eslint-plugin": "^8.37.0"
  }
}
```

## 2. TypeScript Configuration

### tsconfig.json

```json
{
  "compilerOptions": {
    "types": ["vitest"],
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "allowJs": true,
    "esModuleInterop": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": [
    "src/**/*.ts",
    "src/**/*.tsx", 
    "src/**/*.vue"
  ]
}
```

**Critical Requirements:**
- Always enable `strict: true` for maximum type safety
- Include `noUnusedLocals` and `noUnusedParameters` for clean code
- Use `moduleResolution: "bundler"` for Vite compatibility

## 3. Vite Configuration

### vite.config.ts

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    chunkSizeWarningLimit: 1000,
    commonjsOptions: {
      requireReturnsDefault: true,
    },
  },
})
```

**Key Points:**
- Always include Vue plugin for `.vue` file processing
- Configure chunk size warnings for production builds
- Custom plugins can be added (see Invoice project example)

## 4. Application Entry Point

### main.ts

```typescript
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";

const app = createApp(App);
app.use(router);
app.mount("#app");
```

**Standard Pattern:**
- Create Vue app instance
- Register router and other plugins
- Mount to DOM element with ID "app"

## 5. Component Development Patterns

### Basic Component Structure

```vue
<script setup lang="ts">
import { ref, onMounted } from "vue";
import { PropType } from "vue";

// Props with TypeScript types
const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  data: {
    type: Object as PropType<YourDataType>,
    required: false,
  }
});

// Reactive state
const isLoading = ref(false);
const items = ref<YourItemType[]>([]);

// Lifecycle
onMounted(() => {
  loadData();
});

// Methods
async function loadData() {
  isLoading.value = true;
  try {
    // API call logic
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="component">
    <h1>{{ props.title }}</h1>
    <div v-if="isLoading">Loading...</div>
    <div v-else>
      <!-- Component content -->
    </div>
  </div>
</template>

<style scoped>
.component {
  /* Component-specific styles */
}
</style>
```

**Key Points:**
- Always use `<script setup lang="ts">` for Composition API
- Define props with TypeScript types using `PropType<T>`
- Use `ref()` for reactive primitive values
- Use `reactive()` for complex objects
- Always handle loading states in async operations

### Router Link Component Pattern

```vue
<script setup lang="ts">
const props = defineProps({
  to: {
    type: Object,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
});
</script>

<template>
  <router-link
    class="link"
    :to="props.to"
    :title="props.title"
  >
    <slot />
  </router-link>
</template>

<style scoped>
.link {
  /* Link styling */
}
</style>
```

**Usage Pattern:**
```vue
<LinkRouter
  :to="{ name: 'HomePage' }"
  title="Go to Home"
>
  Home
</LinkRouter>
```

## 6. TypeScript Type Definitions

### Interface Patterns

```typescript
// lib/types.ts
export interface User {
  id: string;
  name: string;
  email: string;
  createdAt: Date;
}

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface PageMeta {
  title: string;
  description?: string;
}
```

### Component Prop Types

```typescript
// lib/ComponentTypes.ts
import { PropType } from "vue";

export const StringProp = {
  type: String,
  required: true,
} as const;

export const OptionalStringProp = {
  type: String,
  required: false,
  default: "",
} as const;

export function TypedObjectProp<T>() {
  return {
    type: Object as PropType<T>,
    required: true,
  } as const;
}

export function OptionalTypedObjectProp<T>() {
  return {
    type: Object as PropType<T>,
    required: false,
  } as const;
}
```

## 7. Vue Router Configuration

### router.ts

```typescript
import { createRouter, createWebHistory } from "vue-router";
import HomePage from "./pages/HomePage.vue";
import UserListPage from "./pages/UserListPage.vue";
import UserDetailsPage from "./pages/UserDetailsPage.vue";

const routes = [
  {
    path: "/",
    name: "Home",
    component: HomePage,
  },
  {
    path: "/users",
    name: "UserList",
    component: UserListPage,
  },
  {
    path: "/users/:id",
    name: "UserDetails", 
    component: UserDetailsPage,
    props: true,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
```

**Key Points:**
- Use named routes for better maintainability
- Enable `props: true` for parameterized routes
- Use descriptive route names matching page components

## 8. API Integration Patterns

### API Service Structure

```typescript
// lib/ApiService.ts
import axios, { AxiosResponse } from "axios";

export interface ApiConfig {
  baseURL: string;
  timeout?: number;
}

export class ApiService {
  private client;

  constructor(config: ApiConfig) {
    this.client = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout || 10000,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  async get<T>(url: string): Promise<T> {
    const response: AxiosResponse<T> = await this.client.get(url);
    return response.data;
  }

  async post<T, R>(url: string, data: T): Promise<R> {
    const response: AxiosResponse<R> = await this.client.post(url, data);
    return response.data;
  }

  async put<T, R>(url: string, data: T): Promise<R> {
    const response: AxiosResponse<R> = await this.client.put(url, data);
    return response.data;
  }

  async delete<T>(url: string): Promise<T> {
    const response: AxiosResponse<T> = await this.client.delete(url);
    return response.data;
  }
}

// Create service instance
export const apiService = new ApiService({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
});
```

### Using API in Components

```vue
<script setup lang="ts">
import { ref, onMounted } from "vue";
import { apiService } from "../lib/ApiService";
import type { User } from "../lib/types";

const users = ref<User[]>([]);
const isLoading = ref(false);
const error = ref<string | null>(null);

onMounted(async () => {
  await loadUsers();
});

async function loadUsers() {
  isLoading.value = true;
  error.value = null;
  
  try {
    users.value = await apiService.get<User[]>("/users");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Unknown error";
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div>
    <div v-if="isLoading">Loading users...</div>
    <div v-else-if="error" class="error">Error: {{ error }}</div>
    <div v-else>
      <div v-for="user in users" :key="user.id">
        {{ user.name }} - {{ user.email }}
      </div>
    </div>
  </div>
</template>
```

## 9. Testing Patterns

### Component Testing with Vitest

```typescript
// components/UserCard.test.ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import UserCard from "./UserCard.vue";
import type { User } from "../lib/types";

describe("UserCard", () => {
  const mockUser: User = {
    id: "1",
    name: "John Doe",
    email: "john@example.com",
    createdAt: new Date("2023-01-01"),
  };

  it("renders user information correctly", () => {
    const wrapper = mount(UserCard, {
      props: {
        user: mockUser,
      },
    });

    expect(wrapper.text()).toContain("John Doe");
    expect(wrapper.text()).toContain("john@example.com");
  });

  it("emits edit event when edit button clicked", async () => {
    const wrapper = mount(UserCard, {
      props: {
        user: mockUser,
      },
    });

    await wrapper.find("[data-test='edit-button']").trigger("click");
    
    expect(wrapper.emitted("edit")).toBeTruthy();
    expect(wrapper.emitted("edit")![0]).toEqual([mockUser.id]);
  });
});
```

### vitest.config.ts

```typescript
import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
```

## 10. Build and Development Workflow

### Standard Development Commands

```bash
# Development
npm run dev          # Start development server
npm run build        # Production build
npm run preview      # Preview production build

# Code Quality
npm run lint:analyse # Analyze code with ESLint
npm run lint:fix     # Fix linting issues
npm run test         # Run tests

# Maintenance
npm run update       # Update dependencies
```

### ESLint Configuration

```javascript
// eslint.config.mjs
import js from "@eslint/js";
import vue from "eslint-plugin-vue";
import typescript from "@typescript-eslint/eslint-plugin";

export default [
  js.configs.recommended,
  ...vue.configs["flat/recommended"],
  {
    files: ["**/*.{ts,tsx,vue}"],
    languageOptions: {
      parser: "@typescript-eslint/parser",
    },
    plugins: {
      "@typescript-eslint": typescript,
    },
    rules: {
      "vue/multi-word-component-names": "off",
      "@typescript-eslint/no-unused-vars": "error",
    },
  },
];
```

## 11. Application Navigation Pattern

### Main App Component with Navigation

```vue
<script setup lang="ts">
import { onMounted, ref } from "vue";
import LinkRouter from "./components/LinkRouterComponent.vue";

const currentTime = ref("");

onMounted(() => {
  updateTime();
  setInterval(updateTime, 1000);
});

function updateTime() {
  currentTime.value = new Date().toISOString().split(".")[0].split("T")[1];
}
</script>

<template>
  <nav class="main-nav">
    <ul>
      <li>
        <LinkRouter :to="{ name: 'Home' }" title="Home">
          Home
        </LinkRouter>
      </li>
      <li>
        <LinkRouter :to="{ name: 'UserList' }" title="Users">
          Users
        </LinkRouter>
      </li>
      <li>
        <LinkRouter :to="{ name: 'Settings' }" title="Settings">
          Settings
        </LinkRouter>
      </li>
      <li class="time">{{ currentTime }}</li>
    </ul>
  </nav>
  <main>
    <router-view />
  </main>
</template>

<style scoped>
.main-nav ul {
  display: flex;
  list-style: none;
  padding: 0;
  margin: 0;
  background-color: #272c31;
  color: white;
}

.main-nav li {
  padding: 0.5rem 1rem;
}

.main-nav .time {
  margin-left: auto;
}
</style>
```

## 12. Custom Vite Plugins

### Example Custom Plugin

```typescript
// src/plugins/api-plugin.ts
import type { Plugin } from "vite";

export function apiPlugin(): Plugin {
  return {
    name: "api-plugin",
    configureServer(server) {
      server.middlewares.use("/api", (req, res, next) => {
        // Custom API middleware logic
        if (req.url?.startsWith("/api/data")) {
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ message: "Hello from custom plugin" }));
          return;
        }
        next();
      });
    },
  };
}
```

## 13. Common Antipatterns to Avoid

### DON'T: Mix Options API with Composition API

```vue
<!-- DON'T DO THIS -->
<script lang="ts">
export default {
  data() {
    return { count: 0 };
  },
  setup() {
    const message = ref("Hello");
    return { message };
  }
};
</script>

<!-- DO THIS instead -->
<script setup lang="ts">
import { ref } from "vue";

const count = ref(0);
const message = ref("Hello");
</script>
```

### DON'T: Use any type

```typescript
// DON'T DO THIS
const userData: any = await api.get("/user");

// DO THIS instead
interface User {
  id: string;
  name: string;
  email: string;
}

const userData: User = await api.get<User>("/user");
```

### DON'T: Ignore error handling

```vue
<!-- DON'T DO THIS -->
<script setup lang="ts">
const data = ref([]);

onMounted(async () => {
  data.value = await api.get("/data");
});
</script>

<!-- DO THIS instead -->
<script setup lang="ts">
const data = ref([]);
const error = ref<string | null>(null);
const isLoading = ref(false);

onMounted(async () => {
  isLoading.value = true;
  try {
    data.value = await api.get("/data");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Unknown error";
  } finally {
    isLoading.value = false;
  }
});
</script>
```

### DON'T: Create deep component hierarchies

```vue
<!-- DON'T DO THIS -->
<template>
  <div>
    <div>
      <div>
        <div>
          <UserInfo :user="user">
            <UserDetails :details="user.details">
              <UserAddress :address="user.details.address" />
            </UserDetails>
          </UserInfo>
        </div>
      </div>
    </div>
  </div>
</template>

<!-- DO THIS instead -->
<template>
  <UserCard :user="user" />
</template>
```

## 14. Integration with Benjamin Borbe's Ecosystem

### Git Workflow Integration

- Never add "Generated with Claude" in commit messages
- Follow existing commit message patterns in the project
- Use semantic versioning for releases
- Always run lint and build before commits

### Development Standards

- Use numbered options for user choices: "1. Component 2. Page 3. Utility"
- Maintain consistency with existing project structure
- Follow TypeScript strict mode requirements
- Integrate with existing development toolchain

This guide provides a foundation for building scalable, maintainable Vue 3 + TypeScript applications that integrate seamlessly with Benjamin Borbe's development ecosystem and coding standards.