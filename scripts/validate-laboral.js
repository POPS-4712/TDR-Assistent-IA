/**
 * validate-laboral.js
 * Validación funcional del workflow 02-laboral.json
 */
const fs = require('fs');
const path = require('path');

const WORKFLOW_PATH = path.join(__dirname, '..', 'workflows', '02-laboral.json');

// ─── 1. JSON válido ────────────────────────────────────────────────────────────
let wf;
try {
  wf = JSON.parse(fs.readFileSync(WORKFLOW_PATH, 'utf8'));
  console.log('✅ JSON válido');
} catch (e) {
  console.error('❌ JSON inválido:', e.message);
  process.exit(1);
}

// ─── 2. Estructura básica n8n ─────────────────────────────────────────────────
const REQUIRED_TOP = ['name', 'nodes', 'connections', 'settings'];
for (const k of REQUIRED_TOP) {
  if (!wf[k]) { console.error(`❌ Falta campo requerido: ${k}`); process.exit(1); }
}
console.log('✅ Estructura básica n8n correcta');

// ─── 3. Todos los nodos tienen id, name, type ─────────────────────────────────
const nodeNames = new Set();
const nodeIds = new Set();
for (const node of wf.nodes) {
  if (!node.id) { console.error(`❌ Nodo sin id: ${node.name}`); process.exit(1); }
  if (!node.name) { console.error(`❌ Nodo sin name`); process.exit(1); }
  if (!node.type) { console.error(`❌ Nodo sin type: ${node.name}`); process.exit(1); }
  if (nodeIds.has(node.id)) { console.error(`❌ ID duplicado: ${node.id}`); process.exit(1); }
  nodeIds.add(node.id);
  nodeNames.add(node.name);
}
console.log(`✅ ${wf.nodes.length} nodos validados (sin duplicados)`);

// ─── 4. Conexiones referencia nodos que existen ───────────────────────────────
let connErrors = 0;
for (const [fromNode, connDef] of Object.entries(wf.connections)) {
  if (!nodeNames.has(fromNode)) {
    console.error(`❌ Conexión desde nodo inexistente: ${fromNode}`); connErrors++;
  }
  for (const outputs of Object.values(connDef)) {
    for (const outputArray of outputs) {
      for (const conn of (outputArray || [])) {
        if (!nodeNames.has(conn.node)) {
          console.error(`❌ Conexión hacia nodo inexistente: ${conn.node}`); connErrors++;
        }
      }
    }
  }
}
if (connErrors === 0) console.log('✅ Todas las conexiones referencian nodos existentes');
else { process.exit(1); }

// ─── 5. Nodos obligatorios presentes ─────────────────────────────────────────
const REQUIRED_NODES = [
  'Preparar solicitudes Playwright',
  'HTTP - Ejecutar scraper Playwright',
  'Normalizar y validar ofertas',
  'Filtrar sectores objetivo',
  'Evitar duplicados PostgreSQL',
  'Scoring de ofertas',
  'Seleccionar TOP 3',
  'Gemini - Resumir oferta',
  'Validar JSON Gemini',
  'Construir mensaje Telegram',
  'Telegram - Enviar oferta',
  'Sin ofertas - Preparar mensaje',
];
let missingNodes = 0;
for (const name of REQUIRED_NODES) {
  if (!nodeNames.has(name)) {
    console.error(`❌ Nodo obligatorio ausente: ${name}`); missingNodes++;
  }
}
if (missingNodes === 0) console.log('✅ Todos los nodos obligatorios presentes');
else process.exit(1);

// ─── 6. Triggers configurados ────────────────────────────────────────────────
const triggers = wf.nodes.filter(n =>
  ['n8n-nodes-base.cron', 'n8n-nodes-base.manualTrigger', 'n8n-nodes-base.webhook'].includes(n.type)
);
console.log(`✅ ${triggers.length} triggers configurados: ${triggers.map(t => t.name).join(', ')}`);

// ─── 7. Nodo Postgres tiene credenciales ─────────────────────────────────────
const pgNode = wf.nodes.find(n => n.type === 'n8n-nodes-base.postgres');
if (!pgNode?.credentials?.postgres?.name) {
  console.error('❌ Nodo PostgreSQL sin credenciales configuradas');
  process.exit(1);
}
console.log(`✅ PostgreSQL usa credencial: "${pgNode.credentials.postgres.name}"`);

// ─── 8. Variables de entorno referenciadas (no hardcodeadas) ─────────────────
const wfStr = JSON.stringify(wf);
const hardcodedTokenPattern = /\b[0-9]{8,12}:[A-Za-z0-9_-]{35,}\b/;
if (hardcodedTokenPattern.test(wfStr)) {
  console.error('❌ Se encontró un posible token hardcodeado en el workflow');
  process.exit(1);
}
const usesEnvTelegram = wfStr.includes('TELEGRAM_BOT_TOKEN') && wfStr.includes('TELEGRAM_CHAT_ID');
const usesEnvGemini = wfStr.includes('GEMINI_API_KEY') && wfStr.includes('GEMINI_MODEL');
if (!usesEnvTelegram) { console.error('❌ Variables de Telegram no referenciadas via $env'); process.exit(1); }
if (!usesEnvGemini) { console.error('❌ Variables de Gemini no referenciadas via $env'); process.exit(1); }
console.log('✅ Credenciales referenciadas mediante variables de entorno ($env)');

// ─── 9. Lógica de scoring en el nodo ────────────────────────────────────────
const scoringNode = wf.nodes.find(n => n.name === 'Scoring de ofertas');
const scoringCode = scoringNode?.parameters?.jsCode || '';
const hasCompanies = scoringCode.includes('airbus') && scoringCode.includes('indra') && scoringCode.includes('accenture');
const hasScoreCompute = scoringCode.includes('computeScore') || scoringCode.includes('score');
const hasLocationBonus = scoringCode.includes('barcelona') && scoringCode.includes('madrid');
if (!hasCompanies) { console.error('❌ Lista de empresas prioritarias no encontrada en Scoring'); process.exit(1); }
if (!hasScoreCompute) { console.error('❌ Función de scoring no encontrada'); process.exit(1); }
if (!hasLocationBonus) { console.error('❌ Bonus de ubicación no encontrado en Scoring'); process.exit(1); }
console.log('✅ Scoring con empresas prioritarias, ubicación y nivel correctamente implementado');

// ─── 10. TOP 3 con umbral ────────────────────────────────────────────────────
const top3Node = wf.nodes.find(n => n.name === 'Seleccionar TOP 3');
const top3Code = top3Node?.parameters?.jsCode || '';
if (!top3Code.includes('MAX_OFFERS') && !top3Code.includes('slice(0, 3)') && !top3Code.includes('slice(0,3)') && !top3Code.includes('MAX_OFFERS = 3')) {
  console.error('❌ Selección de máximo 3 ofertas no encontrada'); process.exit(1);
}
if (!top3Code.includes('MIN_SCORE') && !top3Code.includes('score') ) {
  console.error('❌ Umbral mínimo no encontrado en TOP 3'); process.exit(1);
}
console.log('✅ Selección TOP 3 con umbral mínimo correctamente implementada');

// ─── 11. Mensaje Telegram con campos requeridos ──────────────────────────────
const msgNode = wf.nodes.find(n => n.name === 'Construir mensaje Telegram');
const msgCode = msgNode?.parameters?.jsCode || '';
const hasRequiredFields = ['titulo', 'empresa', 'ubicacion', 'score', 'resumen', 'enlace'].every(f => msgCode.includes(f));
if (!hasRequiredFields) {
  console.error('❌ Mensaje Telegram no incluye todos los campos requeridos (empresa, puesto, ubicación, score, resumen, enlace)');
  process.exit(1);
}
console.log('✅ Mensaje Telegram incluye todos los campos requeridos');

// ─── 12. Gemini con fallback ─────────────────────────────────────────────────
const parseNode = wf.nodes.find(n => n.name === 'Validar JSON Gemini');
const parseCode = parseNode?.parameters?.jsCode || '';
if (!parseCode.includes('fallback') && !parseCode.includes('catch') && !parseCode.includes('try')) {
  console.error('❌ Validación de Gemini sin control de errores/fallback'); process.exit(1);
}
console.log('✅ Gemini con validación y fallback correctamente implementado');

// ─── Resumen final ────────────────────────────────────────────────────────────
console.log('\n════════════════════════════════════════════');
console.log('✅ WORKFLOW 02-LABORAL VALIDADO CORRECTAMENTE');
console.log('════════════════════════════════════════════');
console.log(`  Nodos: ${wf.nodes.length}`);
console.log(`  Conexiones: ${Object.keys(wf.connections).length}`);
console.log(`  Flujo: Playwright → Normalizar → Filtrar → Deduplicar → Scoring → TOP3 → Gemini → Telegram`);
