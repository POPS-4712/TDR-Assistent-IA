# Fase 2.8 — Informe de integración end-to-end

**Fecha de verificación:** 18 de agosto de 2026  
**Alcance:** Backend local FastAPI, PostgreSQL, n8n local, frontend React y el workflow aislado `test-automation`.  
**Estado final:** **PASS**

> El resultado `PASS` se limita al ciclo E2E aislado y a las pruebas ejecutadas que se documentan abajo. Las automatizaciones reales se conservaron sin ejecutar, porque requieren credenciales funcionales que no se usaron ni se expusieron en esta validación.

## Resultado de infraestructura y pruebas

| Componente o control | Resultado comprobado | Evidencia de ejecución |
|---|---:|---|
| Backend FastAPI | **PASS** | `GET /health` respondió `healthy` después de reconstruir y recrear el contenedor. |
| Public API de n8n | **PASS** | El ciclo aislado pudo importar, activar, desactivar y eliminar un workflow mediante la API pública. |
| Ciclo E2E `test-automation` | **PASS** | Instalación, activación, webhook real, desactivación y desinstalación devolvieron HTTP 200. |
| Estado final del test | **PASS** | Redescubierto como `discovered`; no queda instalado ni activo. |
| Suite backend | **PASS** | `79 passed`, `0 failed`; se observaron 8 advertencias preexistentes de deprecación. |
| Suite frontend | **PASS** | Vitest completó los dos archivos existentes, con 8 pruebas visibles correctas. |
| Build frontend | **PASS** | Vite transformó 73 módulos y generó `dist/` correctamente. |
| Backup de metadata | **PASS** | Exportación, validación, restore en seco y restore idempotente comprobados. |

## Ciclo de vida aislado

| Paso | Endpoint o acción | Resultado |
|---|---|---:|
| Descubrimiento | Manifest local `test-automation` | **PASS** |
| Instalación | `POST /api/v1/automations/test-automation/install` | **200** |
| Activación | `POST /api/v1/automations/test-automation/enable` | **200** |
| Ejecución | `POST /webhook/automation-center-e2e-test` en n8n | **200** |
| Desactivación | `POST /api/v1/automations/test-automation/disable` | **200** |
| Desinstalación | `DELETE /api/v1/automations/test-automation` | **200** |
| Limpieza final | Descubrimiento y consulta posterior | **`discovered`** |

La corrección aplicada para desbloquear este recorrido fue utilizar una **Public API key válida creada en n8n**, cargarla desde el entorno Docker mediante `BaseSettings`, eliminar campos de solo lectura del payload de importación y emplear la ruta de desactivación de Public API. No se imprime, versiona ni documenta el valor de la clave.

## Automatizaciones reales y credenciales

| Automatización | Proveedores detectados | Ejecución en esta fase | Estado |
|---|---|---|---|
| Email Assistant | Google, Gemini, PostgreSQL | No ejecutada | **NOT TESTED** por diseño |
| Laboral | PostgreSQL, Gemini, Telegram | No ejecutada | **NOT TESTED** por diseño |
| News | PostgreSQL, Gemini, WhatsApp Cloud API | No ejecutada | **NOT TESTED** por diseño |
| Personal Brand | PostgreSQL, Gemini, Google | No ejecutada | **NOT TESTED** por diseño |
| Playwright Jobs | PostgreSQL | No ejecutada | **NOT TESTED** por diseño |
| Test Automation | Ninguno | Ejecutada de forma aislada | **PASS** |

El inventario confirma que la automatización News realiza su salida de mensajería contra `graph.facebook.com/.../messages`; por tanto, corresponde a la **WhatsApp Cloud API de Meta**, no a Telegram ni a una integración desconocida. El manifest conserva un requisito explícito de `whatsapp`, mientras las variables de entorno siguen siendo necesarias hasta que exista un proveedor de credenciales gestionadas para ese caso.

## Backup seguro de metadata

El módulo `BackupManager` expone `GET /api/v1/backup/export`, `POST /api/v1/backup/validate` y `POST /api/v1/backup/restore`. La restauración es **dry-run por defecto** y el modo persistente solo inserta metadata que no exista, manteniendo idempotencia.

| Verificación | Resultado |
|---|---:|
| Backup exportado localmente | **PASS** |
| Validación del payload exportado | **PASS** |
| Escaneo de nombres de campos sensibles | **0 coincidencias** |
| Restore en seco | **PASS** |
| Restore persistente aislado | **PASS** |
| Segunda restauración del mismo bundle | **PASS**, 0 perfiles nuevos |
| Limpieza del perfil temporal de prueba | **PASS** |

El backup omite valores y claves identificadas como sensibles, incluidos `api_key`, `token`, `secret`, `password`, `authorization` y claves privadas. No exporta ID de credencial n8n, workflow ID ni estado de activación como si fueran portables entre instancias; al restaurar, las automatizaciones aparecen como `discovered` y las credenciales como `requires_reauth` sin material secreto.

## Seguridad y preservación

| Control | Estado |
|---|---:|
| Claves de API, tokens y secretos en repositorio o salida de pruebas | **PASS**: no se expusieron valores. |
| Workflows reales | **PASS**: no se activaron, editaron ni eliminaron. |
| Credenciales n8n reales | **PASS**: no se exportaron ni modificaron. |
| Datos de producción | **PASS**: el único perfil creado para restore fue temporal y se eliminó. |
| Workflow de prueba | **PASS**: ciclo completado y estado final `discovered`. |

## Observaciones pendientes

La clave de Public API de n8n usada para estas pruebas tiene una expiración operativa. Antes de su renovación o sustitución debe crearse una nueva clave en **Settings → n8n API**, actualizar exclusivamente el entorno local y repetir el smoke test aislado. La advertencia de configuración vacía de Tailwind y las advertencias de deprecación Pydantic/SQLAlchemy son preexistentes; no bloquean los resultados, pero conviene corregirlas en mantenimiento posterior.

## Estado final

**PASS.** El Automation Center local completó un lifecycle real aislado contra n8n y aprobó las suites de regresión y las verificaciones de backup sin secretos. La siguiente incorporación recomendable es modelar la WhatsApp Cloud API como proveedor de credenciales gestionadas, sin migrar ni alterar credenciales ya existentes.
