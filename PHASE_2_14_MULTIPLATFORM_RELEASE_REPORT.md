# Informe de release multiplataforma — Phase 2.14

**Producto:** Automation Center  
**Versión objetivo:** 1.0.0  
**Fecha de verificación:** 19 de agosto de 2026  
**Resultado de release pública multiplataforma:** **BLOCKED**

> La pipeline CI/CD está implementada y validada estáticamente, y Windows x64 cuenta con artefactos reales verificados localmente. No se ha declarado ni creado una release pública `v1.0.0`: no existe evidencia de ejecuciones nativas de GitHub Actions para los seis targets obligatorios.

## Resumen ejecutivo

La Phase 2.14 convierte `.github/workflows/native-release-builds.yml` en una pipeline de release nativa con una matriz explícita de seis targets. Cada target usa un runner compatible con su arquitectura, ejecuta pruebas backend y frontend antes del build, exige artefactos con nombre exacto y tamaño positivo, escanea seguridad, valida arquitectura y registra hashes SHA-256. El ensamblado final descarga exclusivamente los outputs de los jobs nativos, vuelve a validar el manifiesto y genera `SHA256SUMS.txt`.

La publicación de GitHub está separada de los workflow artifacts. Solo puede ocurrir cuando se ha solicitado `target=all`, todos los jobs de la matriz han terminado correctamente, el ensamblado ha verificado los diez archivos esperados y se solicita de forma explícita `create_release=true`. Una ejecución individual o parcial puede conservar su evidencia como artifact del workflow, pero no puede crear la release pública.

| Aspecto | Estado |
|---|---|
| Matriz CI/CD de seis targets | **IMPLEMENTED / STATICALLY VALIDATED** |
| Preflight de versión, integridad y scripts | **IMPLEMENTED** |
| Tests backend y frontend previos | **IMPLEMENTED / LOCAL PASS** |
| Escaneo y SHA-256 por artefacto | **IMPLEMENTED / WINDOWS x64 PASS** |
| Workflow artifacts | **IMPLEMENTED, NOT EXECUTED REMOTELY** |
| GitHub release `v1.0.0` | **BLOCKED** |

## Pipeline implementada

El workflow `native-release-builds.yml` dispone de cinco etapas. La primera comprueba `VERSION=1.0.0`, el estado limpio del checkout, los scripts requeridos y la definición estática de la propia matriz. El job de build ejecuta la matriz nativa. Cada job instala dependencias deterministas, ejecuta `python -m pytest -q tests/`, ejecuta `npm test -- --run` y `npm run build`, construye solo mediante el script de su plataforma y vuelve a comprobar los artefactos producidos.

La tercera etapa descarga los artifacts de los seis jobs, ensambla un único `dist/release-manifest.json`, verifica hashes de los archivos copiados y genera `dist/SHA256SUMS.txt`. La cuarta etapa, separada, puede publicar con `gh release create`, pero su condición requiere el éxito del ensamblado completo y la opción explícita de publicación. Por tanto, un build parcial nunca recibe el tag `v1.0.0`.

| Job | Responsabilidad | Condición de publicación |
|---|---|---|
| `preflight` | Versión, checkout limpio, integridad de fuentes y definición CI | Obligatorio para toda la matriz |
| `build` | Tests, build nativo, arquitectura, scan, manifiesto y artifact por target | Un job por target nativo |
| `assemble-release` | Descarga, unión, revalidación, `SHA256SUMS.txt` | Solo `target=all` y matriz completa exitosa |
| `publish-release` | Adjunta los diez binarios y metadatos al tag `v1.0.0` | Solo `target=all`, ensamblado exitoso y `create_release=true` |

## Matriz de runners nativos

La matriz evita cross-build. Los nombres de runners se contrastaron con la referencia de runners hospedados de GitHub, que identifica `windows-11-arm`, `ubuntu-24.04-arm`, `macos-26-intel` y `macos-26` como opciones con las arquitecturas correspondientes. [1] [2]

| Target | Runner configurado | Arquitectura exigida | Formatos esperados | Validación nativa |
|---|---|---|---|---|
| `windows-x64` | `windows-latest` | AMD64 | `.exe`, `.zip` | PE del lanzador incluido en ZIP = `0x8664` |
| `windows-arm64` | `windows-11-arm` | ARM64 | `.exe`, `.zip` | PE del lanzador incluido en ZIP = `0xAA64` |
| `linux-x64` | `ubuntu-24.04` | x86_64 | `.deb`, `.tar.gz` | `dpkg-deb` y ELF x86-64 |
| `linux-arm64` | `ubuntu-24.04-arm` | aarch64 | `.deb`, `.tar.gz` | `dpkg-deb` y ELF AArch64 |
| `macos-x64` | `macos-26-intel` | x86_64 | `.dmg` | `file`, `codesign` y bundle montado |
| `macos-arm64` | `macos-26` | arm64 | `.dmg` | `file`, `codesign` y bundle montado |

Los scripts de packaging se endurecieron para rechazar un payload de arquitectura incorrecta: Windows inspecciona el campo `Machine` del PE de `AutomationCenter.exe`; Linux inspecciona el binario en staging, dentro del DEB extraído y dentro del TAR.GZ extraído; macOS revisa el binario del bundle antes y después de montar el DMG. Ninguno de estos controles acepta solo el nombre del archivo como prueba de arquitectura.

## Integridad, seguridad y reproducibilidad

El preflight remoto exige un checkout limpio mediante `git status --porcelain`, `git diff --exit-code` y `git diff --cached --exit-code`. Un checkout con cambios no esperados no llega a construir ni publicar. El manifiesto ampliado registra para cada artefacto real `filename`, `version`, `platform`, `architecture`, `format`, `sha256`, `size`, `status=BUILT` y `validated=true`.

Cada target puede registrar procedencia con el commit, sistema operativo del runner, arquitectura del runner, timestamp y versiones de Python y Node. El flujo de CI marca esa procedencia como `source_integrity=clean`; el build local realizado durante esta fase se identifica honestamente como `dirty`, por haberse efectuado sobre un árbol local no limpio.

| Salvaguarda | Implementación |
|---|---|
| Secretos y archivos privados | `scan_artifact.py` en staging y en cada archivo final; nunca imprime coincidencias |
| Archivo vacío o ausente | Check de existencia y tamaño positivo antes de registrar o subir |
| SHA-256 | Recalculado al registrar, ensamblar y verificar; `SHA256SUMS.txt` generado desde el manifiesto |
| Arquitectura falsa | Checks PE/ELF/DEB/bundle por plataforma |
| Fuente no reproducible | Preflight remoto exige checkout sin diff ni ficheros no versionados |
| Release parcial | El ensamblado y la publicación requieren los seis targets y diez outputs esperados |

## Evidencia local ejecutada

La máquina local es Windows 11 Home AMD64. En ella se ejecutaron los checks que no requieren un runner extranjero. La suite backend terminó con **97 pruebas aprobadas**. La suite frontend terminó con **3 archivos y 11 pruebas aprobadas**, y `npm run build` construyó correctamente la salida de producción. El instalador Windows x64 regenerado superó además la prueba E2E de instalación, primer arranque, perfil, preflight, backup de metadatos, upgrade y desinstalación preservando datos.

| Comprobación | Evidencia | Resultado |
|---|---|---|
| Backend | `python -m pytest -q tests/` | **97 passed** |
| Frontend tests | `npm test -- --run` | **3 files, 11 passed** |
| Frontend build | `npm run build` | **PASS** |
| Definiciones de packaging | `validate_definitions.py` | **PASS** |
| Matriz CI/CD | `validate_release_ci.py` | **PASS** |
| Manifiesto Windows local | `release_manifest.py verify` | **PASS** |
| Seguridad del `.exe` y `.zip` | `scan_artifact.py` | **PASS** |
| Payload Windows portable | PE `Machine=0x8664` | **PASS** |
| Instalador Windows x64 | `test-installer.ps1` | **PASS** |

## Artefactos reales disponibles

Los únicos artefactos declarados como construidos son los producidos localmente para Windows x64. Sus hashes se recalcularon y coinciden con el manifiesto y con `SHA256SUMS.txt`.

| Archivo | Tamaño | SHA-256 | Build | Security | Arquitectura |
|---|---:|---|---|---|---|
| `AutomationCenter-1.0.0-win-x64.exe` | 11,983,720 bytes | `d8775085d693b05c3fea198895ed4d0d2d6135d2283fdc8436d19d29f22c269c` | **BUILT** | **PASS** | Instalador con payload x64 validado |
| `AutomationCenter-1.0.0-win-x64.zip` | 10,107,128 bytes | `44ffa0506ff0fc27f6aae99ee03fb22575bc961ade704139418fbe7663d74949` | **BUILT** | **PASS** | `AutomationCenter.exe` PE `0x8664` |

La procedencia del build local registra el commit `9df32d656de48c76d976dde0f7ce3d9e20368adc`, Windows AMD64, Python 3.14.6 y Node v24.19.0. La misma entrada contiene `source_integrity=dirty`; por ello este build es evidencia de artefacto local real, pero no es evidencia apta para una release reproducible de un commit limpio.

## Targets no generados y estado de GitHub Actions

El host local no puede construir Windows ARM64, Linux ni macOS de forma nativa. La prueba explícita de Windows ARM64 devolvió `PLATFORM UNAVAILABLE` porque el host es x64. Los directorios de distribución de Windows ARM64, Linux x64, Linux ARM64, macOS Intel y macOS ARM64 contienen **cero archivos**. No se crearon extensiones ni paquetes simulados.

Tampoco se ejecutó la pipeline en GitHub Actions. El repositorio local no tiene remoto configurado, la integración GitHub está deshabilitada y el árbol de trabajo actual contiene modificaciones y archivos no versionados que el preflight remoto rechazaría. Esas condiciones impiden una ejecución y una publicación seguras sin alterar credenciales ni cambios del propietario.

| Target | Build | Tests | Security | Estado |
|---|---|---|---|---|
| WINDOWS X64 | Local, real | 97 backend; 11 frontend; E2E PASS | PASS | **BUILT / VALIDATED LOCAL** |
| WINDOWS ARM64 | No ejecutado | No ejecutado | No ejecutado | **PLATFORM_UNAVAILABLE LOCAL** |
| LINUX X64 | No ejecutado | No ejecutado | No ejecutado | **PLATFORM_UNAVAILABLE LOCAL** |
| LINUX ARM64 | No ejecutado | No ejecutado | No ejecutado | **PLATFORM_UNAVAILABLE LOCAL** |
| MACOS INTEL | No ejecutado | No ejecutado | No ejecutado | **PLATFORM_UNAVAILABLE LOCAL** |
| MACOS ARM64 | No ejecutado | No ejecutado | No ejecutado | **PLATFORM_UNAVAILABLE LOCAL** |
| MULTIPLATFORM RELEASE | No creada | Matriz remota no ejecutada | Sin evidencia de seis targets | **BLOCKED** |

## Problemas encontrados y correcciones

| Hallazgo | Corrección aplicada | Verificación |
|---|---|---|
| El workflow anterior solo construía y subía outputs por target | Matriz completa, preflight, ensamblado, revalidación, checksums y gate de release | Validador estático CI PASS |
| El manifiesto previo no incluía el contrato por artefacto solicitado | Se añadieron `filename`, `version`, `validated`, `BUILT` y procedencia de build | Manifiesto Windows actualizado y verificado |
| Linux generaba nombres en minúscula no alineados con el contrato | Nombres ajustados a `AutomationCenter-1.0.0-linux-{arch}.{deb,tar.gz}` | Validación estática PASS; build nativo pendiente |
| Validación de arquitectura Windows dependía de la etiqueta | Se añadió inspección PE del launcher y se añadió control equivalente en Linux/macOS | Build Windows x64 PASS |
| El validador estático trataba el manifiesto y checksum como ficheros no permitidos | Se permiten exclusivamente `release-manifest.json` y `SHA256SUMS.txt` en la raíz de `dist/` | `validate_definitions.py` PASS |
| Una release parcial podía ser confundida con final | `assemble-release` y `publish-release` requieren `target=all` y éxito de todos los jobs | Validación estática PASS |

## Condiciones para desbloquear la release pública

Para convertir este diseño en una release pública verificable se necesita mantener los cambios del propietario, crear un commit limpio, configurar un remoto GitHub y habilitar una vía autorizada para ejecutar GitHub Actions. Entonces debe lanzarse el workflow con `target=all` y `create_release=false` primero. Solo si los seis jobs producen los diez artefactos reales, superan tests, escaneo, validación de arquitectura y `SHA256SUMS.txt`, se puede repetir con `create_release=true`.

> No debe crearse el tag `v1.0.0` ni declararse `READY` hasta disponer de esa evidencia remota completa.

## Referencias

[1]: https://docs.github.com/en/actions/reference/runners/github-hosted-runners "GitHub-hosted runners reference"

[2]: https://github.blog/changelog/2026-02-26-macos-26-is-now-generally-available-for-github-hosted-runners/ "macOS 26 runners generally available"
