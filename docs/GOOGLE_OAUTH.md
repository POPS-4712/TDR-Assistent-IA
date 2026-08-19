# Google OAuth2

1. En Google Cloud crea o selecciona un proyecto.
2. Activa Gmail API, Google Calendar API, Google Tasks API, Google Docs API y Google Drive API.
3. Configura la pantalla de consentimiento OAuth. Añade tu cuenta como usuario de prueba mientras la aplicación esté en pruebas.
4. Crea un cliente OAuth 2.0 de tipo **Web application**.
5. Añade como URI de redirección autorizada:

   `http://localhost:5678/rest/oauth2-credential/callback`

   Si publicas n8n, usa la URL HTTPS definida en `WEBHOOK_URL` y `N8N_EDITOR_BASE_URL`.
6. En n8n crea las credenciales solicitadas por los nodos Google, usando el client ID y client secret del paso anterior. Asigna el nombre `Google OAuth2` a cada credencial para que coincida con los workflows.
7. Autoriza el acceso a Gmail, Calendar, Tasks, Docs y Drive durante la conexión.

La credencial PostgreSQL se llama `Postgres assistant`: host `postgres`, puerto `5432`, base de datos, usuario y contraseña de `.env`.
