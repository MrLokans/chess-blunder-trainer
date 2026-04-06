import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  test: {
    root: resolve(__dirname),
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts'],
      exclude: ['src/vendor.d.ts', 'src/types/**'],
      thresholds: {
        statements: 70,
      },
    },
    setupFiles: ['tests/helpers/setup.ts'],
  },
});
