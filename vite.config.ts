import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Optional private remote access (e.g. a tailnet URL). Same variable the API reads:
// COLLAGE_ALLOWED_ORIGINS=https://machine.tailnet.ts.net:8446
const allowedHosts = (process.env.COLLAGE_ALLOWED_ORIGINS ?? '').split(',').flatMap((origin) => {
  try { return origin.trim() ? [new URL(origin.trim()).hostname] : []; } catch { return []; }
});

export default defineConfig({
  plugins: [react()],
  server: { allowedHosts, proxy: { '/api': 'http://127.0.0.1:8765' } },
  preview: { allowedHosts },
});
