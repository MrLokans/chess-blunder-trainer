import js from '@eslint/js';
import globals from 'globals';

export default [
  js.configs.recommended,
  {
    files: ['blunder_tutor/web/static/js/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        Chess: 'readonly',
        htmx: 'readonly',
        Chart: 'readonly',
        t: 'readonly',
        formatNumber: 'readonly',
        formatDate: 'readonly',
      },
    },
    rules: {
      'no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-undef': 'error',
      'no-constant-condition': 'warn',
      'no-debugger': 'error',
      'no-duplicate-case': 'error',
      'no-empty': ['error', { allowEmptyCatch: true }],
      'eqeqeq': ['error', 'always', { null: 'ignore' }],
      'no-var': 'error',
      'prefer-const': ['error', { destructuring: 'all' }],
      'no-throw-literal': 'error',
    },
  },
  {
    files: ['blunder_tutor/web/static/js/theme-loader.js', 'blunder_tutor/web/static/js/i18n.js'],
    languageOptions: {
      sourceType: 'script',
    },
  },
  {
    files: ['tests_fe/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.node,
        Chess: 'readonly',
      },
    },
  },
];
