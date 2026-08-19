# PHASE 2.8 — FIX GLOBAL BACKEND TESTS / CREDENTIAL STORE

**Fecha de validación:** 18 de agosto de 2026  
**Estado final:** **READY**

## 1. Problema encontrado

La batería completa del backend finalizaba con **63 pruebas correctas y 2 fallos**. Los fallos se concentraban en el almacenamiento seguro de credenciales cuando las pruebas se ejecutaban dentro del contenedor Linux.

| Prueba afectada | Error reproducido |
|---|---|
| `TestSecureStore.test_keyring_store_set_get_delete` | `NoKeyringError`: no había un backend de keyring utilizable en el contenedor. |
| `TestCredentialManager.test_start_oauth_flow` | `RuntimeError`: no existía `/etc/automation-center/system.key` para el vault cifrado seleccionado en contenedores. |

Las dos incidencias pertenecían al entorno de pruebas de `CredentialManager`; no afectaban al sistema de perfiles ni a las automatizaciones existentes.

## 2. Causa raíz

`KeyringSecureStore` usa el backend de keyring del sistema operativo. En el contenedor de pruebas, la biblioteca estaba instalada, pero elegía el backend fallido de keyring al no disponer de un proveedor de escritorio.

De forma independiente, los proveedores OAuth se instancian y registran globalmente. Durante la generación de una URL OAuth almacenan temporalmente el verificador PKCE en su propio `secure_store`. Dentro del contenedor, `get_secure_store()` selecciona `EncryptedFileSecureStore`, que correctamente exige una clave de sistema existente. La ruta de producción `/etc/automation-center/system.key` no debe generarse ni reutilizarse durante pruebas.

## 3. Solución aplicada

Se añadió `backend/tests/conftest.py`, cargado exclusivamente por pytest. La fixture automática de sesión realiza cuatro acciones limitadas al proceso de pruebas:

1. Instala un `InMemoryKeyring` compatible con keyring que conserva los pares servicio/usuario/valor únicamente en memoria.
2. Crea un directorio temporal de pytest y genera con `os.urandom(32)` un material de clave temporal para ese proceso.
3. Construye un `EncryptedFileSecureStore` que apunta a ese directorio temporal y lo asigna solo a los proveedores globales registrados durante la sesión de pruebas.
4. Restaura el backend de keyring original y los `secure_store` originales de los proveedores al finalizar la sesión.

> La fixture no modifica `get_secure_store()`, no cambia rutas ni comportamiento de producción, no escribe en `/etc/automation-center`, no introduce secretos reales y no se incluye en la imagen de producción, ya que el Dockerfile copia únicamente `app/`.

## 4. Archivos modificados

| Archivo | Cambio |
|---|---|
| `backend/tests/conftest.py` | Nueva fixture de pytest con keyring en memoria y vault cifrado temporal, aplicable solo durante pruebas. |

No se modificaron `CredentialManager`, `secure_store.py`, `ProfileManager`, `PersonalizationEngine`, API de perfiles, frontend de perfiles, workflows, n8n, `assistant_processed_items`, tablas internas de n8n ni credenciales reales.

## 5. Tests antes

| Suite | Resultado antes |
|---|---|
| `backend/tests/test_credential_manager.py -v` | 21 PASS, 2 FAIL. |
| Batería completa backend | 63 PASS, 2 FAIL. |
| Perfil y personalización | PASS; sin fallos relacionados. |

## 6. Tests después

| Verificación | Resultado |
|---|---|
| `python -m pytest tests/test_credential_manager.py -v` dentro del backend | **23 passed, 0 failed**. |
| Pruebas de perfiles (`test_personalization_engine`, `test_profile_schemas`, `test_profiles_api`) | **14 passed, 0 failed**. |
| `python -m pytest -q` en toda la batería backend | **65 passed, 0 failed**. |

La suite muestra advertencias preexistentes de APIs deprecadas de Pydantic/SQLAlchemy y de `manifest.dict()`. No son fallos y no se modificaron para mantener el alcance mínimo de esta fase.

## 7. Docker status

La imagen `tdr-assistent-ia-backend` se reconstruyó correctamente mediante Docker Compose. El servicio backend se recreó y alcanzó el estado `healthy`.

| Verificación | Estado |
|---|---|
| Docker build backend | PASS |
| Docker Compose backend recreado | PASS |
| Contenedor backend | PASS — healthy |

## 8. Backend health

La comprobación ejecutada con `curl.exe -sS http://localhost:8000/health` respondió:

```json
{"status":"healthy","app":"Automation Center"}
```

**HEALTH: PASS**

## 9. Security validation

La inspección posterior al reinicio de producción comprobó que el contenedor backend no contiene `/etc/automation-center/system.key` ni `/etc/automation-center/vault.enc` creados por la suite. El resultado fue `TEST_STORAGE_LEAK=PASS`.

La fixture utiliza datos aleatorios efímeros en el directorio temporal de pytest, restaura el estado original al finalizar y no toca claves de n8n, tokens OAuth, API keys, credenciales reales, configuración de producción ni bases de datos.

| Control | Estado |
|---|---|
| Keyring de pruebas solo en memoria | PASS |
| Clave temporal solo durante pytest | PASS |
| Sin secretos reales ni claves de producción | PASS |
| Sin modificación de `N8N_ENCRYPTION_KEY` o `N8N_API_KEY` | PASS |
| Sin modificación de perfiles, workflows o tablas n8n | PASS |
| Sin filtración de clave o vault temporal al contenedor de producción | PASS |

## Resultado requerido

```text
BACKEND TESTS:
PASS: 65
FAIL: 0

PROFILE TESTS:
PASS

CREDENTIAL TESTS:
PASS

DOCKER:
PASS

HEALTH:
PASS

SECURITY:
PASS

FINAL STATUS:
READY
```
