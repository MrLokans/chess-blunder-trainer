import tseslint from 'typescript-eslint';
import { resolve } from 'path';

export default tseslint.config(
  tseslint.configs.strictTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        project: './tsconfig.json',
        tsconfigRootDir: resolve(import.meta.dirname),
      },
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/no-unsafe-assignment': 'error',
      '@typescript-eslint/no-unsafe-call': 'error',
      '@typescript-eslint/no-unsafe-member-access': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'prefer-const': ['error', { destructuring: 'all' }],
      'eqeqeq': ['error', 'always', { null: 'ignore' }],
      'no-var': 'error',
      'no-debugger': 'error',

      // Relaxed for test code — Playwright's API returns many union types
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',

      // UI text is translated (and the locale is a server-global setting), so
      // text locators break whenever the language or a label changes. Locate
      // by data-testid, id or data-value instead. Matching user *data* (e.g. a
      // username) with hasText is fine — disable the rule on that line.
      'no-restricted-syntax': ['error',
        {
          selector: "CallExpression[callee.property.name=/^getBy(Text|Label|Placeholder|Title|AltText)$/]",
          message: 'Locate by data-testid/id/data-value, not by translated text.',
        },
        {
          selector: "CallExpression[callee.property.name='getByRole'] ObjectExpression > Property[key.name='name']",
          message: 'getByRole with `name` matches translated text; use data-testid/id instead.',
        },
        {
          selector: "Property[key.name=/^has(Not)?Text$/]",
          message: 'hasText matches translated text; use data-testid/data-value (disable only for user data).',
        },
        {
          selector: "CallExpression[callee.property.name='locator'] > Literal[value=/(^|\\s|>)text=|:(has-)?text\\(/]",
          message: 'text= / :has-text() selectors match translated text; use data-testid/id instead.',
        },
      ],
    },
  },
  {
    ignores: ['.tmp/', 'test-results/', 'playwright-report/', 'node_modules/', 'eslint.config.ts'],
  },
);
