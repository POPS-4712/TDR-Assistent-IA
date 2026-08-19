# Informe de release — Phase 2.13

**Producto:** Automation Center  
**Versión:** 1.0.0  
**Estado del informe:** verificado mediante ejecución local en Windows x64  
**Alcance:** generación nativa disponible, integridad de artefactos, aislamiento de runtime y validación E2E del instalador.

> **Resultado:** la release Windows x64 se ha construido realmente, ha superado el escaneo de artefactos, mantiene hashes SHA-256 verificables y ha completado el ciclo aislado de instalación, inicio, perfil, preflight, respaldo, actualización y desinstalación.

## Resumen ejecutivo

La Phase 2.13 queda completada para **Windows x64**. Se generaron un instalador Inno Setup y un paquete portable ZIP con nombres oficiales, se registraron hashes SHA-256 reales en el manifiesto y se verificó el contenido final mediante escaneo de secretos. La prueba E2E se realizó sobre el instalador final y confirmó que una instalación aislada funciona sin modificar workflows fuente ni interferir con la instancia de desarrollo.

Durante la validación se corrigieron tres condiciones de primera ejecución: el montaje de producción de Playwright ocultaba las dependencias de la imagen, los recursos de Compose usaban nombres globales que podían colisionar con otra instancia y la desinstalación silenciosa solicitaba una confirmación interactiva. Las instalaciones nuevas reciben ahora un sufijo de instancia privado, generado localmente y conservado en su configuración privada. Las instalaciones heredadas sin sufijo mantienen los nombres históricos para preservar compatibilidad.

| Dimensión | Resultado verificado |
|---|---|
| Release Windows x64 | **BUILT** |
| Instalador E2E final | **PASS** |
| Upgrade en sitio | **PASS** |
| Desinstalación silenciosa con preservación de datos | **PASS** |
| Escaneo de artefactos | **PASS** |
| Manifiesto y SHA-256 | **PASS** |
| Regresión backend | **97 passed** |
| Regresión frontend | **11 passed** |

## Artefactos Windows x64 generados

Los dos archivos siguientes existen en `dist/windows-x64/` y se corresponden exactamente con el manifiesto `dist/release-manifest.json`. Los hashes fueron recalculados desde los archivos finales y comparados con los valores declarados.

| Artefacto | Formato | Tamaño | SHA-256 real | Estado |
|---|---:|---:|---|---|
| `AutomationCenter-1.0.0-win-x64.exe` | Instalador Inno Setup | 11,976,279 bytes | `9b8fd5807e44e2abf998a816cf3c791a5b0cd8ee177ad67314e9a448b06f7bc4` | **BUILT / VERIFIED** |
| `AutomationCenter-1.0.0-win-x64.zip` | Portable ZIP | 10,096,482 bytes | `16939ff0f1e445a3954e296e5e49b93bd6757f9b83c9271a24b2503c9ed617f0` | **BUILT / VERIFIED** |

El lanzador `AutomationCenter.exe` extraído del ZIP final fue inspeccionado como Portable Executable y su campo `Machine` es `0x8664`, correspondiente a **AMD64/x64**. El ejecutable exterior del instalador usa el bootstrap estándar de Inno Setup, que se identifica como `0x014C`; esto no cambia la arquitectura x64 del lanzador de la aplicación incluido en la distribución.

## Integridad, secretos y definiciones

El escáner de distribución se ejecutó sobre ambos artefactos finales. La comprobación incluye archivos privados prohibidos, configuraciones runtime y patrones de alta confianza para secretos. La ejecución terminó en **PASS** para el instalador y el ZIP, sin listar valores sensibles.

El manifiesto de release fue validado estructuralmente, y cada SHA-256 declarado se contrastó con el hash calculado del archivo correspondiente. El validador de definiciones de packaging también finalizó correctamente y reconoce el manifiesto como salida legítima, sin aceptar archivos sueltos no verificados en `dist/`.

| Comprobación | Evidencia de ejecución | Estado |
|---|---|---|
| Escaneo del instalador | `scan_artifact.py` sobre el `.exe` final | **PASS** |
| Escaneo del portable | `scan_artifact.py` sobre el `.zip` final | **PASS** |
| Manifiesto de release | Dos entradas `built` con hash no vacío | **PASS** |
| Coincidencia SHA-256 | Hash calculado = hash de manifiesto para ambos archivos | **PASS** |
| Lanzador empaquetado | `AutomationCenter.exe` del ZIP con PE `0x8664` | **PASS** |
| Definiciones de packaging | `validate_definitions.py` | **PASS** |

## Validación E2E del instalador final

La prueba se realizó en un directorio temporal aislado, con `LOCALAPPDATA` y puerto de interfaz propios. Se instaló el ejecutable final, se arrancaron los servicios locales, se verificaron endpoints HTTP, se creó un perfil, se ejecutó preflight sin mutaciones, se creó un respaldo de metadatos, se reinstaló el instalador como actualización y se desinstaló en modo silencioso. La desinstalación normal preservó la configuración y los respaldos de la instancia aislada.

| Etapa | Verificación realizada | Resultado |
|---|---|---|
| Instalación | Instalador silencioso y creación de runtime privado | **PASS** |
| Primera ejecución | Arranque de frontend, backend, PostgreSQL, n8n y Playwright | **PASS** |
| Interfaz y API | `/health`, estado de sistema, perfiles, automatizaciones y cuentas HTTP 200 | **PASS** |
| Perfil | Creación de perfil aislado | **PASS** |
| Preflight | Ejecución con `mutations_applied=false` | **PASS** |
| Respaldo | Archivo de metadatos creado y revisión estructural sin claves sensibles | **PASS** |
| Upgrade | Reinstalación en sitio; perfil y respaldo conservados | **PASS** |
| Uninstall | Desinstalación silenciosa; datos privados conservados | **PASS** |

La salida final de la ejecución fue:

```text
INSTALL_TEST=PASS
UPGRADE_TEST=PASS
UNINSTALL_TEST=PASS
FIRST_RUN_RUNTIME=PASS
PROFILE_PERSISTENCE=PASS
METADATA_BACKUP_SECURITY=PASS
```

## Salvaguardas añadidas y correcciones verificadas

Las instalaciones nuevas ya no comparten por defecto el proyecto, red ni volúmenes de Compose con otras instancias. Al inicializar un runtime nuevo se genera localmente `AUTOMATION_CENTER_INSTANCE_SUFFIX`; el sufijo forma parte del nombre del proyecto de Compose, de la red y de los volúmenes de datos. No se imprime ni se versiona el contenido de `runtime.env`. Si una instalación existente no contiene ese campo, conserva el nombre histórico `automation-center`, lo que evita una migración implícita de sus datos.

El compose de producción dejó de montar el directorio de fuentes Playwright sobre `/app`. Ese montaje ocultaba `node_modules` que se instala durante la construcción de la imagen y provocaba un error de módulo no encontrado en primeras ejecuciones. El servicio se inicia ahora desde el contenido incluido en la imagen de producción.

El backup de metadatos también excluye ajustes cuyos identificadores tengan forma sensible, además de limpiar valores y claves anidadas. La prueba de instalación valida el JSON de respaldo de manera estructural para detectar claves sensibles reales; no considera secreta una mera referencia documental dentro del contenido de un manifiesto.

Por último, la desinstalación silenciosa no abre diálogos y no elimina datos privados. La limpieza automática de la prueba E2E detiene y retira únicamente contenedores y redes de su instancia temporal; **no emplea `--volumes` y no elimina volúmenes Docker**. Los recursos de producción existentes no fueron seleccionados como destino de las pruebas.

## Regresión del producto y estado del desarrollo

La regresión backend se ejecutó dentro del servicio de desarrollo y terminó con **97 pruebas aprobadas**. La suite de frontend se ejecutó en el entorno de desarrollo Node y terminó con **3 archivos y 11 pruebas aprobadas**. El contenedor frontend de producción no incluye npm, por lo que ejecutar la suite allí no era aplicable; la suite se ejecutó correctamente desde el árbol de desarrollo.

| Verificación | Resultado |
|---|---|
| Backend: `python -m pytest -q tests/` | **97 passed** |
| Frontend: `npm run test -- --run` | **3 files, 11 passed** |
| Backend de desarrollo: `/health` | **PASS** |
| Preflight de desarrollo | **6 automatizaciones; `mutations_applied=false`** |
| Frontend de desarrollo | **HTTP 200** |
| Política de caché SPA | `Cache-Control: no-store, no-cache, must-revalidate` |

## Cobertura de plataformas

No se han inventado artefactos para plataformas que no estaban disponibles en el host de construcción. El equipo de ejecución es Windows sobre arquitectura AMD64; por ello solo Windows x64 se declara construido. Los scripts y la automatización CI nativa están preparados, pero no sustituyen una construcción real en un runner compatible.

| Target | Estado | Justificación |
|---|---|---|
| Windows x64 | **BUILT** | Host Windows AMD64, artefactos `.exe` y `.zip` generados y verificados |
| Windows ARM64 | **PLATFORM UNAVAILABLE** | El host es AMD64; no se generó ni se reclama artefacto ARM64 |
| Linux x64 | **PLATFORM UNAVAILABLE** | El host de esta ejecución es Windows; no se generó paquete Linux |
| Linux ARM64 | **PLATFORM UNAVAILABLE** | El host de esta ejecución es Windows y AMD64 |
| macOS x64 | **PLATFORM UNAVAILABLE** | No había host macOS; no se generó DMG |
| macOS ARM64 | **PLATFORM UNAVAILABLE** | No había host macOS ARM64; no se generó DMG |

El workflow `.github/workflows/native-release-builds.yml` queda preparado para construcciones nativas en runners Windows, Linux y macOS, incluidos targets ARM donde el runner correspondiente está disponible. Su preparación no se presenta como una ejecución ni como un artefacto generado.

## Entregables y trazabilidad

| Ruta | Contenido |
|---|---|
| `dist/windows-x64/AutomationCenter-1.0.0-win-x64.exe` | Instalador Windows final verificado |
| `dist/windows-x64/AutomationCenter-1.0.0-win-x64.zip` | Paquete portable Windows final verificado |
| `dist/release-manifest.json` | Inventario de release con SHA-256 reales |
| `packaging/windows/test-installer.ps1` | Prueba E2E aislada y no destructiva para volúmenes |
| `packaging/common/service_manager.py` | Lanzador local, runtime aislado y timeout de primera ejecución |
| `docker-compose.prod.yml` | Composición de producción corregida y aislada |
| `PHASE_2_13_RELEASE_REPORT.md` | Este informe |

## Conclusión

La Phase 2.13 está **completada para Windows x64** con evidencia de build, integridad, seguridad de empaquetado y validación E2E real. Las demás plataformas permanecen correctamente marcadas como **PLATFORM UNAVAILABLE**, sin extensiones ni builds ficticios. El entorno de desarrollo continuó saludable tras la validación y el preflight no aplicó mutaciones a workflows.

> La siguiente construcción para Linux, Windows ARM64 o macOS deberá ejecutarse en un runner nativo de la plataforma y generar sus propios artefactos y hashes antes de que pueda declararse como BUILT.
