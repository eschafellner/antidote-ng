import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/dist/' : '/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './frontend'),
    },
  },
  server: {
    port: 5173,
    origin: 'http://localhost:5173',
  },
  build: {
    outDir: 'static/dist',
    emptyOutDir: true,
    manifest: 'manifest.json',
    rollupOptions: {
      input: 'frontend/main.js',
      output: {
        manualChunks: {
          'vendor-core': ['vue', '@inertiajs/vue3', 'axios'],
          'vendor-tools': ['marked', 'sortablejs', 'vuedraggable'],
        },
      },
    },
  },
}));
