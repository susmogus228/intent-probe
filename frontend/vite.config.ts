import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: '127.0.0.1',
    proxy: {
      '/api': 'http://127.0.0.1:8771',
      '/docs': 'http://127.0.0.1:8771',
      '/openapi.json': 'http://127.0.0.1:8771',
    },
  },
  build: { outDir: 'dist', sourcemap: false },
});
