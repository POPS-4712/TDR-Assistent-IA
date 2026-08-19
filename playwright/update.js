const { loadConfig } = require('./config');
const { readHistory, mergeHistory } = require('./history');

async function updateHistory(inputFile, historyFile) {
  const current = await readHistory(inputFile);
  return mergeHistory(historyFile, current);
}

if (require.main === module) {
  const config = loadConfig();
  updateHistory(config.outputFile, config.historyFile)
    .then(history => console.log(`Histórico actualizado: ${history.length} ofertas.`))
    .catch(error => { console.error(`[update] ${error.message}`); process.exitCode = 1; });
}

module.exports = { updateHistory };
