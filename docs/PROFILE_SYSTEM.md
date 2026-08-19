# Sistema de perfiles y personalización

## Propósito y límites arquitectónicos

El sistema de perfiles convierte **contexto personal o profesional** en preferencias y configuraciones por automatización. Está diseñado para una instalación **local-first y de usuario único**: una misma persona puede mantener varios perfiles y seleccionar uno como activo, sin que los perfiles representen cuentas, organizaciones o sesiones de autenticación.

> **Separación obligatoria:** un perfil determina el contexto; una automatización determina la funcionalidad; una credencial determina el acceso a servicios externos. Ninguna de estas tres responsabilidades se almacena o gestiona en la capa de las otras.

La implementación se integra sobre el backend FastAPI, PostgreSQL y el frontend React existentes. No crea workflows por profesión, no modifica archivos de workflow de n8n y no realiza operaciones contra el Credential Manager, `AutomationManager` ni `N8NClient`.

| Capa | Responsabilidad del sistema de perfiles | Exclusiones explícitas |
|---|---|---|
| Frontend React | Crear, seleccionar, editar, duplicar, exportar e importar perfiles; presentar el contexto activo. | No conecta directamente con PostgreSQL, n8n, Playwright ni el almacén de credenciales. |
| API FastAPI | Validar solicitudes, aplicar reglas de negocio y devolver respuestas saneadas. | No devuelve secretos ni administra tokens. |
| Servicio de perfiles | Persistir datos, mantener un único perfil activo y construir contexto. | No instala, activa ni reescribe workflows. |
| Personalization Engine | Derivar filtros, términos y preferencias para capacidades genéricas como noticias, empleo, correo y marca personal. | No contiene profesiones codificadas ni credenciales. |
| PostgreSQL | Guardar metadatos y preferencias no sensibles. | No almacena claves API, tokens OAuth, contraseñas, secretos de cliente ni claves de cifrado. |

## Flujo de datos

```text
Usuario local
  ↓
Perfil activo
  ↓
PersonalizationEngine
  ↓
Configuración específica del perfil
  ↓
Automatización genérica existente
  ↓
n8n / IA / servicios externos
```

El cambio de perfil modifica exclusivamente el contexto, filtros, preferencias y configuraciones por perfil. No borra credenciales, no crea credenciales nuevas y no reinstala ni modifica workflows.

## Modelo de perfil

Un perfil es flexible y está compuesto por campos libres, etiquetas y preferencias. No existe una lista cerrada de profesiones. Las plantillas son únicamente puntos de partida editables.

| Grupo | Campos principales |
|---|---|
| Identidad de perfil | `id`, `name`, `description`, `is_active`, `is_enabled`, fechas de creación y actualización. |
| Profesión | Nombre libre, sector y nivel. |
| Contexto | Intereses ponderados, habilidades, empresas, ubicaciones, idiomas, temas y temas excluidos. |
| Objetivos | Lista editable de objetivos, como noticias, empleo, investigación, formación o marca personal. |
| Preferencias | Frecuencia, relevancia, fuentes, horario, notificaciones y ajustes adicionales no sensibles. |
| Automatizaciones | Relaciones con identificadores de automatizaciones existentes, indicador de habilitación y configuración JSON no sensible. |

El frontend crea perfiles mediante un asistente de ocho pasos: nombre, profesión, sector, intereses, objetivos, ubicación, idiomas y preferencias. Posteriormente, el editor permite ajustar todos los campos y guardar una configuración JSON por automatización.

## Base de datos y migración

Las migraciones idempotentes se ejecutan en el inicio del backend desde `backend/app/database/migrations.py`. Añaden únicamente tablas de la funcionalidad de perfiles y sus índices. No alteran `assistant_processed_items`, las tablas internas de n8n, `credentials`, workflows ni volúmenes existentes.

| Tabla | Finalidad | Integridad |
|---|---|---|
| `profiles` | Identidad, profesión, objetivos, idiomas y estado del perfil. | UUID, nombre único e índice parcial que impide más de un perfil activo. |
| `profile_preferences` | Frecuencia, fuentes, notificaciones y ajustes no sensibles. | Relación uno a uno con borrado en cascada. |
| `profile_interests` | Etiquetas de interés con peso entre 1 y 10. | Relación con perfil, unicidad por perfil y nombre. |
| `profile_skills` | Habilidades. | Relación con perfil y unicidad por perfil y nombre. |
| `profile_companies` | Empresas u organizaciones relevantes. | Relación con perfil y unicidad por perfil y nombre. |
| `profile_locations` | Ubicaciones y preferencia de trabajo remoto. | Relación con perfil y unicidad por perfil y valor. |
| `profile_topics` | Temas de interés. | Relación con perfil y unicidad por perfil y nombre. |
| `profile_automations` | Configuración aislada para una automatización existente. | Claves foráneas a `profiles` y `automations`; borrado en cascada. |
| `profile_templates` | Plantillas integradas o futuras plantillas locales. | Identificador estable, datos JSON no sensibles e índice de sistema. |

La activación usa una actualización transaccional: desactiva cualquier perfil activo y activa el seleccionado. Al eliminar el perfil activo, se selecciona el primer perfil habilitado restante, si existe.

## API REST

Todas las rutas se exponen bajo `/api/v1/profiles` y usan esquemas Pydantic con campos adicionales prohibidos. Los identificadores de perfil son UUID.

| Método y ruta | Operación |
|---|---|
| `GET /profiles` | Lista perfiles, con el activo al inicio. |
| `POST /profiles` | Crea un perfil desde cero. |
| `GET /profiles/templates` | Devuelve las plantillas iniciales. |
| `POST /profiles/from-template/{template_id}` | Crea un perfil normal y editable desde una plantilla. |
| `POST /profiles/import` | Restaura un paquete JSON de exportación validado. |
| `GET /profiles/{id}` | Devuelve el detalle seguro de un perfil. |
| `PUT /profiles/{id}` | Actualiza campos declarados del perfil. |
| `DELETE /profiles/{id}` | Elimina el perfil y sus relaciones dependientes. |
| `POST /profiles/{id}/duplicate` | Crea una copia inactiva con nombre único. |
| `POST /profiles/{id}/activate` | Establece el perfil activo. |
| `GET /profiles/{id}/export` | Devuelve un paquete portable sin secretos ni metadatos de credenciales. |
| `GET /profiles/{id}/automations` | Lista las configuraciones por automatización. |
| `PUT /profiles/{id}/automations/{automation_id}` | Guarda una configuración no sensible para una automatización existente. |
| `GET /profiles/{id}/context` | Devuelve contexto estructurado y configuraciones derivadas para consumidores de automatización o IA. |

Las respuestas de error son estructuradas. Los errores no previstos se registran en el servidor y devuelven un mensaje genérico al cliente, sin trazas ni detalles de infraestructura.

## Plantillas iniciales

Las plantillas se siembran de forma idempotente al solicitar el catálogo. Se entregan catorce perfiles iniciales editables: Business & Management, Derecho, Economía & Finanzas, Tecnología, Ingeniería, Ingeniería Aeroespacial, Medicina, Ciencia, Marketing, Arquitectura, Educación, Periodismo, Estudiante y Emprendedor.

Una plantilla contiene profesión, intereses, temas, habilidades, objetivos y preferencias de partida. La plantilla no instala automatizaciones, no contiene cuentas y no restringe los campos que la persona puede modificar.

## Personalization Engine

`PersonalizationEngine` es una capa pura sin acceso a red, secretos ni base de datos. Recibe una representación segura de perfil y genera valores iniciales por **capacidad de automatización**, no por profesión. Las categorías derivadas son `news`, `jobs`, `email` y `personal_brand`.

| Capacidad | Datos derivados del perfil |
|---|---|
| Noticias | Temas, intereses ponderados, empresas, temas excluidos, idioma, frecuencia, fuentes y relevancia. |
| Empleo | Profesión libre, sector, habilidades, ubicaciones, preferencia remota, objetivos y palabras clave. |
| Correo | Idioma, objetivos y prioridad de relevancia. |
| Marca personal | Temas, sector de audiencia, idioma y objetivos. |

Las relaciones entre profesión y resultados no están codificadas. Por ejemplo, las palabras de empleo parten de la profesión y las habilidades que el usuario haya introducido; una persona puede editar manualmente la configuración JSON correspondiente a una automatización concreta.

Una configuración almacenada en `profile_automations` se combina sobre la configuración derivada. La combinación no toca el archivo de workflow, ni la instalación de n8n, ni el mapeo de credenciales.

## Seguridad

La seguridad del sistema se aplica en la API antes de llegar a los servicios de persistencia. Los esquemas rechazan campos no declarados y nombres sensibles como `api_key`, `access_token`, `refresh_token`, `client_secret`, `password`, `credential` y variantes equivalentes. También bloquean patrones comunes de valores secretos, incluidos tokens con prefijos de proveedores y JWT.

| Control | Aplicación |
|---|---|
| Prevención de secretos | Validación recursiva de cargas de creación, actualización, importación, preferencias y configuraciones. |
| Prevención de inyección | Pydantic valida tipos y límites; SQLAlchemy usa consultas parametrizadas y claves foráneas. |
| Prevención de XSS | React representa contenido como texto; no se inserta HTML del perfil. |
| Prevención de path traversal | La importación procesa contenido JSON en memoria y no acepta rutas del cliente. |
| Separación de credenciales | No hay relación de almacenamiento entre `profiles` y `credentials`; solo se permite referenciar automatizaciones existentes. |
| Exportación segura | El paquete contiene preferencias y configuración no sensible, nunca tokens, claves o contraseñas. |
| Registros saneados | Las operaciones registran identificadores y estados, no los contenidos de perfiles ni secretos. |

## Importación, exportación y restauración

La exportación devuelve un paquete con `schema_version`, `exported_at` y `profile`. El bloque de perfil contiene el contexto portable, preferencias y configuraciones no sensibles. La misma estructura puede volver a enviarse a `POST /profiles/import`; el campo temporal `exported_at` se acepta para asegurar un ciclo de restauración directo.

Desde la interfaz, **Exportar** descarga un archivo JSON local. **Importar** lee un archivo JSON elegido por el usuario y lo valida en FastAPI. Si se detecta un campo o valor sensible, el backend rechaza la restauración.

## Interfaz de usuario

La sección **Profiles** está disponible desde la navegación principal. El selector global aparece en la cabecera y permite cambiar el perfil activo o iniciar uno nuevo. El dashboard incorpora una tarjeta de perfil activo con resumen de intereses y objetivos; las métricas y ejecuciones existentes permanecen separadas y sin cambios de comportamiento.

La pantalla de perfiles proporciona lista, edición, duplicación, activación, desactivación, importación, exportación, plantillas y asistente. Todas las peticiones se hacen a FastAPI mediante el cliente HTTP centralizado.

## Pruebas relevantes

Las pruebas de perfiles cubren la derivación de contexto, los filtros de secretos, la compatibilidad del paquete de importación/exportación y el contrato de rutas HTTP. Las pruebas del adaptador frontend cubren las rutas de listado, activación e importación. Las verificaciones concretas y sus resultados se recogen en `PHASE_PROFILE_SYSTEM_REPORT.md`.
