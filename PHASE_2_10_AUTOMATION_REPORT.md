# Informe de Phase 2.10: operación automática y preflight seguro

**Proyecto:** Automation Center / TDR-Assistent-IA  
**Fecha de verificación:** 19 de agosto de 2026  
**Estado:** **PASS con bloqueos explícitos de dependencias reales**

## Resumen ejecutivo

Phase 2.10 incorpora una experiencia de operación automática para las automatizaciones locales. Al abrir la vista **Automations**, el sistema descubre los manifests disponibles, ejecuta un preflight global de solo lectura y presenta el estado resultante sin importar, activar ni ejecutar workflows reales. El sistema diferencia una automatización preparada de una automatización bloqueada por requisitos reales, sin revelar secretos ni referencias internas de n8n.

La incidencia visual del frontend se resolvió mediante una configuración explícita de Tailwind y una política de no caché para el documento SPA. La interfaz local respondió correctamente en `http://localhost:3001/automations` y fue confirmada visualmente en el navegador del usuario.

| Área verificada | Resultado |
|---|---:|
| Backend `/health` | **healthy** |
| Endpoint automático `POST /api/v1/automations/preflight` | **PASS** |
| Mutaciones del preflight | **False** |
| Automatizaciones evaluadas | **6** |
| Automatizaciones reales bloqueadas de forma segura | **5** |
| Automatización de prueba | **ready / discovered** |
| Regresión backend | **85 passed** |
| Build y pruebas frontend | **PASS; 8 tests passed** |
| Documento SPA sin caché | **PASS** |

## Flujo automático implementado

El backend incorpora el preflight global `POST /api/v1/automations/preflight`. Este flujo descubre los manifests locales y evalúa cada automatización sin invocar importación, activación, ejecución ni modificación de workflows en n8n. La respuesta publica únicamente estados, requisitos y comprobaciones no sensibles.

La interfaz consume este preflight al cargarse. En consecuencia, no depende de que el usuario pulse **Discover** para detectar los requisitos pendientes. Las automatizaciones con dependencias faltantes se muestran como **Bloqueada** y explican que volverán a evaluarse automáticamente, sin importar el workflow mientras los requisitos no estén satisfechos.

> El preflight es una barrera de seguridad, no una ejecución. Su respuesta validada mantiene `mutations_applied: false`.

## Estado factual de las automatizaciones

| Automatización | Estado de preflight | Resultado operativo |
|---|---:|---|
| `test-automation` | `ready` | Permanece `discovered`; no está instalada ni activa. |
| `playwright-jobs` | `blocked` | Requiere dependencias de ejecución y credencial compatible antes de importarse. |
| `laboral` | `blocked` | Requiere credenciales y dependencias declaradas. |
| `news` | `blocked` | Requiere providers y trigger configurado. |
| `personal-brand` | `blocked` | Requiere providers y trigger configurado. |
| `email-assistant` | `blocked` | Requiere proveedores Google/PostgreSQL compatibles. |

Los estados bloqueados son correctos y protectores: se derivan de requisitos faltantes, no de errores de importación. No se conectaron cuentas reales, no se ejecutaron mensajes ni solicitudes externas y no se modificaron los workflows fuente.

## Seguimiento de perfil y ejecuciones

Se amplió el contrato no sensible de ejecuciones con `profile_id` y `duration_ms`. Los logs de automatizaciones exponen estos campos cuando existan, sin incluir secretos, tokens, valores de configuración, referencias internas de n8n ni payloads sensibles adicionales.

| Campo | Finalidad | Contenido permitido |
|---|---|---|
| `profile_id` | Asociar una ejecución al perfil de contexto | Identificador no sensible del perfil |
| `duration_ms` | Medir duración de una ejecución | Entero no negativo |
| `status` | Estado operacional | Estado de ejecución no sensible |

## Corrección de la interfaz local

La interfaz inicialmente cargaba el documento HTML pero no las utilidades de Tailwind, debido a que faltaba `tailwind.config.js`. Se añadió la configuración de rutas de contenido y se realizó una compilación sin caché. El CSS generado pasó de aproximadamente 4,93 KB a 23,43 KB, incorporando las clases requeridas por la interfaz.

Además, Nginx ahora responde las rutas SPA con `Cache-Control: no-store, no-cache, must-revalidate`. Los bundles estáticos conservan sus nombres versionados; el navegador no conserva un documento HTML antiguo que pudiera referenciar assets de una compilación anterior.

## Límites inevitables

La automatización del proceso no puede ni debe fabricar credenciales, tokens, permisos OAuth o endpoints de terceros inexistentes. El sistema resuelve esto de forma automática mediante preflight: detecta las ausencias, bloquea antes de importar y vuelve a evaluar en futuras cargas. Cuando una cuenta real esté disponible en el almacén seguro y sea compatible con el tipo n8n requerido, la automatización podrá pasar de `blocked` a preparada sin modificar el workflow fuente.

## Evidencia de limpieza

La automatización `test-automation` quedó en estado `discovered` después de las verificaciones. No quedan workflows de prueba activos. El preflight global declarado como automático mantuvo `mutations_applied: false` para las seis automatizaciones revisadas.
