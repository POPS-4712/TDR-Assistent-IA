const { text, cleanTitle, extractSeniority } = require('./normalize');

function normalizeInfoJobsLink(rawLink) {
  const value = text(rawLink);
  if (!value) return null;
  try {
    const url = new URL(value, 'https://www.infojobs.net');
    url.hostname = url.hostname.toLowerCase().replace(/^www\./, '');
    url.search = '';
    url.hash = '';
    url.pathname = url.pathname.replace(/\/+$/, '') || '/';
    return url.href;
  } catch {
    return value;
  }
}

function extractInfoJobsId(rawLink) {
  const link = text(rawLink);
  const queryId = link.match(/[?&](?:id|offerId|offer_id)=([A-Za-z0-9_-]+)/i);
  if (queryId) return queryId[1];
  const slugId = link.match(/\/of-([A-Za-z0-9_-]+)(?:[/?#]|$)/i);
  if (slugId) return slugId[1];
  const numericId = link.match(/(?:^|[/-])(\d{5,})(?:[/?#-]|$)/);
  return numericId ? numericId[1] : null;
}

function fallbackKey(job) {
  return [job.company, job.title, job.location]
    .map(value => text(value).toLocaleLowerCase().normalize('NFKC'))
    .join('|');
}

function identityKey(job) {
  return job.id ? `id:${job.id}` : job.link ? `url:${job.link}` : `fallback:${fallbackKey(job)}`;
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
  return raw[field].map(text).filter(Boolean)
    .filter((value, index, values) => values.indexOf(value) === index);
}

function normalizeInfoJobsJob(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const link = normalizeInfoJobsLink(raw.link);
  const id = text(raw.id) || extractInfoJobsId(link);
  const title = cleanTitle(raw.title);
  if (!title || (!id && !link && !raw.company && !raw.location)) return null;
  const searchQueries = [
    ...(Array.isArray(raw.searchQueries) ? raw.searchQueries : []),
    raw.searchQuery,
  ].map(text).filter(Boolean)
    .filter((value, index, values) => values.indexOf(value) === index);
  const closed = raw.closed === true || raw.isClosed === true || text(raw.status).toLowerCase() === 'closed';
  const normalized = {
    id: id || null,
    title,
    company: text(raw.company) || null,
    location: text(raw.location) || null,
    link,
    description: text(raw.description) || null,
    source: 'infojobs',
    ...(searchQueries.length ? { searchQueries } : {}),
    ...(closed ? { closed: true } : {}),
    scrapedAt: raw.scrapedAt || new Date().toISOString(),
  };
  for (const field of NULL_FIELDS) {
    normalized[field] = field === 'seniority' && raw[field] === undefined
      ? extractSeniority(raw) : optionalValue(raw, field);
  }
  for (const field of ARRAY_FIELDS) normalized[field] = optionalList(raw, field);
  return normalized;
}

module.exports = {
  normalizeInfoJobsLink,
  extractInfoJobsId,
  fallbackKey,
  identityKey,
  normalizeInfoJobsJob,
  normalizeJob: normalizeInfoJobsJob,
};
