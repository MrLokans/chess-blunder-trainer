import { defineConfig } from 'vite';
import { resolve } from 'path';
import preact from '@preact/preset-vite';

export default defineConfig({
  root: resolve(__dirname),
  plugins: [preact()],
  resolve: {
    alias: {
      '@vendor/chessground': resolve(__dirname, '../blunder_tutor/web/static/vendor/chessground-10.0.2.min.js'),
    },
  },
  build: {
    outDir: resolve(__dirname, '../blunder_tutor/web/static/dist'),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        trainer: resolve(__dirname, 'src/trainer/index.tsx'),
        dashboard: resolve(__dirname, 'src/dashboard/index.tsx'),
        settings: resolve(__dirname, 'src/settings/index.tsx'),
        management: resolve(__dirname, 'src/management/index.tsx'),
        'import': resolve(__dirname, 'src/import/index.tsx'),
        setup: resolve(__dirname, 'src/setup/index.tsx'),
        starred: resolve(__dirname, 'src/starred/index.tsx'),
        'game-review': resolve(__dirname, 'src/game-review/index.tsx'),
        traps: resolve(__dirname, 'src/traps/index.tsx'),
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    origin: 'http://localhost:5173',
  },
});
