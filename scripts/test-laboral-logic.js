/**
 * test-laboral-logic.js
 * Prueba la lógica JavaScript de los nodos Code del workflow laboral
 * sin necesidad de n8n ni Docker activos.
 */
const assert = (cond, msg) => { if (!cond) { console.error(`❌ FALLO: ${msg}`); process.exit(1); } };
let passed = 0;
const ok = msg => { console.log(`✅ ${msg}`); passed++; };

// ─── Simular datos que devuelve el scraper Playwright ─────────────────────────
const mockJobs = [
  {
    title: 'Graduate Industrial Engineer',
    company: 'Airbus Spain',
    location: 'Madrid, Spain',
    link: 'https://www.linkedin.com/jobs/view/1234567890/?trk=blah',
    description: 'Buscamos ingeniero industrial para programa graduate en fabricación aeroespacial. Experiencia en Supply Chain y Lean valorada.',
    skills: ['Lean', 'Supply Chain', 'CAD'],
    source: 'linkedin',
    scrapedAt: new Date().toISOString(),
  },
  {
    title: 'Senior Director of Sales',
    company: 'Random Corp',
    location: 'Madrid',
    link: 'https://www.linkedin.com/jobs/view/9999999999/',
    description: 'Director senior de ventas con 15 años de experiencia.',
    source: 'linkedin',
    scrapedAt: new Date().toISOString(),
  },
  {
    title: 'Junior Project Manager - Digital Transformation',
    company: 'Capgemini',
    location: 'Barcelona',
    link: 'https://www.linkedin.com/jobs/view/2222222222/',
    description: 'Junior PM para proyectos de transformación digital en clientes industriales.',
    skills: ['Agile', 'PMO'],
    source: 'linkedin',
    scrapedAt: new Date().toISOString(),
  },
  {
    title: 'Trainee Supply Chain Analyst',
    company: 'Deloitte',
    location: 'Remote - Spain',
    link: 'https://www.linkedin.com/jobs/view/3333333333/',
    description: 'Trainee para equipo de Supply Chain y Operations consulting.',
    source: 'linkedin',
    scrapedAt: new Date().toISOString(),
  },
  {
    title: 'Retail Store Manager',
    company: 'Zara',
    location: 'Barcelona',
    link: 'https://www.linkedin.com/jobs/view/4444444444/',
    description: 'Gestor de tienda minorista.',
    source: 'linkedin',
  },
];

// ─── Test 1: Normalización de URLs ────────────────────────────────────────────
const normalizeLink = v => {
  const raw = String(v ?? '').replace(/\s+/g, ' ').trim();
  if (!raw) return null;
  try {
    const url = new URL(raw, 'https://www.linkedin.com');
    url.hostname = url.hostname.toLowerCase().replace(/^www\./, '');
    url.search = ''; url.hash = '';
    url.pathname = url.pathname.replace(/\/+$/, '') || '/';
    return url.href;
  } catch { return raw; }
};
const normalized = normalizeLink('https://www.linkedin.com/jobs/view/1234567890/?trk=blah&ref=test');
assert(normalized === 'https://linkedin.com/jobs/view/1234567890', `URL normalizada correctamente: ${normalized}`);
ok('Normalización de URL elimina parámetros innecesarios');

// ─── Test 2: Filtrado ─────────────────────────────────────────────────────────
const ROLES_INCLUDE = [
  'industrial engineer', 'supply chain', 'project manager', 'business analyst',
  'operations', 'digital transformation', 'aerospace', 'automation', 'strategy',
  'consultant', 'consulting', 'manufacturing', 'technology', 'engineering',
  'engineer', 'associate', 'graduate', 'junior', 'trainee', 'entry level',
];
const ROLES_EXCLUDE = [
  'director', 'senior director', 'head of', 'sales manager', 'retail', 'hospitality',
];
const LEVEL_EXCLUDE = [/\bsenior\b/i, /\bdirector\b/i, /\bhead of\b/i];
const LOCATION_OK = ['barcelona', 'madrid', 'spain', 'españa', 'remote', 'hybrid', 'remoto'];

const filterJob = job => {
  if (!job.title) return false;
  const titleLow = job.title.toLowerCase();
  const fullLow = (job.description || job.title).toLowerCase();
  const includes = (text, terms) => terms.some(t => text.includes(t.toLowerCase()));
  const matchesAny = (text, patterns) => patterns.some(p => p.test(text));
  if (!includes(titleLow, ROLES_INCLUDE) && !includes(fullLow, ROLES_INCLUDE)) return false;
  if (includes(titleLow, ROLES_EXCLUDE)) return false;
  if (matchesAny(titleLow, LEVEL_EXCLUDE)) {
    const hasJunior = /\b(junior|graduate|trainee|intern|entry.level|young)\b/i.test(titleLow);
    if (!hasJunior) return false;
  }
  if (job.location) {
    const locLow = job.location.toLowerCase();
    if (!LOCATION_OK.some(l => locLow.includes(l))) return false;
  }
  return true;
};

const filtered = mockJobs.filter(filterJob);
assert(filtered.some(j => j.title.includes('Graduate Industrial Engineer')), 'Graduate Industrial Engineer debe pasar el filtro');
assert(!filtered.some(j => j.title.includes('Senior Director')), 'Senior Director debe ser filtrado');
assert(!filtered.some(j => j.title.includes('Retail')), 'Retail debe ser filtrado');
assert(filtered.some(j => j.title.includes('Junior Project Manager')), 'Junior PM debe pasar el filtro');
assert(filtered.some(j => j.title.includes('Trainee Supply Chain')), 'Trainee Supply Chain debe pasar el filtro');
ok(`Filtrado: ${filtered.length}/${mockJobs.length} ofertas pasan el filtro (esperado 3)`);

// ─── Test 3: Scoring ──────────────────────────────────────────────────────────
const PRIORITY_COMPANIES = ['airbus', 'capgemini', 'deloitte', 'indra', 'accenture'];
const ROLE_SCORES = {
  aerospace: 30, 'industrial engineer': 18, 'supply chain': 18, 'project manager': 18,
  'digital transformation': 20, operations: 15, consulting: 14, manufacturing: 13,
  engineering: 10, engineer: 8, junior: 0,
};
const LEVEL_BONUS = { graduate: 15, junior: 15, trainee: 10 };
const LOCATION_BONUS = { barcelona: 20, madrid: 18, spain: 15, remote: 12, hybrid: 10 };

const computeScore = job => {
  let score = 0;
  const title = (job.title || '').toLowerCase();
  const full = (job.description || job.title).toLowerCase();
  const company = (job.company || '').toLowerCase();
  const location = (job.location || '').toLowerCase();
  for (const [term, pts] of Object.entries(ROLE_SCORES)) {
    if (title.includes(term)) { score += pts; break; }
  }
  for (const [level, pts] of Object.entries(LEVEL_BONUS)) {
    if (title.includes(level) || full.includes(level)) { score += pts; break; }
  }
  for (const [loc, pts] of Object.entries(LOCATION_BONUS)) {
    if (location.includes(loc)) { score += pts; break; }
  }
  for (const co of PRIORITY_COMPANIES) {
    if (company.includes(co)) { score += 20; break; }
  }
  return Math.min(score, 100);
};

const airbus = filtered.find(j => j.company.toLowerCase().includes('airbus'));
const capgemini = filtered.find(j => j.company.toLowerCase().includes('capgemini'));
const deloitte = filtered.find(j => j.company.toLowerCase().includes('deloitte'));

if (airbus) {
  const airScore = computeScore(airbus);
  assert(airScore > 50, `Airbus Graduate debe tener puntuación alta: ${airScore}`);
  ok(`Airbus Graduate Engineering score: ${airScore}/100`);
}
if (capgemini) {
  const capScore = computeScore(capgemini);
  assert(capScore > 30, `Capgemini Junior PM debe tener puntuación razonable: ${capScore}`);
  ok(`Capgemini Junior PM score: ${capScore}/100`);
}
if (deloitte) {
  const delScore = computeScore(deloitte);
  ok(`Deloitte Trainee Supply Chain score: ${delScore}/100`);
}

// ─── Test 4: TOP 3 ────────────────────────────────────────────────────────────
const MIN_SCORE = 20;
const MAX_OFFERS = 3;
const scored = filtered.map(j => ({ ...j, score: computeScore(j) }));
const top3 = scored.filter(j => j.score >= MIN_SCORE).sort((a, b) => b.score - a.score).slice(0, MAX_OFFERS);
assert(top3.length <= 3, `TOP 3 no supera 3 ofertas: ${top3.length}`);
ok(`TOP 3 seleccionadas: ${top3.length} ofertas (máximo 3)`);

// ─── Test 5: Mensaje Telegram ─────────────────────────────────────────────────
const escapeHtml = s => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const buildMsg = job => {
  const titulo = escapeHtml(job.title || 'Sin título');
  const empresa = escapeHtml(job.company || 'Empresa desconocida');
  const ubicacion = escapeHtml(job.location || 'No especificada');
  const score = job.score || 0;
  const resumen = escapeHtml((job.description || '').substring(0, 200));
  const enlace = job.link || '';
  let msg = `💼 <b>${titulo}</b>\n\n`;
  msg += `🏢 <b>Empresa:</b> ${empresa}\n`;
  msg += `📍 <b>Ubicación:</b> ${ubicacion}\n`;
  msg += `⭐ <b>Puntuación:</b> ${score}/100\n\n`;
  if (resumen) msg += `📝 <b>Resumen:</b>\n${resumen}\n\n`;
  if (enlace) msg += `🔗 <a href="${enlace}">Ver oferta en LinkedIn</a>\n`;
  msg += '────────────────────';
  return msg;
};

if (top3.length > 0) {
  const msg = buildMsg(top3[0]);
  assert(msg.includes('💼'), 'Mensaje incluye emoji de puesto');
  assert(msg.includes('🏢'), 'Mensaje incluye emoji de empresa');
  assert(msg.includes('📍'), 'Mensaje incluye emoji de ubicación');
  assert(msg.includes('⭐'), 'Mensaje incluye puntuación');
  assert(msg.includes('🔗'), 'Mensaje incluye enlace');
  assert(msg.includes('<b>'), 'Mensaje usa HTML para Telegram');
  assert(!msg.includes('undefined'), 'Mensaje no contiene "undefined"');
  ok('Formato de mensaje Telegram correcto con todos los campos');
  console.log('\nEjemplo de mensaje generado:');
  console.log('─────────────────────────────────');
  console.log(buildMsg(top3[0]));
  console.log('─────────────────────────────────');
}

// ─── Test 6: Deduplicación (simulación de la clave) ──────────────────────────
const buildKey = job => {
  const link = normalizeLink(job.link);
  const id = link?.match(/(?:-|%2D|\/view\/)(\d+)(?:[/?]|$)/i)?.[1] || null;
  const identity = link ? `url:${link}` : (id ? `id:${id}` : `fallback:${job.company}|${job.title}|${job.location}`);
  return `job:linkedin:${identity}`;
};
const keys = mockJobs.map(buildKey);
const uniqueKeys = new Set(keys);
assert(uniqueKeys.size === mockJobs.length, 'Todas las ofertas tienen item_key único');
ok('Deduplicación: todas las claves son únicas');

// ─── Resumen ──────────────────────────────────────────────────────────────────
console.log(`\n════════════════════════════════════════════`);
console.log(`✅ ${passed} TESTS PASADOS — Lógica del workflow correcta`);
console.log(`════════════════════════════════════════════`);
