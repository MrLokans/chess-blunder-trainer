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
      {
        '/.*/': [
          /var\(\s*--space-\d/,
          /var\(\s*--(?:red|blue|yellow|black|white|warm-gray|mid-gray(?:-light)?|dark-gray|correct)\b/,
        ],
      },
      {
        message:
          'Themeable components must use semantic tokens, not structural color primitives. Use --surface, --text, --border, --accent, or a semantic state token.',
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
        'declaration-property-value-disallowed-list': null,
      },
    },
  ],
};
