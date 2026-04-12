import { defineConfig } from 'vitest/config';
import { resolve } from 'path';
import preact from '@preact/preset-vite';

export default defineConfig({
  plugins: [preact()],
  resolve: {
    alias: {
      '@vendor/chessground': resolve(__dirname, '../blunder_tutor/web/static/vendor/chessground-10.0.2.min.js'),
    },
  },
  test: {
    root: resolve(__dirname),
    environment: 'jsdom',
    include: ['tests/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/vendor.d.ts', 'src/types/**'],
      thresholds: {
        statements: 70,
      },
    },
    setupFiles: ['tests/helpers/setup.ts'],
  },
});
