const fs = require('fs/promises');
const path = require('path');
const { loadConfig } = require('./config');
const { normalizeJob, identityKey } = require('./normalize');

async function processJobs(inputFile, outputFile) {
  const contents = await fs.readFile(inputFile, 'utf8');
  const raw = JSON.parse(contents.replace(/^\uFEFF/, ''));
  const jobs = Array.isArray(raw) ? raw : raw.jobs;
  if (!Array.isArray(jobs)) throw new Error(`Entrada inválida (${inputFile}): se esperaba un array de ofertas.`);
  const deduped = new Map();
  for (const item of jobs) {
    const job = normalizeJob(item);
    if (!job) continue;
    const key = identityKey(job);
    const old = deduped.get(key);
    deduped.set(key, old ? {
      ...old, ...job,
      searchQueries: [...new Set([...(old.searchQueries || []), ...(job.searchQueries || [])])],
    } : job);
  }
  await fs.mkdir(path.dirname(outputFile), { recursive: true });
  await fs.writeFile(outputFile, `${JSON.stringify([...deduped.values()], null, 2)}\n`, 'utf8');
  return [...deduped.values()];
}

if (require.main === module) {
  const config = loadConfig();
  processJobs(config.outputFile, config.outputFile)
    .then(jobs => console.log(`Procesadas ${jobs.length} ofertas.`))
    .catch(error => { console.error(`[process] ${error.message}`); process.exitCode = 1; });
}

module.exports = { processJobs };
