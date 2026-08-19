const { runScraper } = require('./playwright/scraper');

runScraper()
  .then(results => process.stdout.write(`${JSON.stringify(results)}\n`))
  .catch(error => {
    console.error(`[scraper] ${error.message}`);
    process.exitCode = 1;
  });
