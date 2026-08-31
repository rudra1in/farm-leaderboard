**Part 5 of 7 – Frontend (Astro) Setup + SSR/ISR Leaderboard Page**

Copy everything below this line.

---

### Frontend Setup

1. Create the frontend folder and scaffold Astro:
```bash
npm create astro@latest frontend
```

When prompted, choose:
- Template: `Empty` / `Minimal`
- Install dependencies: Yes
- TypeScript: Yes (recommended) or No
- Git: No (optional)

2. Move into the folder:
```bash
cd frontend
```

3. Add React support:
```bash
npx astro add react
```

Confirm all prompts with Yes.

4. Install any extra packages (optional but useful):
```bash
npm install
```

---

### File: `frontend/astro.config.mjs`

Replace the content with this (enables server-side rendering):

```js
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import node from '@astrojs/node';   // or vercel / netlify later

export default defineConfig({
  output: 'server',                 // Important for SSR
  adapter: node({
    mode: 'standalone'
  }),
  integrations: [react()],
  server: {
    port: 4321,
  },
  vite: {
    server: {
      proxy: {
        // Optional: proxy API calls during development
        // '/api': 'http://localhost:8000'
      }
    }
  }
});
```

> Note: If you don’t want the Node adapter yet, you can temporarily use `output: 'hybrid'`. For full SSR + ISR-style control we use `server`.

Install the Node adapter if it wasn’t added automatically:
```bash
npx astro add node
```

---

### File: `frontend/.env`

Create this file inside the `frontend` folder:

```env
PUBLIC_API_URL=http://localhost:8000
```

---

### File: `frontend/src/pages/leaderboard.astro`

This is the main page that demonstrates **SSR** (and can be extended to ISR-style revalidation).

```astro
---
// src/pages/leaderboard.astro
export const prerender = false;   // Force SSR on every request

const API_URL = import.meta.env.PUBLIC_API_URL || "http://localhost:8000";

const page = Number(Astro.url.searchParams.get("page") || 1);
const size = Number(Astro.url.searchParams.get("size") || 20);

let items = [];
let total = 0;
let links = {};
let error = null;

try {
  const res = await fetch(`${API_URL}/leaderboard?page=${page}&size=${size}`, {
    headers: {
      "Accept": "application/json"
    }
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  const data = await res.json();
  items = data.items || [];
  total = data.total || 0;
  links = data.links || {};
} catch (err) {
  error = err.message;
  console.error("Failed to load leaderboard:", err);
}

// Simple title
const title = `Leaderboard – Page ${page}`;
---

<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <style>
      body {
        font-family: system-ui, -apple-system, sans-serif;
        max-width: 900px;
        margin: 40px auto;
        padding: 0 20px;
        background: #0f172a;
        color: #e2e8f0;
      }
      h1 {
        margin-bottom: 8px;
      }
      .subtitle {
        color: #94a3b8;
        margin-bottom: 30px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        background: #1e293b;
        border-radius: 12px;
        overflow: hidden;
      }
      th, td {
        padding: 14px 18px;
        text-align: left;
      }
      th {
        background: #334155;
        font-weight: 600;
      }
      tr:nth-child(even) {
        background: #1e293b;
      }
      tr:nth-child(odd) {
        background: #0f172a;
      }
      .rank {
        font-weight: 700;
        color: #38bdf8;
      }
      .pagination {
        margin-top: 24px;
        display: flex;
        gap: 12px;
        align-items: center;
      }
      a {
        color: #38bdf8;
        text-decoration: none;
      }
      a:hover {
        text-decoration: underline;
      }
      .error {
        background: #7f1d1d;
        padding: 16px;
        border-radius: 8px;
      }
    </style>
  </head>

  <body>
    <h1>Leaderboard</h1>
    <p class="subtitle">SSR powered by Astro • Data from FastAPI + Redis</p>

    {error ? (
      <div class="error">
        <strong>Error loading leaderboard:</strong> {error}
      </div>
    ) : (
      <>
        <!-- React island for interactive features -->
        <LeaderboardTable client:load items={items} />

        <div class="pagination">
          {links.prev && <a href={links.prev}>← Previous</a>}
          <span>Page {page}</span>
          {links.next && <a href={links.next}>Next →</a>}
          <span style="margin-left: auto; color: #94a3b8;">
            Total players: {total}
          </span>
        </div>
      </>
    )}
  </body>
</html>

<script>
  // Optional: client-side refresh button logic can go here later
</script>
```

> Important: We still need the React component `LeaderboardTable`. That will come in **Part 6**.

---

### Quick Test (after Part 6)

Once the React component is added, run the frontend with:

```bash
npm run dev
```

Then open: http://localhost:4321/leaderboard

---

**End of Part 5**

Reply with **`next`** or **`part 6`** to receive the **React component** + final frontend pieces.