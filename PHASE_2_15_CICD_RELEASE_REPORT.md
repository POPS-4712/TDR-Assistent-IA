# Informe de release CI/CD nativa multiplataforma — Phase 2.15

**Producto:** Automation Center  
**Versión publicada:** `v1.0.0`  
**Fecha de cierre:** 19 de agosto de 2026  
**Resultado:** **PASS — release publicada con validación completa**

> La release `v1.0.0` fue publicada únicamente después de que una matriz nativa de seis runners, el ensamblado de diez artefactos, la revalidación de seguridad y la generación de checksums finalizaran correctamente. La URL de distribución es [GitHub Release v1.0.0][1].

## Resumen ejecutivo

La Phase 2.15 ejecutó de forma remota y real la pipeline definida en `.github/workflows/native-release-builds.yml`. El run de publicación final `32284849538` terminó en **success** para el preflight, los seis targets nativos, el ensamblado de la release y el job de publicación. Ningún target se marcó como `PLATFORM UNAVAILABLE`, porque todos se construyeron en runners nativos disponibles. La ejecución completa verificable está disponible en [GitHub Actions][2].

| Control | Evidencia | Estado |
|---|---|---|
| Integridad de fuente y definiciones CI | Job `Source integrity and test preflight` del run final | **PASS** |
| Windows x64 nativo | `windows-latest`; `.exe` y `.zip` | **PASS** |
| Windows ARM64 nativo | `windows-11-arm`; `.exe` y `.zip` | **PASS** |
| Linux x64 nativo | `ubuntu-24.04`; `.deb` y `.tar.gz` | **PASS** |
| Linux ARM64 nativo | `ubuntu-24.04-arm`; `.deb` y `.tar.gz` | **PASS** |
| macOS Intel nativo | `macos-26-intel`; `.dmg` | **PASS** |
| macOS ARM64 nativo | `macos-26`; `.dmg` | **PASS** |
| Ensamblado y contrato de diez artefactos | Job `Assemble verified multiplatform release bundle` | **PASS** |
| Publicación condicionada | Job `Publish GitHub release only after complete validation` | **PASS** |
| Release publicada | Tag `v1.0.0`, no draft, no prerelease | **PASS** |

## Trazabilidad de la publicación

El tag `v1.0.0` resuelve al commit `11c321b4ccc43be8392e37e46df4dcd227c99448`, cuyo cambio incorpora límites y reintentos acotados para la instalación de paquetes Linux. El tag, el commit y los diez activos finales son públicos dentro del repositorio privado autorizado; la release no es borrador ni prerelease. [1] [4]

| Elemento | Valor verificado |
|---|---|
| Repositorio | `POPS-4712/TDR-Assistent-IA` |
| Tag | `v1.0.0` |
| Commit del tag | `11c321b4ccc43be8392e37e46df4dcd227c99448` |
| Fecha de publicación | `2026-08-19T18:18:43Z` |
| Run final de publicación | [`32284849538`][2] |
| Run de validación sin publicar | [`32276358953`][3] |
| Release | [Automation Center 1.0.0][1] |

## Evidencia de ejecución final

El run final se lanzó con `target=all` y `create_release=true`. El preflight confirmó la versión, la fuente y los validadores. La matriz ejecutó las regresiones backend y frontend antes del empaquetado de cada target; cada build validó la arquitectura nativa esperada, escaneó los artefactos y subió su evidencia. Tras obtener los seis outputs, el ensamblado descargó exclusivamente esos outputs, recompuso el manifiesto, exigió exactamente diez ficheros y recalculó `SHA256SUMS.txt`. Solo entonces se habilitó el job que creó la release. [2]

| Job del run `32284849538` | Conclusión |
|---|---|
| `Source integrity and test preflight` | **success** |
| `macos-arm64 native build` | **success** |
| `macos-x64 native build` | **success** |
| `linux-arm64 native build` | **success** |
| `linux-x64 native build` | **success** |
| `windows-arm64 native build` | **success** |
| `windows-x64 native build` | **success** |
| `Assemble verified multiplatform release bundle` | **success** |
| `Publish GitHub release only after complete validation` | **success** |

## Activos publicados y checksums SHA-256

La release contiene exactamente diez binarios o paquetes de distribución, más `release-manifest.json` y `SHA256SUMS.txt`. Los hashes siguientes proceden de la suma de comprobación publicada y coinciden con los digest SHA-256 expuestos por los activos de la release. El manifiesto publicado declara `version=1.0.0`, diez artefactos, `status=BUILT` y `validated=true` para cada uno. [1]

| Plataforma | Activo | Tamaño (bytes) | SHA-256 | Estado |
|---|---|---:|---|---|
| Linux ARM64 | `AutomationCenter-1.0.0-linux-arm64.deb` | 16,646,176 | `f3d55058beb2c87285c2e6129f3464c692dae29b5790298e709831a8d10be410` | **BUILT / VALIDATED** |
| Linux ARM64 | `AutomationCenter-1.0.0-linux-arm64.tar.gz` | 16,758,699 | `7b510add55d735561b636ca29070490ab71c51c94e232972816dbf186d19ae82` | **BUILT / VALIDATED** |
| Linux x64 | `AutomationCenter-1.0.0-linux-x64.deb` | 17,427,170 | `5e238ffa700eb6fb0afc7f4d54a8554fb8a79e073f364ee9b8e0d0194c54ce60` | **BUILT / VALIDATED** |
| Linux x64 | `AutomationCenter-1.0.0-linux-x64.tar.gz` | 17,541,816 | `434781a2b1273cf23e19dc1c5c2ca7a35c270eede4439814664e08b7c8af7be4` | **BUILT / VALIDATED** |
| macOS ARM64 | `AutomationCenter-1.0.0-macos-arm64.dmg` | 8,620,431 | `2061ec64d7a10d84506e5d5599cfa59224dbe89ac8e44964489f8a52c6e6743e` | **BUILT / VALIDATED** |
| macOS x64 | `AutomationCenter-1.0.0-macos-x64.dmg` | 9,400,592 | `9ab0218bf34572476e10323d2810fa97b79b61133678e1f26c72270d928cd81d` | **BUILT / VALIDATED** |
| Windows ARM64 | `AutomationCenter-1.0.0-win-arm64.exe` | 10,531,435 | `99a9cc144336a982d4efe1749c269e818acfc58dd2c1a0717399873dcdc3e366` | **BUILT / VALIDATED** |
| Windows ARM64 | `AutomationCenter-1.0.0-win-arm64.zip` | 8,664,434 | `f14f9c569346cdc75c2af98853686410e5e57151f60aa4201d6e1ce079870c77` | **BUILT / VALIDATED** |
| Windows x64 | `AutomationCenter-1.0.0-win-x64.exe` | 10,802,189 | `46217db7c3c66a7ff7e00813e58af5fbe25b0fc8ef92cce3e57b0993d292078c` | **BUILT / VALIDATED** |
| Windows x64 | `AutomationCenter-1.0.0-win-x64.zip` | 8,933,060 | `94ed34b5aa608c60353c8cdc2ba1ce4f18f51205f424d2ac2864591b220081e0` | **BUILT / VALIDATED** |

## Validaciones aplicadas

La evidencia no depende de los nombres de archivo. La pipeline comprueba la arquitectura del runner, ejecuta tests backend y frontend, construye mediante el script específico de cada plataforma, verifica que cada output exista y tenga tamaño positivo, ejecuta el escáner de artefactos y registra la procedencia y hashes. Para Windows, se inspecciona el campo `Machine` del ejecutable PE incluido en el ZIP; para Linux y macOS, los scripts de empaquetado validan el payload nativo de los paquetes. La etapa de ensamblado repite las verificaciones sobre los ficheros descargados, no sobre artefactos simulados. [2] [5]

| Salvaguarda | Resultado final |
|---|---|
| Checkout y fuente inmutables | **PASS** |
| Tests backend y frontend antes de cada build | **PASS** |
| Escaneo de secretos en cada activo | **PASS** |
| Validación de arquitectura por plataforma | **PASS** |
| Existencia y tamaño positivo de los diez outputs | **PASS** |
| Reensamblado desde artifacts remotos reales | **PASS** |
| Revalidación y regeneración de SHA-256 | **PASS** |
| Gate que impide release parcial | **PASS** |

## Incidencias resueltas durante la fase

Se mantuvo la regla de no declarar éxitos sin evidencia. La primera ejecución completa de validación (`32276358953`) superó todos los gates y no publicó porque fue lanzada deliberadamente con `create_release=false`. Esto estableció que los seis targets y el ensamblado son alcanzables con artefactos reales. [3]

Durante la primera ejecución de publicación, el paso de herramientas Linux x64 quedó bloqueado en `apt-get update`. Esa ejecución se canceló de forma controlada antes de publicar y se incorporó el commit `11c321b`, que añade timeouts, reintentos y opciones de red a la instalación Linux. El siguiente intento encontró un timeout externo de `ArtifactService/CreateArtifact` al subir la evidencia macOS x64; las cinco reintentos del servicio fallaron antes de que pudiera publicarse nada. También se canceló sin crear release. La tercera ejecución fue completa y exitosa, por lo que es la única utilizada como evidencia de publicación. [2] [4]

| Run | Propósito o incidencia | Resultado | ¿Publicó? |
|---|---|---|---|
| [`32276358953`][3] | Validación completa, `create_release=false` | **success** | No; job de publicación omitido por diseño |
| `32278669817` | Primer intento de publicación; instalación Linux x64 bloqueada | **cancelled** | No |
| `32283195989` | Segundo intento; timeout externo de creación de artifact macOS x64 | **cancelled** | No |
| [`32284849538`][2] | Intento final con matriz, ensamblado y publicación | **success** | **Sí** |

## Criterios incorporados del adjunto

Los criterios aportados se han incorporado como requisitos de aceptación del cierre. La evidencia final los satisface sin reinterpretar una espera prolongada como fallo: las dos ejecuciones canceladas se documentan como incidencias de infraestructura con evidencia concreta —un paso Linux x64 sin actividad útil durante un periodo prolongado y un timeout de `ArtifactService` tras cinco reintentos—, y no se usaron para declarar éxito. La única ejecución empleada como prueba de publicación es el run final exitoso. [2] [3]

| Requisito incorporado | Evidencia aplicable | Resultado |
|---|---|---|
| Seis runners nativos y sin cross-build | Seis jobs nativos exitosos en el run final | **PASS** |
| Diez artefactos finales exactos | Ensamblado exitoso y manifiesto publicado con diez entradas | **PASS** |
| Tests, arquitectura y escaneo antes de publicar | Jobs de build y revalidación de ensamblado exitosos | **PASS** |
| SHA-256 y metadatos de release | `SHA256SUMS.txt`, `release-manifest.json` y digest de activos coincidentes | **PASS** |
| No publicar release parcial | Dos intentos no exitosos documentados sin publicación; solo el run final creó el tag | **PASS** |
| Declarar READY únicamente con evidencia real | Run `32284849538` finalizado correctamente y release `v1.0.0` publicada | **PASS** |

## Conclusión

La Phase 2.15 queda **completada**. Automation Center `v1.0.0` dispone de una release real, reproducible desde el commit etiquetado, con diez artefactos nativos de Windows, Linux y macOS. Cada artefacto publicado cuenta con un SHA-256 verificable y el tag se creó solo después de que la matriz completa y los gates de ensamblado y seguridad finalizaran correctamente.

No hay artefactos ficticios, extensiones simuladas ni plataformas declaradas como válidas sin runner nativo. Los intentos interrumpidos están documentados como `cancelled` y no se usan para sostener el resultado final.

## Referencias

[1]: https://github.com/POPS-4712/TDR-Assistent-IA/releases/tag/v1.0.0 "Automation Center v1.0.0 — release publicada"

[2]: https://github.com/POPS-4712/TDR-Assistent-IA/actions/runs/32284849538 "GitHub Actions — publicación final exitosa"

[3]: https://github.com/POPS-4712/TDR-Assistent-IA/actions/runs/32276358953 "GitHub Actions — validación completa sin publicación"

[4]: https://github.com/POPS-4712/TDR-Assistent-IA/commit/11c321b4ccc43be8392e37e46df4dcd227c99448 "Commit de resiliencia de instalación Linux"

[5]: https://github.com/POPS-4712/TDR-Assistent-IA/blob/11c321b4ccc43be8392e37e46df4dcd227c99448/.github/workflows/native-release-builds.yml "Workflow de release nativa"
