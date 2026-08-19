const path = require('path');

const ROOT = __dirname;
const number = (value, fallback, min = 1) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= min ? parsed : fallback;
};
const list = (value, fallback) => {
  if (!value) return fallback.slice();
  return String(value).split(',').map(item => item.trim()).filter(Boolean);
};

const SEARCH_TERMS = [
  'Project Manager', 'Program Manager', 'PMO', 'Business Analyst',
  'Operations Manager', 'Continuous Improvement', 'Operational Excellence',
  'Lean', 'Industrial Engineer', 'Supply Chain', 'Business Intelligence',
  'Strategy', 'Digital Transformation', 'Innovation', 'Consultant',
  'Product Manager', 'Change Management',
];

const INCLUDE = [
  'project manager', 'program manager', 'pmo', 'business analyst', 'operations',
  'process', 'continuous improvement', 'lean', 'operational excellence',
  'industrial engineer', 'supply chain', 'logistics', 'digital transformation',
  'innovation', 'consultant', 'strategy', 'business intelligence', 'data analyst',
  'product manager', 'product owner', 'planning', 'planner', 'manufacturing excellence',
  'operations manager', 'project engineer', 'program management', 'transformation',
  'change management', 'industrialization', 'performance', 'production planning',
  's&op', 'planning engineer', 'business process', 'industrial performance',
  'operations excellence', 'manufacturing engineer', 'engineering manager',
];
const EXCLUDE = [
  'mecánico', 'mechanical', 'eléctrico', 'electrical', 'electrónico', 'electronics',
  'embedded', 'firmware', 'climatización', 'climatizacion', 'hvac',
  'electromecánico', 'electromecanico', 'robotics', 'automation engineer',
  'validation', 'testing', 'qa engineer', 'electronic', 'electrical design',
  'mechanical design', 'cad', 'solidworks', 'catia', 'nx', 'plc', 'scada',
  'instrumentación', 'civil', 'obras', 'instalaciones', 'peritajes', 'patentes',
  'homologaciones', 'mantenimiento', 'ferroviario', 'automoción', 'automocion',
];

function loadConfig(overrides = {}) {
  const valueOrEnv = (key, envKey) => overrides[key] !== undefined ? overrides[key] : process.env[envKey];
  return {
    storageState: valueOrEnv('storageState', 'LINKEDIN_STORAGE_STATE') || path.join(ROOT, 'linkedin.json'),
    outputFile: valueOrEnv('outputFile', 'SCRAPER_OUTPUT_FILE') || path.join(ROOT, 'jobs.json'),
    debugDir: valueOrEnv('debugDir', 'SCRAPER_DEBUG_DIR') || path.join(ROOT, 'output'),
    historyFile: valueOrEnv('historyFile', 'SCRAPER_HISTORY_FILE') || path.join(ROOT, 'jobs-history.json'),
    location: valueOrEnv('location', 'LINKEDIN_LOCATION') || 'Barcelona Metropolitan Area',
    terms: Array.isArray(overrides.terms) && overrides.terms.length ? overrides.terms : list(process.env.LINKEDIN_SEARCH_TERMS, SEARCH_TERMS),
    include: overrides.include || INCLUDE,
    exclude: overrides.exclude || EXCLUDE,
    termsPerQuery: number(valueOrEnv('termsPerQuery', 'TERMS_PER_QUERY'), 6),
    maxJobsPerSearch: number(valueOrEnv('maxJobsPerSearch', 'MAX_JOBS_PER_SEARCH'), 60),
    maxScrollSteps: number(valueOrEnv('maxScrollSteps', 'MAX_SCROLL_STEPS'), 4, 0),
    gotoTimeout: number(valueOrEnv('gotoTimeout', 'GOTO_TIMEOUT'), 30000),
    selectorTimeout: number(valueOrEnv('selectorTimeout', 'SELECTOR_TIMEOUT'), 10000),
    diagnosticsTimeout: number(valueOrEnv('diagnosticsTimeout', 'DIAGNOSTICS_TIMEOUT'), 5000),
    headless: overrides.headless !== undefined ? overrides.headless : process.env.PLAYWRIGHT_HEADLESS !== 'false',
  };
}

module.exports = { loadConfig, SEARCH_TERMS, INCLUDE, EXCLUDE };
