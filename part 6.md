**Part 6 of 7 – React Component + Remaining Frontend Files**

Copy everything below this line.

---

### 1. React Component

Create the folder and file:

```bash
mkdir -p src/components
```

Now create the file `src/components/LeaderboardTable.tsx` and paste this:

```tsx
import React from 'react';

interface LeaderboardItem {
  rank: number;
  user_id: string;
  points: number;
}

interface Props {
  items: LeaderboardItem[];
}

export default function LeaderboardTable({ items }: Props) {
  if (!items || items.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8' }}>
        No players on the leaderboard yet.
      </div>
    );
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>User ID</th>
          <th>Points</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={`${item.user_id}-${item.rank}`}>
            <td className="rank">#{item.rank}</td>
            <td>{item.user_id}</td>
            <td>{item.points.toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

---

### 2. Update `leaderboard.astro` (Important)

Open `src/pages/leaderboard.astro` and make sure you have this import at the top of the frontmatter (right after the `---`).

Replace the top part of the file with this improved version:

```astro
---
import LeaderboardTable from '../components/LeaderboardTable';

export const prerender = false;   // Force SSR

const API_URL = import.meta.env.PUBLIC_API_URL || "http://localhost:8000";

const page = Number(Astro.url.searchParams.get("page") || 1);
const size = Number(Astro.url.searchParams.get("size") || 20);

let items = [];
let total = 0;
let links = {};
let error = null;

try {
  const res = await fetch(`${API_URL}/leaderboard?page=${page}&size=${size}`);
  
  if (!res.ok) {
    throw new Error(`API returned ${res.status}`);
  }

  const data = await res.json();
  items = data.items || [];
  total = data.total || 0;
  links = data.links || {};
} catch (err: any) {
  error = err.message || "Unknown error";
  console.error(err);
}
---
```

(The rest of the HTML/CSS you already pasted in Part 5 can stay the same.)

---

### 3. Optional: Nice Index Page

Create `src/pages/index.astro`:

```astro
---
---

<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Leaderboard POC</title>
    <style>
      body {
        font-family: system-ui, sans-serif;
        background: #0f172a;
        color: #e2e8f0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100vh;
        margin: 0;
      }
      a {
        color: #38bdf8;
        font-size: 1.25rem;
        text-decoration: none;
        border: 1px solid #38bdf8;
        padding: 12px 24px;
        border-radius: 8px;
      }
      a:hover {
        background: #38bdf8;
        color: #0f172a;
      }
    </style>
  </head>
  <body>
    <h1>Leaderboard POC</h1>
    <p>Astro SSR + FastAPI + Redis + Kafka</p>
    <a href="/leaderboard">View Leaderboard →</a>
  </body>
</html>
```

---

### 4. Package.json scripts (optional check)

Make sure your `package.json` has at least:

```json
"scripts": {
  "dev": "astro dev",
  "build": "astro build",
  "preview": "astro preview"
}
```

---

**End of Part 6**

Just reply if you also need any other part again.