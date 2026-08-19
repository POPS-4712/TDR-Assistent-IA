const express = require('express');
const { runScraper } = require('./scraper');
const { runInfoJobsScraper } = require('./infojobs-scraper');

const app = express();
const port = Number(process.env.PORT || 3000);
const runningSources = new Set();
const optionalNumber = (query, name) => (
  query[name] === undefined || query[name] === '' ? undefined : Number(query[name])
);

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', scraperRunning: runningSources.size > 0 });
});

app.get('/linkedin', async (req, res) => {
  if (runningSources.has('linkedin')) {
    return res.status(409).json({ error: 'Ya hay un scraping en curso.' });
  }

  runningSources.add('linkedin');
  try {
    const terms = req.query.keywords
      ? String(req.query.keywords).split(',').map(term => term.trim()).filter(Boolean)
      : undefined;
    const jobs = await runScraper({
      terms,
      location: req.query.location ? String(req.query.location) : undefined,
      termsPerQuery: optionalNumber(req.query, 'termsPerQuery'),
      maxJobsPerSearch: optionalNumber(req.query, 'maxJobsPerSearch'),
      maxScrollSteps: optionalNumber(req.query, 'maxScrollSteps'),
      gotoTimeout: optionalNumber(req.query, 'gotoTimeout'),
      selectorTimeout: optionalNumber(req.query, 'selectorTimeout'),
    });
    return res.json(jobs);
  } catch (error) {
    console.error(`[api] ${error.stack || error.message}`);
    return res.status(500).json({ error: error.message });
  } finally {
    runningSources.delete('linkedin');
  }
});

app.get('/infojobs', async (req, res) => {
  if (runningSources.has('infojobs')) {
    return res.status(409).json({ error: 'Ya hay un scraping en curso.' });
  }

  runningSources.add('infojobs');
  try {
    const terms = req.query.keywords
      ? String(req.query.keywords).split(',').map(term => term.trim()).filter(Boolean)
      : undefined;
    const jobs = await runInfoJobsScraper({
      terms,
      location: req.query.location ? String(req.query.location) : undefined,
      termsPerQuery: optionalNumber(req.query, 'termsPerQuery'),
      maxJobsPerSearch: optionalNumber(req.query, 'maxJobsPerSearch'),
      maxScrollSteps: optionalNumber(req.query, 'maxScrollSteps'),
      gotoTimeout: optionalNumber(req.query, 'gotoTimeout'),
      selectorTimeout: optionalNumber(req.query, 'selectorTimeout'),
    });
    return res.json(jobs);
  } catch (error) {
    console.error(`[api/infojobs] ${error.stack || error.message}`);
    return res.status(500).json({ error: error.message });
  } finally {
    runningSources.delete('infojobs');
  }
});

app.listen(port, () => {
  console.log(`Playwright API escuchando en http://localhost:${port}`);
});
