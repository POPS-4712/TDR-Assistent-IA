# AI Personal Assistant

Asistente personal con n8n, PostgreSQL, Gemini, Gmail, Calendar, Tasks, Google Docs, RSS y WhatsApp Cloud API. Preparado para Docker Desktop en Windows.

## Instalación

1. Instala Docker Desktop y Git, y comprueba que Docker Desktop está iniciado.
2. Copia `.env.example` como `.env` y completa los valores. Genera secretos con:

   ```powershell
   .\scripts\generate-secrets.ps1
   ```

3. Valida la configuración y arranca el stack:

   ```powershell
   docker compose config --quiet
   docker compose up -d
   docker compose ps
   ```

4. Abre `http://localhost:5678` y crea el propietario de n8n.
5. Configura OAuth2 siguiendo [docs/GOOGLE_OAUTH.md](docs/GOOGLE_OAUTH.md).
6. En n8n crea la credencial PostgreSQL llamada `Postgres assistant` (host `postgres`, puerto `5432`, valores de `.env`). Crea las credenciales Google con el nombre `Google OAuth2`.
7. Importa los JSON desde **Workflows → Import from File**, o ejecuta:

   ```powershell
   .\scripts\import-workflows.ps1
   ```

8. Abre cada workflow, asigna las credenciales que correspondan, prueba una ejecución manual y actívalo.

## Credenciales y conexiones

- **Gmail / Calendar / Tasks / Docs:** credenciales OAuth2 de Google. La URL de retorno local es `http://localhost:5678/rest/oauth2-credential/callback`.
- **Gemini:** crea una API key en Google AI Studio y establece `GEMINI_API_KEY`; los workflows la leen desde el entorno.
- **WhatsApp:** configura Meta WhatsApp Cloud API mediante `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN` y `WHATSAPP_RECIPIENT` (formato internacional, sin `+`).
- **Google Docs:** si se desea una carpeta concreta, establece `GOOGLE_DOCS_FOLDER_ID`; de lo contrario los borradores se crean en la raíz de Drive.

## Workflows

- `01-email-manager.json`: filtra correo no prioritario, clasifica estrictamente con Gemini y crea eventos/tareas, resúmenes o borradores LinkedIn.
- `02-laboral.json`: pipeline laboral principal exclusivamente de LinkedIn mediante Playwright (con `linkedin.json`); normaliza, deduplica en PostgreSQL y prepara los resultados nuevos.
- `03-news.json`: resume noticias de economía, IA, tecnología, geopolítica, aeronáutica y espacio sin reenvíos.
- `04-personal-brand.json`: busca noticias de OpenAI, Google, Microsoft, NVIDIA, SpaceX, Airbus, ESA y NASA y guarda borradores LinkedIn.
- `05-playwright-jobs.json`: workflow independiente compatible para ejecutar sólo el pipeline Playwright. La integración principal está en `02-laboral.json`.

### Pipeline Playwright integrado

`02-laboral.json` conecta exclusivamente las ofertas nuevas de LinkedIn obtenidas mediante
Playwright al filtro de sectores, deduplicación, Gemini y WhatsApp. Los disparadores
programado/manual/webhook preparan una solicitud `source=linkedin` y llaman por HTTP a
`PLAYWRIGHT_BASE_URL`. PostgreSQL hace un upsert por `item_key`, pero sólo los registros
insertados en esa ejecución llegan a Gemini/WhatsApp. El webhook exige `source=linkedin`
y rechaza otros orígenes.

### Workflow Playwright Jobs independiente

El workflow `05-playwright-jobs.json` está preparado para n8n dentro del `docker compose`:
usa `http://playwright:3000` mediante `PLAYWRIGHT_BASE_URL`, no expone sesiones ni
credenciales y necesita la credencial PostgreSQL `Postgres assistant`. La ejecución
programada y manual consulta LinkedIn. El webhook
`GET /webhook/assistant/playwright-jobs` exige `source=linkedin`.
El workflow independiente `05-playwright-jobs.json` usa
`GET /webhook/assistant/playwright-jobs-standalone` para evitar conflictos si ambos
workflows están importados y activos.
para consultar un solo origen, además de `location`, `keywords`, `termsPerQuery`, `maxJobsPerSearch`,
`maxScrollSteps`, `gotoTimeout`, `selectorTimeout` y `httpTimeout` (timeout HTTP del
workflow, entre 1000 y 300000 ms). Los parámetros numéricos se validan antes de llamar
al scraper; `maxScrollSteps=0` es válido.

Ejemplo:

```powershell
Invoke-WebRequest 'http://localhost:5678/webhook/assistant/playwright-jobs?source=linkedin&location=Barcelona&keywords=PMO,Operations'
```

Playwright normaliza, deduplica y actualiza `jobs-history.json` antes de responder. El workflow vuelve a validar la forma
estable de cada oferta y usa `assistant_processed_items` para que sólo pasen al
resultado las ofertas nuevas para n8n. La activación del workflow es opcional; se
recomienda probar primero una ejecución manual.

## Scraper de ofertas de LinkedIn

Puedes ejecutar los comandos desde la raíz del proyecto:

```powershell
npm run login
npm run scrape
npm run process
npm run update
npm test
```

El servicio Playwright expone `GET http://localhost:3000/linkedin` y devuelve un array JSON
con las ofertas filtradas. Antes de usarlo, crea una sesión local (se abrirá un navegador
para iniciar sesión manualmente):

```powershell
Set-Location .\playwright
npm run login
npm start
```

Comprueba el servicio con `Invoke-WebRequest http://localhost:3000/health`. La búsqueda
admite `location`, `keywords` (términos separados por comas) y `termsPerQuery`, por ejemplo:

```powershell
Invoke-WebRequest 'http://localhost:3000/linkedin?location=Barcelona&keywords=PMO,Operations'
```

## Scraper público de InfoJobs

InfoJobs dispone de un scraper independiente que no usa credenciales ni `linkedin.json`.
Comprueba `robots.txt` antes de abrir Playwright, aplica los mismos filtros y mantiene sus
propios ficheros `playwright/infojobs-jobs.json` e `playwright/infojobs-history.json`:

```powershell
npm run scrape:infojobs
Invoke-WebRequest 'http://localhost:3000/infojobs?location=Barcelona&keywords=PMO,Operations'
```

La configuración opcional usa `INFOJOBS_LOCATION`, `INFOJOBS_SEARCH_TERMS`,
`INFOJOBS_OUTPUT_FILE`, `INFOJOBS_HISTORY_FILE`, `INFOJOBS_SEARCH_URL` y los límites
`INFOJOBS_*` equivalentes a los de LinkedIn.

La sesión de LinkedIn se guarda sólo en `playwright/linkedin.json`, que está excluida de Git.
El scraper InfoJobs no usa sesión. Ningún pipeline imprime, inspecciona ni copia credenciales
o estados de sesión.

### Pipeline modular

La implementación está separada en `playwright/config.js` (configuración centralizada),
`extractor.js` (DOM), `normalize.js` (modelo estable), `filters.js` (reglas deterministas)
e `history.js` (histórico JSON). `scraper.js` sólo coordina estas etapas. Cada oferta se
deduplica por identificador, URL normalizada o empresa+título+ubicación como fallback, se
escribe en `jobs.json` y se incorpora a `jobs-history.json` (ambos ignorados por Git).
`searchQueries` conserva todas las búsquedas que devolvieron una oferta. El histórico
acepta tanto el formato antiguo de array como el formato versionado
`{ "version": 1, "jobs": [...] }`, por lo que la migración es automática y no destructiva;
registra estados `new`, `known`, `missing`, `closed` y `changed` sin borrar ofertas.

Variables opcionales: `LINKEDIN_LOCATION`, `LINKEDIN_SEARCH_TERMS` (separadas por comas),
`TERMS_PER_QUERY`, `MAX_JOBS_PER_SEARCH`, `MAX_SCROLL_STEPS`, `GOTO_TIMEOUT`,
`SELECTOR_TIMEOUT` y `DIAGNOSTICS_TIMEOUT`,
`SCRAPER_OUTPUT_FILE`, `SCRAPER_HISTORY_FILE`, `SCRAPER_DEBUG_DIR` y
`PLAYWRIGHT_HEADLESS=false`. Los filtros de inclusión/exclusión permanecen en
`config.js` y no requieren IA.

Validación local:

```powershell
Set-Location .\playwright
npm test
npm run check
```

Para reprocesar o actualizar el histórico sin abrir Playwright:

```powershell
npm run process
npm run update
```

## Operación y actualización

Todos los elementos tratados se deduplican en PostgreSQL. Gemini y WhatsApp reintentan tres veces; los fallos permanecen en las ejecuciones y logs de n8n.

Para actualizar, fija primero la versión deseada de n8n en `docker-compose.yml`, realiza copia de seguridad de los volúmenes y ejecuta:

```powershell
docker compose pull
docker compose up -d
```

## Verificación

```powershell
node .\scripts\validate-workflows.js
docker compose config --quiet
docker compose ps
docker compose logs --tail=100 n8n
```

No subas `.env`, tokens OAuth ni exportaciones de credenciales al repositorio.
