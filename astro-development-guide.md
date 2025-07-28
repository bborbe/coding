# Astro Development Guidelines

This document provides comprehensive guidance for building modern, performant websites and applications using Astro. These guidelines cover core development patterns, performance optimization, and AI integration strategies.

## 1. Project Setup and Configuration

### Project Creation

Use the modern Astro CLI to create new projects:

```bash
# Create a new project with npm
npm create astro@latest

# Create with pnpm (recommended)
pnpm create astro@latest

# Create with yarn
yarn create astro

# Create from template
pnpm create astro@latest --template blog
```

**Key points:**
- Always use `@latest` to get the most current version
- Choose package manager consistently across your development environment
- Use official templates for specific use cases (blog, portfolio, docs)

### Basic Configuration Structure

```javascript
// astro.config.mjs
import { defineConfig } from 'astro/config';

export default defineConfig({
  // Core configuration options
  root: '.',                    // Project root directory
  srcDir: './src',             // Source directory
  publicDir: './public',       // Static assets directory  
  outDir: './dist',           // Build output directory
  cacheDir: './node_modules/.astro', // Build cache directory
  
  // Build configuration
  build: {
    concurrency: 1,            // Pages to build in parallel
    inlineStylesheets: 'auto'  // CSS inlining strategy
  },
  
  // Development server
  server: {
    port: 4321,
    host: false
  }
});
```

### Project Structure

```
project-name/
├── public/                 # Static assets
│   ├── favicon.svg
│   └── robots.txt
├── src/
│   ├── components/         # Reusable components
│   │   ├── Header.astro
│   │   └── Button.jsx
│   ├── layouts/           # Page layouts
│   │   └── Layout.astro
│   ├── pages/             # File-based routing
│   │   ├── index.astro
│   │   └── about.astro
│   ├── content/           # Content collections
│   │   └── blog/
│   └── styles/            # Global styles
│       └── global.css
├── astro.config.mjs       # Astro configuration
├── package.json
└── tsconfig.json          # TypeScript configuration
```

**Key points:**
- Follow the conventional directory structure for consistency
- Use `src/components/` for reusable UI components
- Place static assets in `public/` directory
- Leverage file-based routing in `src/pages/`

## 2. Development Workflow

### Development Commands

```bash
# Start development server
pnpm run dev

# Build for production
pnpm run build

# Preview production build
pnpm run preview

# Type checking
pnpm run astro check
```

### TypeScript Configuration

```json
// tsconfig.json
{
  "extends": "astro/tsconfigs/base",
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "exactOptionalPropertyTypes": true
  }
}
```

**Key points:**
- Extend Astro's base TypeScript configuration
- Enable strict mode for better type safety
- Use `astro check` for type validation
- Configure your IDE for Astro file support

### Testing Setup

```javascript
// vitest.config.ts
/// <reference types="vitest" />
import { getViteConfig } from 'astro/config';

export default getViteConfig({
  test: {
    environment: 'happy-dom',
    globals: true
  }
});
```

**Key points:**
- Use Astro's `getViteConfig` helper for Vitest integration
- Configure appropriate test environment
- Set up testing for both components and utilities

## 3. Performance Optimization

### Build Optimization

```javascript
// astro.config.mjs
import { defineConfig } from 'astro/config';

export default defineConfig({
  build: {
    // Optimize concurrent builds (use carefully)
    concurrency: 2,
    
    // Control CSS inlining for performance
    inlineStylesheets: 'auto' // 'always' | 'auto' | 'never'
  },
  
  // Configure prefetching
  prefetch: {
    prefetchAll: true,
    defaultStrategy: 'viewport' // 'tap' | 'hover' | 'viewport' | 'load'
  }
});
```

### Streaming and Performance

```astro
---
// pages/optimized.astro
import SlowComponent from '../components/SlowComponent.astro';
import FastComponent from '../components/FastComponent.astro';
---
<html>
  <head>
    <title>Optimized Page</title>
  </head>
  <body>
    <!-- Fast content renders immediately -->
    <h1>Welcome</h1>
    <FastComponent />
    
    <!-- Slow content streams in when ready -->
    <SlowComponent />
  </body>
</html>
```

### Image Optimization

```javascript
// astro.config.mjs
import { defineConfig } from 'astro/config';

export default defineConfig({
  image: {
    // Use built-in Sharp service for optimization
    service: {
      entrypoint: 'astro/assets/services/sharp'
    },
    
    // Or use passthrough for no processing
    // service: passthroughImageService()
  }
});
```

**Key points:**
- Enable streaming for better perceived performance
- Use appropriate prefetch strategies based on user behavior
- Optimize images with Sharp or use passthrough when needed
- Monitor build concurrency to avoid memory issues

## 4. Integrations and Adapters

### Adding Integrations

```bash
# Add integrations automatically
pnpm astro add react
pnpm astro add mdx
pnpm astro add tailwind

# Add multiple integrations
pnpm astro add react mdx tailwind
```

### Manual Integration Configuration

```javascript
// astro.config.mjs
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import mdx from '@astrojs/mdx';

export default defineConfig({
  integrations: [
    react(),
    mdx({
      optimize: true,
      extendMarkdownConfig: false
    })
  ]
});
```

### Server-Side Rendering Setup

```javascript
// astro.config.mjs
import { defineConfig } from 'astro/config';
import node from '@astrojs/node';

export default defineConfig({
  output: 'server', // 'static' | 'server'
  adapter: node({
    mode: 'standalone' // 'middleware' | 'standalone'
  })
});
```

**Key points:**
- Use `astro add` for automatic integration setup
- Configure integrations based on specific project needs
- Choose appropriate output mode (static vs server)
- Select the right adapter for your deployment target

## 5. AI Integration Strategies

### Architecture Strategy

| AI Task Type | Execution Target | Astro Strategy |
|--------------|-------------------|----------------|
| Chatbots / LLMs | Server-Side (API call) | SSR or endpoints |
| Image generation | Server-Side or Edge | Astro endpoints + cache strategy |
| Content generation | Build-Time or SSR | Content pipeline + fetch |
| Personalization | Client or SSR | Cookies/localStorage + conditional UI |
| Search / Recommendations | Server or Client | Client:js integrations |

### Server-Side AI Integration

```javascript
// src/pages/api/chat.ts
import type { APIRoute } from 'astro';

export const POST: APIRoute = async ({ request }) => {
  try {
    const { messages } = await request.json();
    
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${import.meta.env.OPENAI_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'gpt-4',
        messages: messages
      })
    });
    
    const data = await response.json();
    
    return new Response(JSON.stringify({
      reply: data.choices[0].message.content
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: 'AI request failed' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
```

### Build-Time AI Content Generation

```astro
---
// src/pages/blog/[slug].astro
import { getCollection } from 'astro:content';

export async function getStaticPaths() {
  const posts = await getCollection('blog');
  
  return posts.map((post) => ({
    params: { slug: post.slug },
    props: { post }
  }));
}

const { post } = Astro.props;

// Generate AI intro at build time
async function generateIntro(content: string) {
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: 'gpt-4',
      messages: [{
        role: 'user',
        content: `Generate a compelling intro for this blog post: ${content.slice(0, 500)}`
      }]
    })
  });
  
  const data = await response.json();
  return data.choices[0].message.content;
}

const aiIntro = await generateIntro(post.body);
---

<html>
  <head>
    <title>{post.data.title}</title>
  </head>
  <body>
    <article>
      <h1>{post.data.title}</h1>
      <div class="ai-intro">{aiIntro}</div>
      <div class="content">
        <post.Content />
      </div>
    </article>
  </body>
</html>
```

### Client-Side AI Components

```jsx
// src/components/ChatBox.jsx
import { useState } from 'react';

export default function ChatBox() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages })
      });

      const data = await response.json();
      setMessages([...newMessages, { role: 'assistant', content: data.reply }]);
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-box">
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {loading && <div className="loading">AI is thinking...</div>}
      </div>
      
      <form onSubmit={sendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me anything..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>Send</button>
      </form>
    </div>
  );
}
```

```astro
---
// Using the AI component
import ChatBox from '../components/ChatBox.jsx';
---

<html>
  <head>
    <title>AI Chat Demo</title>
  </head>
  <body>
    <h1>AI Assistant</h1>
    <ChatBox client:load />
  </body>
</html>
```

**Key points:**
- Keep API keys server-side only using `import.meta.env`
- Use build-time generation for static AI content
- Implement proper error handling for AI API calls
- Add loading states for better user experience
- Use appropriate client directives (`client:load`, `client:visible`) for interactive components

## 6. Deployment and Production

### Environment Configuration

```bash
# .env
OPENAI_API_KEY=your-key-here
DATABASE_URL=your-database-url
SENTRY_DSN=your-sentry-dsn
```

```javascript
// astro.config.mjs
import { defineConfig } from 'astro/config';

export default defineConfig({
  // Environment-specific configuration
  vite: {
    define: {
      __BUILD_TIME__: JSON.stringify(new Date().toISOString())
    }
  }
});
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM node:lts AS runtime
WORKDIR /app

COPY . .
RUN npm install
RUN npm run build

ENV HOST=0.0.0.0
ENV PORT=4321
EXPOSE 4321
CMD node ./dist/server/entry.mjs
```

### Deployment Checklist

- [ ] API keys configured securely in production
- [ ] AI endpoints protected with rate limiting
- [ ] Error handling and fallbacks implemented
- [ ] Performance monitoring enabled
- [ ] Build optimization settings applied
- [ ] Content Security Policy configured
- [ ] SEO meta tags implemented

**Key points:**
- Never commit API keys to version control
- Use environment variables for all secrets
- Implement proper error boundaries for AI features
- Monitor API usage and costs
- Set up logging for production debugging

## 7. Common Antipatterns to Avoid

### DON'T: Mix AI API keys in client-side code

```javascript
// DON'T DO THIS - exposes API key
const response = await fetch('https://api.openai.com/v1/chat/completions', {
  headers: {
    'Authorization': `Bearer sk-your-api-key-here` // EXPOSED!
  }
});

// DO THIS instead - use server endpoints
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ message: userInput })
});
```

### DON'T: Block rendering with slow AI calls

```astro
---
// DON'T DO THIS - blocks entire page
const slowAIResult = await callExpensiveAI();
const anotherSlowCall = await anotherAI();
---

<html>
  <body>
    <h1>Page blocked until AI finishes</h1>
    <div>{slowAIResult}</div>
    <div>{anotherSlowCall}</div>
  </body>
</html>
```

```astro
---
// DO THIS instead - use streaming components
import SlowAIComponent from '../components/SlowAI.astro';
---

<html>
  <body>
    <h1>Page renders immediately</h1>
    <SlowAIComponent />
  </body>
</html>
```

### DON'T: Ignore error handling for AI features

```javascript
// DON'T DO THIS - no error handling
export const POST = async ({ request }) => {
  const data = await request.json();
  const aiResponse = await openai.chat.completions.create(data);
  return new Response(JSON.stringify(aiResponse));
};

// DO THIS instead - proper error handling
export const POST = async ({ request }) => {
  try {
    const data = await request.json();
    const aiResponse = await openai.chat.completions.create(data);
    return new Response(JSON.stringify(aiResponse));
  } catch (error) {
    console.error('AI API error:', error);
    return new Response(
      JSON.stringify({ error: 'AI service unavailable' }), 
      { status: 500 }
    );
  }
};
```

### DON'T: Use `output: 'server'` unnecessarily

```javascript
// DON'T DO THIS - forces SSR for static content
export default defineConfig({
  output: 'server', // Unnecessary for static sites
  adapter: node()
});

// DO THIS instead - use static when possible
export default defineConfig({
  output: 'static' // Better performance for static content
});
```

This documentation ensures consistent Astro development practices while enabling powerful AI integration capabilities within your development ecosystem.