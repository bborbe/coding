🧠 Astro + AI Integration Playbook

📌 Goal

Build performant, SEO-friendly, modern websites or apps using Astro that incorporate AI capabilities such as:
	•	LLM-based chat
	•	Content generation
	•	Personalization
	•	Image generation
	•	AI-based search or recommendations

⸻

1. ⚙️ Architecture Strategy

✅ Choose AI Workload Type

AI Task Type	Execution Target	Astro Strategy
Chatbots / LLMs	Server-Side (API call)	SSR or endpoints
Image generation	Server-Side or Edge	Astro endpoints + cache or CDN strategy
Content generation	Build-Time or SSR	Use Astro content pipeline + fetch
Personalization	Client or SSR	Use cookies/localStorage + conditional UI
Search / Recommendations	Server or Client	Combine Astro with client:js integrations


⸻

2. 📦 Project Setup

npm create astro@latest
npm install openai dotenv axios

File Structure Example

/src
  /components
  /pages
  /lib             ← your API clients
  /layouts
  /routes/api      ← AI endpoints
.env


⸻

3. 🔐 Secrets & Environment Setup

In .env:

OPENAI_API_KEY=your-key

In astro.config.mjs:

import { defineConfig } from 'astro/config';
export default defineConfig({
  experimental: {
    assets: true,
  }
});

Use secrets only in server.ts or Astro endpoints.

⸻

4. 🧱 AI API Integration Patterns

a) Server-side LLM (chatbot)

Create an API endpoint:

// src/routes/api/chat.ts
import { OpenAI } from 'openai';

export async function POST({ request }) {
  const body = await request.json();
  const openai = new OpenAI({ apiKey: import.meta.env.OPENAI_API_KEY });

  const res = await openai.chat.completions.create({
    model: 'gpt-4',
    messages: body.messages,
  });

  return new Response(JSON.stringify({ reply: res.choices[0].message.content }), {
    headers: { 'Content-Type': 'application/json' }
  });
}

Then call it from your frontend via fetch('/api/chat').

⸻

b) AI at Build Time

Example: Generate blog intros with OpenAI during getStaticPaths

// src/pages/blog/[slug].astro
const post = await fetchPost(slug);
const aiIntro = await generateIntro(post.content); // OpenAI call


⸻

5. 🧑‍🎨 UI Integration Patterns

a) Interactive AI Component

Use client:load or client:visible to mount a React/Svelte component that talks to the API:

---
// in .astro file
import ChatBox from '../components/ChatBox.jsx';
---
<ChatBox client:visible />

b) Generated Content

Render server-side or build-time AI-generated content directly into the HTML.

⸻

6. ⚡ Performance & SEO

Concern	Strategy
Latency	Use streaming (where possible) or caching
SEO (static content)	Use AI at build time (SSG)
Payload size	Lazy-load AI components (client:*)
Privacy	Keep API keys server-side only


⸻

7. 🧪 Testing & Evaluation
	•	Use mock APIs in dev to avoid hitting real API quota.
	•	Validate output for hallucination or bad content.
	•	Log token usage to optimize prompts and cost.

⸻

8. 🚀 Deployment Checklist
	•	Astro deployed (e.g. Vercel, Netlify, or custom Node/Edge)
	•	AI endpoints protected (e.g. rate limiting, logging)
	•	API keys set securely in production
	•	UI fallbacks for API errors

⸻

🔧 Bonus Tips
	•	Use LangChain if chaining tools, memory, or RAG.
	•	Use Zod to validate AI input/output.
	•	Add loading indicators to AI UI elements.
	•	Use client:media to only load AI UI when needed.

