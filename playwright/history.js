const fs = require('fs/promises');
const { identityKey, normalizeJob } = require('./normalize');

async function readHistory(file) {
  try {
    const contents = await fs.readFile(file, 'utf8');
    const parsed = JSON.parse(contents.replace(/^\uFEFF/, ''));
    const jobs = Array.isArray(parsed) ? parsed : (Array.isArray(parsed.jobs) ? parsed.jobs : []);
    return jobs.filter(job => job && (job.id || job.link || job.title)).map(job => {
      const normalized = normalizeJob(job);
      return normalized ? { ...job, ...normalized } : { ...job };
    });
  } catch (error) {
    if (error.code === 'ENOENT') return [];
    throw new Error(`Histórico inválido (${file}): ${error.message}`);
  }
}

async function mergeHistory(file, current) {
  const previous = await readHistory(file);
  const now = new Date().toISOString();
  const merged = new Map(previous.map(job => [identityKey(job), job]));
  const currentKeys = new Set();
  for (const job of current) {
    const normalized = normalizeJob(job) || job;
    const key = identityKey(normalized);
    currentKeys.add(key);
    const old = merged.get(key);
    const changedFields = ['title', 'company', 'location', 'link', 'description', 'source', 'seniority', 'salary',
      'remote', 'hybrid', 'contractType', 'employmentType', 'industry', 'companyUrl', 'applicationUrl',
      'skills', 'requirements', 'education', 'languages', 'experience', 'detectedKeywords'];
    const changed = Boolean(old && changedFields.some(field => JSON.stringify(old[field] ?? null) !== JSON.stringify(normalized[field] ?? null)));
    const status = normalized.closed ? 'closed' : (old ? (changed ? 'changed' : 'known') : 'new');
    const searchQueries = [...new Set([...(old?.searchQueries || []), ...(normalized.searchQueries || [])])];
    merged.set(key, {
      ...(old || {}),
      ...normalized,
      // A later open result must not retain a stale historical `closed` flag.
      closed: normalized.closed ? true : undefined,
      ...(searchQueries.length ? { searchQueries } : {}),
      firstSeenAt: old?.firstSeenAt || normalized.scrapedAt || now,
      lastSeenAt: now,
      seenCount: (old?.seenCount || 0) + 1,
      status,
      statusAt: now,
      statusHistory: [...(old?.statusHistory || []), { status, at: now }],
    });
  }
  for (const [key, job] of merged) {
    if (!currentKeys.has(key) && job.status !== 'closed') {
      merged.set(key, {
        ...job,
        status: 'missing',
        statusAt: now,
        statusHistory: [...(job.statusHistory || []), { status: 'missing', at: now }],
      });
    }
  }
  const result = [...merged.values()];
  await fs.writeFile(file, `${JSON.stringify({ version: 1, updatedAt: now, jobs: result }, null, 2)}\n`, 'utf8');
  return result;
}

module.exports = { readHistory, mergeHistory };
