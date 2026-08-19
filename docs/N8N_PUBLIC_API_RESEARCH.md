# Investigación de autenticación de la Public API de n8n

La documentación oficial de n8n indica que una clave de Public API se crea explícitamente desde **Settings → n8n API → Create an API key**. Esa clave se utiliza en el encabezado `X-N8N-API-KEY`; no se documenta una variable de servidor `N8N_API_KEY` como mecanismo para registrar o aprovisionar automáticamente una clave dentro de n8n.[1]

La Public API de workflow usa como raíz `/api/v1`. La creación de un workflow se realiza mediante `POST /api/v1/workflows` y requiere `name`, `nodes`, `connections` y `settings`; la documentación establece el mismo esquema de autenticación por API key.[2]

La variable `N8N_API_KEY` aparece en la documentación de la CLI oficial como una forma de entregar una clave ya creada al cliente de línea de comandos. Esto confirma que puede ser una variable de cliente o de integración, pero no demuestra que n8n la convierta por sí misma en una clave válida de Public API.[3]

> Hipótesis de trabajo: el valor compartido por Docker Compose se está inyectando tanto en backend como en n8n, pero no corresponde a una clave de Public API creada y asociada a un usuario dentro de la instancia. Por ello n8n responde HTTP 401 aunque el encabezado y la URL del backend sean correctos. Esta hipótesis debe confirmarse en la instancia sin imprimir claves.

## Fuentes

[1]: https://docs.n8n.io/connect/n8n-api/authentication/ "n8n — Authentication"
[2]: https://docs.n8n.io/connect/n8n-api/workflow/ "n8n — Workflow Public API"
[3]: https://docs.n8n.io/connect/n8n-cli/ "n8n — CLI configuration"
