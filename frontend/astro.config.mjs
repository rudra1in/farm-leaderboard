// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
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

