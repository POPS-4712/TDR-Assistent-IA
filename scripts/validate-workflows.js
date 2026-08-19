const fs = require('fs');
const path = require('path');

const workflowDir = path.join(__dirname, '..', 'workflows');
let failed = false;

const requiredWorkflows = new Map([
  ['01-email-manager.json', ['Gmail Trigger', 'Gemini - Clasificar correo', 'Switch - Categoría']],
  ['02-laboral.json', ['Webhook - Playwright Jobs', 'Preparar solicitudes Playwright', 'HTTP - Ejecutar scraper Playwright', 'Normalizar y validar ofertas', 'Gemini - Resumir oferta']],
  ['03-news.json', ['RSS - Noticias', 'Eliminar duplicados', 'Gemini - Resumir noticia']],
  ['04-personal-brand.json', ['RSS - OpenAI', 'RSS - Google', 'RSS - Microsoft', 'RSS - NVIDIA', 'Gemini - Borrador LinkedIn']],
  ['05-playwright-jobs.json', ['Webhook - Playwright Jobs', 'HTTP - Ejecutar scraper Playwright', 'Normalizar y validar ofertas', 'Histórico PostgreSQL - Sólo nuevos', 'Preparar resultados']],
]);

for (const file of fs.readdirSync(workflowDir).filter((name) => name.endsWith('.json')).sort()) {
  try {
    const workflow = JSON.parse(fs.readFileSync(path.join(workflowDir, file), 'utf8'));
    const names = new Set();
    const ids = new Set();
    for (const node of workflow.nodes ?? []) {
      if (!node.name || !node.id || !node.type) throw new Error('Nodo incompleto');
      if (names.has(node.name)) throw new Error(`Nombre de nodo duplicado: ${node.name}`);
      if (ids.has(node.id)) throw new Error(`ID de nodo duplicado: ${node.id}`);
      names.add(node.name);
      ids.add(node.id);
    }
    for (const [source, outputs] of Object.entries(workflow.connections ?? {})) {
      if (!names.has(source)) throw new Error(`Origen de conexión inexistente: ${source}`);
      for (const output of outputs.main ?? []) {
        for (const connection of output ?? []) {
          if (!names.has(connection.node)) throw new Error(`Destino inexistente: ${connection.node}`);
        }
      }
    }
    for (const expected of requiredWorkflows.get(file) ?? []) {
      if (!names.has(expected)) throw new Error(`Nodo obligatorio ausente: ${expected}`);
    }
    if (file === '02-laboral.json') {
      const forbidden = /\b(infojobs|indeed)\b|RSS\s*-\s*InfoJobs|RSS\s*-\s*Indeed/i;
      if (forbidden.test(JSON.stringify(workflow))) {
        throw new Error('El workflow laboral contiene una referencia no LinkedIn');
      }
      const serialized = JSON.stringify(workflow);
      if (!/source\s*:\s*['"]linkedin['"]/.test(serialized)) {
        throw new Error('El workflow laboral no fuerza source=linkedin');
      }
      if (!serialized.includes('El webhook sólo acepta source=linkedin')) {
        throw new Error('El webhook laboral no restringe source=linkedin');
      }
    }
    if (!workflow.settings?.executionOrder) throw new Error('Falta settings.executionOrder');
    console.log(`OK ${file}: ${names.size} nodos`);
  } catch (error) {
    failed = true;
    console.error(`ERROR ${file}: ${error.message}`);
  }
}

for (const expectedFile of requiredWorkflows.keys()) {
  if (!fs.existsSync(path.join(workflowDir, expectedFile))) {
    failed = true;
    console.error(`ERROR falta el workflow ${expectedFile}`);
  }
}

process.exitCode = failed ? 1 : 0;
