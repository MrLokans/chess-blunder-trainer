// Minimal ICU MessageFormat client for plural + simple placeholders
// Reads from window.__i18n__ (flat key→message dict) and window.__locale__

const PLURAL_RULES = {
  en: (n) => n === 1 ? 'one' : 'other',
  ru: (n) => {
    const m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return 'one';
    if (m10 >= 2 && m10 <= 4 && !(m100 >= 12 && m100 <= 14)) return 'few';
    if (m10 === 0 || (m10 >= 5 && m10 <= 9) || (m100 >= 11 && m100 <= 14)) return 'many';
    return 'other';
  },
  uk: (n) => {
    const m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return 'one';
    if (m10 >= 2 && m10 <= 4 && !(m100 >= 12 && m100 <= 14)) return 'few';
    if (m10 === 0 || (m10 >= 5 && m10 <= 9) || (m100 >= 11 && m100 <= 14)) return 'many';
    return 'other';
  },
  de: (n) => n === 1 ? 'one' : 'other',
  fr: (n) => (n === 0 || n === 1) ? 'one' : 'other',
  es: (n) => n === 1 ? 'one' : 'other',
  pl: (n) => {
    if (n === 1) return 'one';
    const m10 = n % 10, m100 = n % 100;
    if (m10 >= 2 && m10 <= 4 && !(m100 >= 12 && m100 <= 14)) return 'few';
    return 'many';
  },
};

const PLURAL_RE = /\{(\w+),\s*plural,\s*((?:[^{}]*\{[^{}]*\})*[^{}]*)\}/g;
const BRANCH_RE = /(\w+|=\d+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)}/g;
const PLACEHOLDER_RE = /\{(\w+)\}/g;

function resolvePlural(message, params, locale) {
  return message.replace(PLURAL_RE, (_, varName, branchesStr) => {
    const count = Number(params[varName]) || 0;
    const branches = {};
    let m;
    BRANCH_RE.lastIndex = 0;
    while ((m = BRANCH_RE.exec(branchesStr)) !== null) {
      branches[m[1]] = m[2];
    }
    const exact = '=' + Math.floor(count);
    if (branches[exact]) return branches[exact].replace(/#/g, String(count));
    const rule = PLURAL_RULES[locale] || PLURAL_RULES.en;
    const cat = rule(Math.floor(count));
    const text = branches[cat] || branches['other'] || '';
    return text.replace(/#/g, String(count));
  });
}

function resolvePlaceholders(message, params) {
  return message.replace(PLACEHOLDER_RE, (match, key) =>
    Object.prototype.hasOwnProperty.call(params, key) ? String(params[key]) : match
  );
}

window.t = function(key, params) {
  const dict = window.__i18n__ || {};
  let message = dict[key];
  if (message === undefined) return key;
  if (!params) return message;
  const locale = window.__locale__ || 'en';
  message = resolvePlural(message, params, locale);
  message = resolvePlaceholders(message, params);
  return message;
};

window.formatNumber = function(n, opts) {
  const locale = window.__locale__ || 'en';
  return new Intl.NumberFormat(locale, opts).format(n);
};

window.formatDate = function(d, style) {
  const locale = window.__locale__ || 'en';
  const date = d instanceof Date ? d : new Date(d);
  return new Intl.DateTimeFormat(locale, style).format(date);
};
