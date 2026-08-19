function parseRobots(content) {
  const groups = [];
  let group = null;

  for (const originalLine of String(content || '').split(/\r?\n/)) {
    const line = originalLine.split('#', 1)[0].trim();
    if (!line) continue;
    const separator = line.indexOf(':');
    if (separator < 0) continue;
    const field = line.slice(0, separator).trim().toLowerCase();
    const value = line.slice(separator + 1).trim();

    if (field === 'user-agent') {
      if (!group || group.rules.length) {
        group = { agents: [], rules: [] };
        groups.push(group);
      }
      group.agents.push(value.toLowerCase());
    } else if ((field === 'allow' || field === 'disallow') && group) {
      group.rules.push({ type: field, path: value });
    }
  }

  const wildcard = groups.find(candidate => candidate.agents.includes('*'));
  return wildcard ? wildcard.rules : [];
}

function ruleMatches(pathname, rulePath) {
  if (!rulePath) return false;
  const expression = String(rulePath)
    .replace(/[.+?^${}()|[\]\\]/g, '\\$&')
    .replace(/\*/g, '.*');
  const anchored = expression.endsWith('\\$')
    ? `${expression.slice(0, -2)}$`
    : `^${expression}`;
  return new RegExp(anchored).test(pathname);
}

function isAllowedByRobots(targetUrl, rules) {
  const url = new URL(targetUrl);
  const pathname = `${url.pathname || '/'}${url.search || ''}`;
  const matches = rules
    .filter(rule => ruleMatches(pathname, rule.path))
    .sort((left, right) => right.path.length - left.path.length);
  if (!matches.length) return true;
  const bestLength = matches[0].path.length;
  const best = matches.filter(rule => rule.path.length === bestLength);
  return !best.some(rule => rule.type === 'disallow');
}

async function assertRobotsAllowed({ robotsUrl, targetUrl, timeout = 10000, fetchImpl = globalThis.fetch }) {
  if (typeof fetchImpl !== 'function') throw new Error('No hay fetch disponible para comprobar robots.txt.');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetchImpl(robotsUrl, {
      signal: controller.signal,
      headers: { 'User-Agent': 'TDR-Assistent-IA-InfoJobsScraper/1.0' },
    });
    if (!response || !response.ok) {
      throw new Error(`No se pudo leer robots.txt (${response ? response.status : 'sin respuesta'}).`);
    }
    const rules = parseRobots(await response.text());
    if (!isAllowedByRobots(targetUrl, rules)) {
      throw new Error(`robots.txt no permite acceder a ${new URL(targetUrl).pathname}.`);
    }
    return rules;
  } finally {
    clearTimeout(timer);
  }
}

module.exports = { parseRobots, isAllowedByRobots, assertRobotsAllowed };
