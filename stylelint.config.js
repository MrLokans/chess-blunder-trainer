/** @type {import('stylelint').Config} */
export default {
  plugins: ['stylelint-value-no-unknown-custom-properties'],
  rules: {
    'csstools/value-no-unknown-custom-properties': [
      true,
      { importFrom: ['blunder_tutor/web/static/css/tokens.css'] },
    ],
  },
};
