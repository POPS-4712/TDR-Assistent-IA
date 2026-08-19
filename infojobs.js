const { runInfoJobsScraper } = require('./playwright/infojobs-scraper');

runInfoJobsScraper()
  .then(results => process.stdout.write(`${JSON.stringify(results)}\n`))
  .catch(error => {
    console.error(`[infojobs] ${error.message}`);
    process.exitCode = 1;
  });
