# Actualización segura de Automation Center

**Versión de producto:** `1.0.0`

> Una actualización normal reemplaza la aplicación, no los datos de usuario. Los perfiles, metadata de automatizaciones, metadata de cuentas, backups y volúmenes de PostgreSQL/n8n se conservan.

## Flujo de actualización

El proceso de actualización debe usar un instalador o paquete de la misma arquitectura que la instalación existente. Antes de sustituir la aplicación, el lanzador solicita un backup de metadata al backend local. El backup existente excluye secretos y se valida antes de guardarse en el directorio privado de `backups`.

| Etapa | Acción | Protección |
|---|---|---|
| Detección | El instalador identifica una instalación existente por su identificador de aplicación y directorio de datos. | No crea una segunda raíz de datos sin necesidad. |
| Backup | El lanzador invoca `backup-metadata` antes de actualizar. | El guardia local rechaza metadata que contenga marcadores sensibles. |
| Sustitución | Se actualizan binarios, frontend y composición de producción. | El archivo `runtime.env` y los volúmenes no se incluyen en el paquete. |
| Migración | El backend ejecuta migraciones no destructivas al arrancar. | La configuración actual conserva `ENABLE_DATABASE_MIGRATIONS=true`. |
| Verificación | El lanzador comprueba la salud de backend, PostgreSQL, n8n y Playwright. | Las credenciales externas no se verifican ni se inventan. |

La actualización Windows usa `packaging/windows/upgrade-windows.ps1` como flujo de referencia. Si existe una instalación previa, el script cancela la actualización cuando el backup de metadata no se completa correctamente. Los instaladores de otras plataformas siguen el mismo principio: preservar datos y detenerse antes de una sustitución insegura.

## Datos que se conservan

| Elemento | Actualización normal | Exportación de metadata |
|---|---|---|
| Perfiles y plantillas | Se conserva | Se incluye, sin secretos |
| Metadata de automatizaciones | Se conserva | Se incluye |
| Metadata pública de cuentas | Se conserva | Se incluye, sin tokens |
| Credential vault | Se conserva localmente | No se incluye |
| PostgreSQL | Volumen conservado | No se copia como secreto en el paquete |
| n8n | Volumen conservado | No se copia como secreto en el paquete |
| `runtime.env` | Se conserva en datos de usuario | No se incluye |
| Logs y backups | Se conserva | Los backups se mantienen en el directorio privado |

## Recuperación y validación

Si una actualización se interrumpe antes de iniciar los nuevos servicios, no se deben borrar los volúmenes de producción ni el directorio de usuario. Se puede reinstalar el mismo paquete de arquitectura o ejecutar una reparación. Tras recuperar el runtime, la ruta **System** muestra los estados de servicio y el backend conserva sus migraciones idempotentes.

Un backup de metadata puede comprobarse y restaurarse mediante la API local de backup. La restauración se mantiene en modo seguro y no recupera valores de credenciales. Restaurar metadata no sustituye un volumen PostgreSQL ni una configuración secreta de n8n.

## Cambio de arquitectura o plataforma

No hay actualización directa entre x64 y ARM64. El usuario debe instalar una distribución nativa para el nuevo equipo, configurar un directorio de datos compatible y realizar una migración de datos explícita. No se debe copiar `runtime.env`, keyrings, tokens OAuth ni volúmenes Docker entre arquitecturas sin un procedimiento de migración aprobado.

## Reparación

La opción **Repair** del instalador vuelve a instalar los archivos de aplicación y revalida el runtime local. No borra perfiles, datos, backups ni volúmenes. Si el runtime de contenedores no está disponible, la reparación informa el estado y no intenta finalizar procesos externos.
