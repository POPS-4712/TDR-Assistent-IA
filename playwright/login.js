const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const output = process.env.LINKEDIN_STORAGE_STATE || path.join(__dirname, 'linkedin.json');
  const browser = await chromium.launch({ headless: false });

  const context = await browser.newContext();

  const page = await context.newPage();

  await page.goto("https://www.linkedin.com/login");

  console.log("Inicia sesión manualmente.");
  console.log("Cuando veas tu feed de LinkedIn, pulsa ENTER en esta consola.");

  process.stdin.once("data", async () => {
    await context.storageState({ path: output });
    console.log(`Sesión guardada en ${output}.`);
    await browser.close();
    process.exit();
  });
})();