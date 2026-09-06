import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: resolve(__dirname),
  publicDir: false,
  build: {
    outDir: resolve(__dirname, '../blunder_tutor/web/static/js'),
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, 'src/global/theme-loader.ts'),
      formats: ['iife'],
      name: 'ThemeLoader',
      fileName: () => 'theme-loader.js',
    },
  },
});
