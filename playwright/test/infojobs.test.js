const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs/promises');
const os = require('os');
const path = require('path');
const { loadInfoJobsConfig } = require('../infojobs-config');
const { parseRobots, isAllowedByRobots, assertRobotsAllowed } = require('../infojobs-robots');
const { INFOJOBS_JOB_LINK_SELECTOR, mapInfoJobsCard } = require('../infojobs-extractor');
const {
  extractInfoJobsId, normalizeInfoJobsLink, normalizeInfoJobsJob, identityKey,
} = require('../infojobs-normalize');
const { mergeInfoJobsHistory } = require('../infojobs-history');
const { buildInfoJobsSearchUrl } = require('../infojobs-scraper');

test('configura InfoJobs sin reutilizar la sesión de LinkedIn', () => {
  const config = loadInfoJobsConfig({ terms: ['PMO'], maxScrollSteps: 0 });
  assert.equal(config.source, 'infojobs');
  assert.equal(config.storageState, undefined);
  assert.match(config.outputFile, /infojobs-jobs\.json$/);
  assert.equal(config.maxScrollSteps, 0);
});

test('extrae y normaliza tarjetas InfoJobs sin navegador ni red', () => {
  const raw = mapInfoJobsCard({
    name: ' Senior PMO ',
    companyName: 'Acme',
    city: 'Barcelona',
    url: 'https://www.infojobs.net/oferta-trabajo/pmo/123456789',
  }, 'PMO', '2026-01-01T00:00:00.000Z');
  const job = normalizeInfoJobsJob(raw);
  assert.match(INFOJOBS_JOB_LINK_SELECTOR, /oferta-trabajo/);
  assert.equal(extractInfoJobsId(raw.link), '123456789');
  assert.equal(normalizeInfoJobsLink(`${raw.link}?ref=search`), 'https://infojobs.net/oferta-trabajo/pmo/123456789');
  assert.equal(job.source, 'infojobs');
  assert.equal(job.title, 'Senior PMO');
  assert.equal(job.link, 'https://infojobs.net/oferta-trabajo/pmo/123456789');
  assert.equal(identityKey(job), 'id:123456789');
});
test('extrae el identificador de las URLs actuales de InfoJobs', () => {
  const link = 'https://www.infojobs.net/barcelona/pmo/of-i5d4de8adf144219b692b67aa92f37c';
  assert.equal(extractInfoJobsId(link), 'i5d4de8adf144219b692b67aa92f37c');
});

test('aplica robots.txt con la regla más específica', () => {
  const rules = parseRobots('User-agent: *\nDisallow: /private\nAllow: /private/public\n');
  assert.equal(isAllowedByRobots('https://www.infojobs.net/private/public', rules), true);
  assert.equal(isAllowedByRobots('https://www.infojobs.net/private/secret', rules), false);
  assert.equal(isAllowedByRobots('https://www.infojobs.net/oferta-trabajo/pmo', rules), true);
});

test('comprueba robots offline y falla cerrado cuando el acceso está prohibido', async () => {
  const fakeFetch = async () => ({
    ok: true,
    text: async () => 'User-agent: *\nDisallow: /jobsearch/\n',
  });
  await assert.rejects(
    assertRobotsAllowed({
      robotsUrl: 'https://www.infojobs.net/robots.txt',
      targetUrl: 'https://www.infojobs.net/jobsearch/search-results/list.xhtml',
      fetchImpl: fakeFetch,
    }),
    /robots\.txt no permite/,
  );
});

test('deduplica y conserva histórico InfoJobs por separado', async () => {
  const file = path.join(await fs.mkdtemp(path.join(os.tmpdir(), 'infojobs-')), 'history.json');
  const first = normalizeInfoJobsJob({
    id: '123', title: 'PMO', company: 'Acme', link: 'https://infojobs.net/oferta/123',
  });
  const second = normalizeInfoJobsJob({
    id: '123', title: 'PMO Senior', company: 'Acme', link: 'https://infojobs.net/oferta/123',
  });
  const initial = await mergeInfoJobsHistory(file, [first]);
  const result = await mergeInfoJobsHistory(file, [second]);
  assert.equal(initial[0].status, 'new');
  assert.equal(result.length, 1);
  assert.equal(result[0].status, 'changed');
  assert.equal(result[0].seenCount, 2);
});

test('construye búsquedas InfoJobs sin tocar otros dominios', () => {
  const url = buildInfoJobsSearchUrl(
    'https://www.infojobs.net/jobsearch/search-results/list.xhtml',
    '"PMO" OR "Operations"',
    'Barcelona',
  );
  assert.equal(new URL(url).hostname, 'www.infojobs.net');
  assert.equal(new URL(url).searchParams.get('keyword'), '"PMO" OR "Operations"');
  assert.equal(new URL(url).searchParams.get('location'), 'Barcelona');
});
