const fs = require('fs/promises');
const path = require('path');
const { chromium } = require('playwright');
const { loadConfig } = require('./config');
const { cleanTitle, extractJobId, normalizeJob, identityKey } = require('./normalize');
const { passesFilter, filterJobs } = require('./filters');
const { mergeHistory } = require('./history');
const { JOB_CARD_SELECTOR, extractCards } = require('./extractor');

// Selector for LinkedIn "no results" message
const NO_RESULTS_SELECTOR = '.jobs-search-no-results-banner, .jobs-search__no-results, [data-test-no-results], .artdeco-empty-state';

function buildGroupedQueries(terms, groupSize = 6) {
  const groups = [];
  for (let i = 0; i < terms.length; i += groupSize) {
    groups.push(terms.slice(i, i + groupSize).map(term => `"${term}"`).join(' OR '));
  }
  return groups;
}

function mergeJobs(previous, current) {
  const merged = { ...previous, ...current };
  for (const field of ['description', 'company', 'location', 'link', 'source', 'seniority',
    'salary', 'remote', 'hybrid', 'contractType', 'employmentType', 'industry',
    'companyUrl', 'applicationUrl']) {
    if ((current[field] === null || current[field] === undefined || current[field] === '') &&
        previous[field] !== null && previous[field] !== undefined && previous[field] !== '') {
      merged[field] = previous[field];
    }
  }
  for (const field of ['searchQueries', 'skills', 'requirements', 'education', 'languages',
    'experience', 'detectedKeywords']) {
    merged[field] = [...new Set([
      ...(Array.isArray(previous[field]) ? previous[field] : []),
      ...(Array.isArray(current[field]) ? current[field] : []),
    ])];
  }
  return merged;
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

async function runScraper(options = {}) {
  const config = loadConfig(options);
  try { await fs.access(config.storageState); } catch {
    throw new Error(`No existe la sesión de LinkedIn en ${config.storageState}. Ejecuta "npm run login" primero.`);
  }
  const jobs = new Map();
  const browser = await chromium.launch({ headless: config.headless, args: ['--disable-blink-features=AutomationControlled'] });
  try {
    const context = await browser.newContext({ storageState: config.storageState, viewport: { width: 1920, height: 1080 }, locale: 'es-ES', timezoneId: 'Europe/Madrid' });
    // THREE PREDEFINED SEARCH GROUPS
    const groups = [
      '"Project Manager" OR "Program Manager" OR "PMO" OR "Business Analyst" OR "Operations Manager" OR "Continuous Improvement"',
      '"Industrial Engineer" OR "Supply Chain" OR "Operational Excellence" OR "Lean" OR "Manufacturing" OR "Automation"',
      '"Digital Transformation" OR "Business Intelligence" OR "Strategy" OR "Technology" OR "Artificial Intelligence" OR "Aerospace"'
    ];
    // Track statistics for logging
    const searchStats = [];
    let totalJobsBeforeSearch = 0;
    
    for (let index = 0; index < groups.length; index += 1) {
      const page = await context.newPage();
      let jobsFoundInSearch = 0;
      let jobsAddedInSearch = 0;
      let searchHadResults = false;
      
      try {
        const query = groups[index];
        const url = `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(query)}&location=${encodeURIComponent(config.location)}`;
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: config.gotoTimeout });
        
        // Wait for either job cards OR "no results" message (race condition)
        // This prevents timeout when there are no results
        try {
          await Promise.race([
            page.waitForSelector(JOB_CARD_SELECTOR, { timeout: config.selectorTimeout }),
            page.waitForSelector(NO_RESULTS_SELECTOR, { timeout: config.selectorTimeout })
          ]);
        } catch (waitError) {
          // If both selectors timeout, check which one exists
          const hasJobCards = await page.locator(JOB_CARD_SELECTOR).count() > 0;
          const hasNoResults = await page.locator(NO_RESULTS_SELECTOR).count() > 0;
          
          if (!hasJobCards && hasNoResults) {
            // No results page detected
            console.error(`[scraper] búsqueda ${index + 1}/3: sin resultados`);
            searchStats.push({ search: index + 1, query, jobsFound: 0, jobsAdded: 0, duplicates: 0 });
            continue; // Skip to next search
          } else if (!hasJobCards && !hasNoResults) {
            // Neither found - likely a loading issue or unexpected page
            throw waitError; // Re-throw to be caught by outer catch
          }
          // If hasJobCards, continue normally
        }
        
        // Check if we're on a "no results" page
        const noResultsCount = await page.locator(NO_RESULTS_SELECTOR).count();
        if (noResultsCount > 0) {
          console.error(`[scraper] búsqueda ${index + 1}/3: sin resultados`);
          searchStats.push({ search: index + 1, query, jobsFound: 0, jobsAdded: 0, duplicates: 0 });
          continue;
        }
        
        // We have results - scroll and extract
        await scrollResults(page, config.maxScrollSteps);
        const rawJobs = await extractCards(page, { maxJobsPerSearch: config.maxJobsPerSearch, query });
        jobsFoundInSearch = rawJobs.length;
        
        let jobsPassedFilter = 0;
        let duplicatesInSearch = 0;
        totalJobsBeforeSearch = jobs.size;
        for (const raw of rawJobs) {
          const job = normalizeJob(raw);
          if (job && passesFilter(job.title, config)) {
            jobsPassedFilter++;
            const key = identityKey(job);
            const previous = jobs.get(key);
            const isDuplicate = previous !== undefined;
            jobs.set(key, previous ? mergeJobs(previous, job) : mergeJobs({}, job));
            if (!isDuplicate) {
              jobsAddedInSearch++;
            } else {
              duplicatesInSearch++;
            }
          }
        }
        
        searchHadResults = true;
        console.error(`[scraper] búsqueda ${index + 1}/3: ${jobsFoundInSearch} ofertas encontradas, ${jobsPassedFilter} pasaron filtro, ${jobsAddedInSearch} nuevas, ${duplicatesInSearch} duplicadas`);
        searchStats.push({ search: index + 1, query, jobsFound: jobsFoundInSearch, jobsAdded: jobsAddedInSearch, duplicates: duplicatesInSearch });
        
      } catch (error) {
        // Check if this is a timeout error from waitForSelector (likely means no results)
        if (error.message.includes('Timeout') && error.message.includes('waitForSelector')) {
          console.error(`[scraper] búsqueda ${index + 1}/3: sin resultados (timeout)`);
        } else {
          console.error(`[scraper] búsqueda ${index + 1}/3: error - ${error.message}`);
        }
        try {
          await saveDiagnostics(page, config.debugDir, index + 1, config.diagnosticsTimeout);
        } catch (diagnosticError) {
          console.error(`[scraper] no se pudo guardar diagnóstico: ${diagnosticError.message}`);
        }
        searchStats.push({ search: index + 1, query: groups[index], jobsFound: 0, jobsAdded: 0, duplicates: 0, error: error.message });
      } finally {
        await page.close({ runBeforeUnload: false }).catch(error => {
          console.error(`[scraper] no se pudo cerrar la página: ${error.message}`);
        });
      }
    }
    
    // Final summary logging
    const totalJobsFound = searchStats.reduce((sum, s) => sum + s.jobsFound, 0);
    const totalJobsAdded = searchStats.reduce((sum, s) => sum + s.jobsAdded, 0);
    const totalDuplicates = searchStats.reduce((sum, s) => sum + s.duplicates, 0);
    const successfulSearches = searchStats.filter(s => s.jobsFound > 0 || s.jobsAdded > 0).length;
    console.error(`[scraper] Resumen: ${successfulSearches}/3 búsquedas con resultados, ${totalJobsFound} ofertas totales, ${totalJobsAdded} únicas, ${totalDuplicates} duplicadas eliminadas, ${jobs.size} ofertas finales`);
    const results = filterJobs([...jobs.values()], config);
    await fs.mkdir(path.dirname(config.outputFile), { recursive: true });
    await fs.mkdir(path.dirname(config.historyFile), { recursive: true });
    await fs.writeFile(config.outputFile, `${JSON.stringify(results, null, 2)}\n`, 'utf8');
    await mergeHistory(config.historyFile, results);
    return results;
  } finally {
    await browser.close({ runBeforeUnload: false }).catch(error => {
      console.error(`[scraper] no se pudo cerrar el navegador: ${error.message}`);
    });
  }
}

if (require.main === module) {
  runScraper().then(results => process.stdout.write(`${JSON.stringify(results)}\n`))
    .catch(error => { console.error(`[scraper] ${error.message}`); process.exitCode = 1; });
}

module.exports = {
  runScraper, buildGroupedQueries, cleanTitle, extractJobId, passesFilter, mergeJobs,
};
