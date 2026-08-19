const fs = require('fs/promises');
const path = require('path');
const { chromium } = require('playwright');
const { buildGroupedQueries, mergeJobs } = require('./scraper');
const { filterJobs } = require('./filters');
const { loadInfoJobsConfig } = require('./infojobs-config');
const { assertRobotsAllowed } = require('./infojobs-robots');
const { INFOJOBS_JOB_LINK_SELECTOR, extractInfoJobsCards } = require('./infojobs-extractor');
const { identityKey, normalizeInfoJobsJob } = require('./infojobs-normalize');
const { mergeInfoJobsHistory } = require('./infojobs-history');

function buildInfoJobsSearchUrl(searchUrl, query, location) {
  const url = new URL(searchUrl);
  if (query) url.searchParams.set('keyword', query);
  if (location) url.searchParams.set('location', location);
  return url.href;
}

async function saveDiagnostics(page, directory, index, timeout) {
  await fs.mkdir(directory, { recursive: true });
  const diagnostics = Promise.all([
    page.screenshot({ path: path.join(directory, `search-${index}.png`), fullPage: true }),
    page.content().then(html => fs.writeFile(path.join(directory, `search-${index}.html`), html, 'utf8')),
  ]);
  await Promise.race([
    diagnostics,
    new Promise((_, reject) => setTimeout(() => reject(new Error('diagnóstico agotó su timeout')), timeout)),
  ]);
}

async function scrollResults(page, steps) {
  for (let step = 0; step < steps; step += 1) {
    await page.mouse.wheel(0, 2500);
    await page.waitForTimeout(700);
  }
}

async function runInfoJobsScraper(options = {}) {
  const config = loadInfoJobsConfig(options);
  const groups = buildGroupedQueries(config.terms, config.termsPerQuery);
  const firstUrl = buildInfoJobsSearchUrl(config.searchUrl, groups[0] || '', config.location);

  // InfoJobs is public: no credentials or storage state are loaded. Fail closed if robots.txt
  // cannot be checked or disallows the search path.
  await assertRobotsAllowed({
    robotsUrl: config.robotsUrl,
    targetUrl: firstUrl,
    timeout: config.robotsTimeout,
  });

  const jobs = new Map();
  const browser = await chromium.launch({ headless: config.headless });
  try {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      locale: 'es-ES',
      timezoneId: 'Europe/Madrid',
    });
    for (let index = 0; index < groups.length; index += 1) {
      const page = await context.newPage();
      try {
        const query = groups[index];
        const url = buildInfoJobsSearchUrl(config.searchUrl, query, config.location);
        const response = await page.goto(url, {
          waitUntil: 'domcontentloaded', timeout: config.gotoTimeout,
        });
        if (response && response.status() >= 400) {
          throw new Error(`InfoJobs respondió con HTTP ${response.status()}.`);
        }
        await page.waitForSelector(INFOJOBS_JOB_LINK_SELECTOR, { timeout: config.selectorTimeout });
        await scrollResults(page, config.maxScrollSteps);
        for (const raw of await extractInfoJobsCards(page, {
          maxJobsPerSearch: config.maxJobsPerSearch, query,
        })) {
          const job = normalizeInfoJobsJob(raw);
          if (job && filterJobs([job], config).length) {
            const key = identityKey(job);
            const previous = jobs.get(key);
            jobs.set(key, previous ? mergeJobs(previous, job) : mergeJobs({}, job));
          }
        }
      } catch (error) {
        console.error(`[infojobs] búsqueda ${index + 1}/${groups.length}: ${error.message}`);
        try {
          await saveDiagnostics(page, config.debugDir, index + 1, config.diagnosticsTimeout);
        } catch (diagnosticError) {
          console.error(`[infojobs] no se pudo guardar diagnóstico: ${diagnosticError.message}`);
        }
      } finally {
        await page.close({ runBeforeUnload: false }).catch(error => {
          console.error(`[infojobs] no se pudo cerrar la página: ${error.message}`);
        });
      }
    }
    const results = filterJobs([...jobs.values()], config);
    await fs.mkdir(path.dirname(config.outputFile), { recursive: true });
    await fs.mkdir(path.dirname(config.historyFile), { recursive: true });
    await fs.writeFile(config.outputFile, `${JSON.stringify(results, null, 2)}\n`, 'utf8');
    await mergeInfoJobsHistory(config.historyFile, results);
    return results;
  } finally {
    await browser.close({ runBeforeUnload: false }).catch(error => {
      console.error(`[infojobs] no se pudo cerrar el navegador: ${error.message}`);
    });
  }
}

if (require.main === module) {
  runInfoJobsScraper().then(results => process.stdout.write(`${JSON.stringify(results)}\n`))
    .catch(error => { console.error(`[infojobs] ${error.message}`); process.exitCode = 1; });
}

module.exports = {
  runInfoJobsScraper,
  runScraper: runInfoJobsScraper,
  buildInfoJobsSearchUrl,
};
