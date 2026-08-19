const path = require('path');
const { SEARCH_TERMS, INCLUDE, EXCLUDE } = require('./config');

const ROOT = __dirname;

function number(value, fallback, min = 1) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= min ? parsed : fallback;
}

function list(value, fallback) {
  if (!value) return fallback.slice();
  return String(value).split(',').map(item => item.trim()).filter(Boolean);
}

function loadInfoJobsConfig(overrides = {}) {
  const valueOrEnv = (key, envKey) => overrides[key] !== undefined ? overrides[key] : process.env[envKey];
  return {
    source: 'infojobs',
    outputFile: valueOrEnv('outputFile', 'INFOJOBS_OUTPUT_FILE') || path.join(ROOT, 'infojobs-jobs.json'),
    historyFile: valueOrEnv('historyFile', 'INFOJOBS_HISTORY_FILE') || path.join(ROOT, 'infojobs-history.json'),
    debugDir: valueOrEnv('debugDir', 'INFOJOBS_DEBUG_DIR') || path.join(ROOT, 'output', 'infojobs'),
    location: valueOrEnv('location', 'INFOJOBS_LOCATION') || 'Barcelona',
    terms: Array.isArray(overrides.terms) && overrides.terms.length
      ? overrides.terms : list(process.env.INFOJOBS_SEARCH_TERMS, SEARCH_TERMS),
    include: overrides.include || INCLUDE,
    exclude: overrides.exclude || EXCLUDE,
    termsPerQuery: number(valueOrEnv('termsPerQuery', 'INFOJOBS_TERMS_PER_QUERY'), 6),
    maxJobsPerSearch: number(valueOrEnv('maxJobsPerSearch', 'INFOJOBS_MAX_JOBS_PER_SEARCH'), 60),
    maxScrollSteps: number(valueOrEnv('maxScrollSteps', 'INFOJOBS_MAX_SCROLL_STEPS'), 4, 0),
    gotoTimeout: number(valueOrEnv('gotoTimeout', 'INFOJOBS_GOTO_TIMEOUT'), 30000),
    selectorTimeout: number(valueOrEnv('selectorTimeout', 'INFOJOBS_SELECTOR_TIMEOUT'), 10000),
    diagnosticsTimeout: number(valueOrEnv('diagnosticsTimeout', 'INFOJOBS_DIAGNOSTICS_TIMEOUT'), 5000),
    robotsTimeout: number(valueOrEnv('robotsTimeout', 'INFOJOBS_ROBOTS_TIMEOUT'), 10000),
    headless: overrides.headless !== undefined
      ? overrides.headless : process.env.PLAYWRIGHT_HEADLESS !== 'false',
    searchUrl: valueOrEnv('searchUrl', 'INFOJOBS_SEARCH_URL')
      || 'https://www.infojobs.net/jobsearch/search-results/list.xhtml',
    robotsUrl: valueOrEnv('robotsUrl', 'INFOJOBS_ROBOTS_URL')
      || 'https://www.infojobs.net/robots.txt',
  };
}

module.exports = { loadInfoJobsConfig, loadConfig: loadInfoJobsConfig };
