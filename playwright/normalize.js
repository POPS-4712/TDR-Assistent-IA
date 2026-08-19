function text(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function cleanTitle(raw) {
  const value = text(raw);
  const half = value.length / 2;
  return Number.isInteger(half) && value.slice(0, half) === value.slice(half)
    ? value.slice(0, half).trim() : value;
}

function extractJobId(link) {
  const match = text(link).match(/(?:-|%2D|\/view\/)(\d+)(?:[/?]|$)/i);
  return match ? match[1] : null;
}

function normalizeLink(rawLink) {
  const value = text(rawLink);
  if (!value) return null;
  try {
    const url = new URL(value, 'https://www.linkedin.com');
    url.hostname = url.hostname.toLowerCase().replace(/^www\./, '');
    url.search = '';
    url.hash = '';
    url.pathname = url.pathname.replace(/\/+$/, '') || '/';
    return url.href;
  } catch {
    return value;
  }
}

function fallbackKey(job) {
  return [job.company, job.title, job.location]
    .map(value => text(value).toLocaleLowerCase().normalize('NFKC'))
    .join('|');
}

function identityKey(job) {
  return job.id ? `id:${job.id}` : job.link ? `url:${job.link}` : `fallback:${fallbackKey(job)}`;
}

function extractSeniority(raw) {
  const value = text(`${raw.title || ''} ${raw.description || ''}`).toLowerCase();
  if (/\b(intern|internship|becario|prácticas|practicas|trainee)\b/.test(value)) return 'intern';
  if (/\b(junior|jr\.?|entry[- ]level)\b/.test(value)) return 'junior';
  if (/\b(senior|sr\.?|lead|principal|staff)\b/.test(value)) return 'senior';
  if (/\b(manager|director|head of|responsable)\b/.test(value)) return 'manager';
  return null;
}

const NULL_FIELDS = ['seniority', 'salary', 'remote', 'hybrid', 'contractType', 'employmentType',
  'industry', 'companyUrl', 'applicationUrl'];
const ARRAY_FIELDS = ['skills', 'requirements', 'education', 'languages', 'experience', 'detectedKeywords'];

function optionalValue(raw, field) {
  if (raw[field] === null || raw[field] === undefined || raw[field] === '') return null;
  return typeof raw[field] === 'string' ? text(raw[field]) || null : raw[field];
}

function optionalList(raw, field) {
  if (!Array.isArray(raw[field])) return [];
  return raw[field].map(text).filter(Boolean).filter((value, index, values) => values.indexOf(value) === index);
}

function normalizeJob(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const link = normalizeLink(raw.link);
  const id = text(raw.id) || extractJobId(link);
  const title = cleanTitle(raw.title);
  if (!title || (!id && !link && !raw.company && !raw.location)) return null;
  const searchQueries = [
    ...(Array.isArray(raw.searchQueries) ? raw.searchQueries : []),
    raw.searchQuery,
  ].map(text).filter(Boolean).filter((value, index, values) => values.indexOf(value) === index);
  const closed = raw.closed === true || raw.isClosed === true || text(raw.status).toLowerCase() === 'closed';
  const normalized = {
    id: id || null,
    title,
    company: text(raw.company) || null,
    location: text(raw.location) || null,
    link,
    description: text(raw.description) || null,
    source: text(raw.source) || 'linkedin',
    ...(searchQueries.length ? { searchQueries } : {}),
    ...(closed ? { closed: true } : {}),
    scrapedAt: raw.scrapedAt || new Date().toISOString(),
  };
  for (const field of NULL_FIELDS) {
    normalized[field] = field === 'seniority' && raw[field] === undefined
      ? extractSeniority(raw)
      : optionalValue(raw, field);
  }
  for (const field of ARRAY_FIELDS) normalized[field] = optionalList(raw, field);
  return normalized;
}

module.exports = {
  text, cleanTitle, extractJobId, normalizeLink, fallbackKey, identityKey, extractSeniority, normalizeJob,
};
