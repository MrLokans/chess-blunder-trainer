/** @type {import('stylelint').Config} */
export default {
  plugins: ['stylelint-value-no-unknown-custom-properties'],
  rules: {
    'csstools/value-no-unknown-custom-properties': [
      true,
      { importFrom: ['blunder_tutor/web/static/css/tokens.css'] },
    ],
    'color-no-hex': [
      true,
      {
        message:
          'Raw hex colors are banned outside tokens.css. Define a token in tokens.css and reference it via var().',
      },
    ],
    'declaration-property-value-disallowed-list': [
      { '/.*/': [/var\(\s*--space-\d/] },
      {
        message:
          'Legacy numeric spacing aliases (--space-N) are banned for new code. Use the semantic --s-* scale from tokens.css (--s-xs/--s-sm/--s-md/--s-lg/--s-xl/--s-2xl).',
      },
    ],
  },
  overrides: [
    {
      files: [
        'blunder_tutor/web/static/css/tokens.css',
        'blunder_tutor/web/static/css/chessground-theme.css',
      ],
      rules: {
        'color-no-hex': null,
      },
    },
  ],
};
