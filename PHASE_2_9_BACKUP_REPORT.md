# Fase 2.9 — Informe de backup y restore de metadata

**Fecha de verificación:** 18 de agosto de 2026  
**Estado final:** **PASS**

## Objetivo

Esta fase incorpora un mecanismo portable de backup para el Automation Center local. Conserva únicamente **metadata de configuración** suficiente para reconstruir catálogo y personalización, sin exportar secretos, credenciales n8n, workflows activos ni historial de ejecución potencialmente sensible.

> El backup no reemplaza una copia de seguridad completa de PostgreSQL o n8n. Es una exportación segura de configuración de Automation Center.

## Contrato HTTP

| Método | Ruta | Propósito | Salvaguarda |
|---|---|---|---|
| `GET` | `/api/v1/backup/export` | Exporta metadata portable. | Filtra secretos y añade `integrity_sha256`. |
| `POST` | `/api/v1/backup/validate` | Revisa el bundle sin persistir. | Rechaza campos sensibles y checksums inválidos con HTTP 422. |
| `POST` | `/api/v1/backup/restore` | Simula o restaura metadata válida. | `dry_run=true` por defecto; inserción idempotente cuando se habilita. |

## Contenido incluido y exclusiones

| Área | Tratamiento | Justificación |
|---|---|---|
| Automatizaciones | ID, nombre, descripción, versión y dependencias. | Permite recuperar el inventario local. |
| Estado, workflow ID y activación n8n | Excluidos del restore portable. | Son referencias específicas de una instancia. |
| Credenciales | Solo proveedor, cuenta, scopes y estado `requires_reauth`. | Indica qué reconectar sin transportar material de autenticación. |
| `n8n_credential_id` | Excluido. | No es una referencia portable. |
| Settings, perfiles y templates | Incluidos tras filtrado recursivo. | Preservan configuración y personalización no sensible. |
| Manifests | Incluidos como YAML sanitizado. | Conservan requisitos declarativos. |
| Ejecuciones y resultados | Excluidos. | No son necesarios para restaurar configuración y pueden incluir payloads sensibles. |

## Protección e idempotencia

El exportador remueve recursivamente claves cuyo nombre contenga `api_key`, `apikey`, `access_token`, `refresh_token`, `token`, `secret`, `password`, `authorization`, `private_key` o `encryption_key`. El validador impide restaurar cualquier payload que presente dichos campos, incluso anidados. Si el backup exportado contiene suma de integridad, el validador calcula nuevamente el SHA-256 y rechaza alteraciones.

En modo persistente, la restauración agrega solamente metadata ausente. No duplica automatizaciones, credenciales equivalentes, settings, templates ni perfiles con el mismo nombre. Las automatizaciones restauradas quedan como `discovered` y las credenciales como `requires_reauth`.

## Evidencia de verificación

| Verificación | Resultado |
|---|---:|
| Exportar metadata actual | **PASS** — 6 automatizaciones y 6 manifests. |
| Validar el bundle exportado | **PASS** |
| Escaneo de nombres de campos sensibles | **PASS** — 0 coincidencias. |
| Restore en seco | **PASS** |
| Restore persistente de perfil temporal | **PASS** — 1 perfil creado. |
| Repetir el mismo restore | **PASS** — 0 perfiles nuevos. |
| Limpieza del perfil temporal | **PASS** |
| Rechazar checksum inválido | **PASS** |
| Pruebas unitarias específicas | **PASS** — 9 pruebas. |
| Suite backend completa | **PASS** — 79 pruebas, 0 fallos. |

## Operación recomendada

Primero se debe exportar el JSON y guardarlo en un medio local protegido. Después se debe enviar a `/validate`; a continuación se recomienda invocar `/restore` con el valor predeterminado `dry_run=true`. Solo una solicitud explícita con `dry_run=false` inserta metadata no existente. El proceso no activa workflows ni repone secretos: tras restaurar, cada cuenta debe reautorizarse desde el gestor de credenciales.

## Resultado final

**PASS.** El Automation Center dispone de exportación, validación y restauración local de metadata no sensible, con simulación por defecto, bloqueo de campos sensibles, verificación de integridad e idempotencia comprobada.
