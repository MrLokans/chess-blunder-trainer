import tseslint from 'typescript-eslint';
import vitest from 'eslint-plugin-vitest';
import reactHooks from 'eslint-plugin-react-hooks';
import { resolve } from 'path';

const allPageModules = [
  'trainer', 'dashboard', 'settings', 'game-review', 'management',
  'import', 'setup', 'starred', 'traps', 'heatmap', 'growth', 'profiles',
];

function crossPageRestrictions(): Array<Record<string, unknown>> {
  return allPageModules.map(mod => ({
    files: [`src/${mod}/**/*.{ts,tsx}`],
    rules: {
      'no-restricted-imports': ['error', {
        patterns: [{
          group: allPageModules.filter(m => m !== mod).map(m => `../${m}/*`),
          message: 'Page modules cannot import from other page modules. Move shared code to shared/.',
        }],
      }],
    },
  }));
}

export default tseslint.config(
  tseslint.configs.strictTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        project: './tsconfig.eslint.json',
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
      'no-restricted-globals': ['error',
        { name: 'process', message: 'Use import.meta.env for env vars.' },
      ],
      'no-restricted-imports': ['error', {
        paths: [
          { name: 'chart.js', message: 'Chart is a global from vendor. Use window.Chart.' },
        ],
        patterns: [
          { group: ['node:*'], message: 'Node.js APIs not available in browser.' },
        ],
      }],
      'prefer-const': ['error', { destructuring: 'all' }],
      'eqeqeq': ['error', 'always', { null: 'ignore' }],
      'no-var': 'error',
      'no-throw-literal': 'error',
      'no-debugger': 'error',
    },
  },
  ...crossPageRestrictions(),
  {
    files: ['**/*.tsx'],
    plugins: { 'react-hooks': reactHooks },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
  {
    files: ['**/*.tsx'],
    ignores: ['**/components/Button.tsx'],
    rules: {
      'no-restricted-syntax': ['error',
        {
          selector: 'JSXAttribute[name.name=/^(class|className)$/] Literal[value=/btn-(primary|secondary|danger|ghost)|(^|\\s)btn /]',
          message: 'Do not hand-roll button classes (btn / btn-primary / btn-secondary / btn-danger / btn-ghost). Use the <Button> component from components/Button. For a genuine styled <a> or a variant Button lacks, add an eslint-disable-next-line no-restricted-syntax with a reason.',
        },
        {
          selector: 'JSXAttribute[name.name=/^(class|className)$/] TemplateElement[value.raw=/btn-(primary|secondary|danger|ghost)|(^|\\s)btn /]',
          message: 'Do not hand-roll button classes (btn / btn-primary / btn-secondary / btn-danger / btn-ghost). Use the <Button> component from components/Button. For a genuine styled <a> or a variant Button lacks, add an eslint-disable-next-line no-restricted-syntax with a reason.',
        },
      ],
    },
  },
  {
    files: ['tests/**/*.test.{ts,tsx}'],
    plugins: { vitest },
    rules: {
      'vitest/expect-expect': 'error',
      'vitest/no-focused-tests': 'error',
      'vitest/no-conditional-expect': 'error',
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unsafe-call': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
    },
  },
  {
    ignores: ['dist/**'],
  },
);
