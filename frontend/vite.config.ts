import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

/**
 * Three entry points, one repository (lld-frontend.md §4).
 *
 * The point of separate entries is that a customer downloads the assistant bundle only
 * — never the agent console or the curation console. That is the largest single
 * performance win available and it is free; §3's bundle budgets depend on it.
 */
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': resolve(__dirname, 'src') } },
  build: {
    rollupOptions: {
      input: {
        assistant: resolve(__dirname, 'assistant.html'),
        agent: resolve(__dirname, 'agent.html'),
        curation: resolve(__dirname, 'curation.html'),
      },
    },
  },
  server: {
    // The API lives on a different origin permanently (AS-F4). Proxying in dev keeps
    // that fact visible rather than papering over it with same-origin assumptions that
    // would break in production.
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
  test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'], globals: true },
})
