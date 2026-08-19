const test = require('node:test');
const assert = require('node:assert/strict');
const { buildGroupedQueries, cleanTitle, mergeJobs, passesFilter } = require('../scraper');
const { extractJobId, extractSeniority, normalizeJob, identityKey } = require('../normalize');
const { mergeHistory } = require('../history');
const { loadConfig } = require('../config');
const fs = require('fs/promises');
const os = require('os');
const path = require('path');

test('agrupa términos y limpia títulos duplicados', () => {
  assert.deepEqual(buildGroupedQueries(['A', 'B', 'C'], 2), ['"A" OR "B"', '"C"']);
  assert.equal(cleanTitle('PMOPMO'), 'PMO');
});
test('normaliza identificador y enlace', () => {
  assert.equal(extractJobId('https://www.linkedin.com/jobs/view/12345/?x=1'), '12345');
  assert.equal(normalizeJob({ title: '  PMO  ', link: '/jobs/view/12345/?trk=x' }).link, 'https://linkedin.com/jobs/view/12345');
});
test('extrae seniority sólo cuando aparece explícitamente', () => {
  assert.equal(extractSeniority({ title: 'Senior Project Manager' }), 'senior');
  assert.equal(extractSeniority({ title: 'Project Analyst' }), null);
});
test('expone el esquema completo sin inventar campos ausentes', () => {
  const job = normalizeJob({ title: 'PMO', company: 'Acme' });
  for (const field of ['seniority', 'salary', 'remote', 'hybrid', 'contractType', 'employmentType',
    'industry', 'companyUrl', 'applicationUrl']) assert.equal(job[field], null);
  for (const field of ['skills', 'requirements', 'education', 'languages', 'experience', 'detectedKeywords']) {
    assert.deepEqual(job[field], []);
  }
  assert.equal(job.description, null);
});
test('deduplica por URL normalizada o fallback y conserva búsquedas', () => {
  const first = normalizeJob({
    title: ' PMO ', company: 'Acme', location: 'Barcelona',
    link: 'https://www.linkedin.com/jobs/view/12345/?trk=foo', searchQuery: 'PMO',
  });
  test('fusiona duplicados sin perder datos disponibles', () => {
    const merged = mergeJobs(
      { id: '1', title: 'PMO', description: 'Descripción', salary: '50k', skills: ['SQL'] },
      { id: '1', title: 'PMO Senior', description: null, salary: null, skills: ['Lean'],
        searchQueries: ['Operations'] },
    );
    assert.equal(merged.description, 'Descripción');
    assert.equal(merged.salary, '50k');
    assert.deepEqual(merged.skills, ['SQL', 'Lean']);
    assert.deepEqual(merged.searchQueries, ['Operations']);
  });
  const second = normalizeJob({
    title: 'PMO', company: 'Acme', location: 'Barcelona',
    link: '/jobs/view/12345/', searchQueries: ['Operations'],
  });
  assert.equal(identityKey(first), identityKey(second));
  assert.deepEqual(second.searchQueries, ['Operations']);
  assert.equal(normalizeJob({ title: 'PMO', company: 'Acme', location: 'Barcelona' }).link, null);
});
test('aplica inclusión y exclusión sin IA', () => {
  const config = { include: ['project manager'], exclude: ['mechanical'] };
  assert.equal(passesFilter('Senior Project Manager', config), true);
  assert.equal(passesFilter('Mechanical Project Manager', config), false);
});
test('migra histórico en array y deduplica por id', async () => {
  const file = path.join(await fs.mkdtemp(path.join(os.tmpdir(), 'linkedin-')), 'history.json');
  await fs.writeFile(file, JSON.stringify([{ id: '1', title: 'Old' }]));
  const result = await mergeHistory(file, [{ id: '1', title: 'New', scrapedAt: '2026-01-01T00:00:00.000Z' }, { id: '2', title: 'Two' }]);
  assert.equal(result.length, 2);
  assert.equal(result.find(job => job.id === '1').seenCount, 1);
});
test('registra new, changed, missing y closed sin borrar', async () => {
  const file = path.join(await fs.mkdtemp(path.join(os.tmpdir(), 'linkedin-')), 'history.json');
  await mergeHistory(file, [
    { id: '1', title: 'PMO', company: 'Acme', location: 'BCN' },
    { id: '2', title: 'Old', company: 'Acme', location: 'BCN' },
  ]);
  const result = await mergeHistory(file, [
    { id: '1', title: 'PMO Senior', company: 'Acme', location: 'BCN' },
    { id: '3', title: 'Closed', company: 'Acme', location: 'BCN', status: 'closed' },
  ]);
  assert.equal(result.find(job => job.id === '1').status, 'changed');
  assert.equal(result.find(job => job.id === '2').status, 'missing');
  assert.equal(result.find(job => job.id === '3').status, 'closed');
});
test('respeta valores numéricos explícitos, incluido cero', () => {
  assert.equal(loadConfig({ maxScrollSteps: 0, termsPerQuery: 1 }).maxScrollSteps, 0);
  assert.equal(loadConfig({ maxScrollSteps: 0, termsPerQuery: 1 }).termsPerQuery, 1);
});
