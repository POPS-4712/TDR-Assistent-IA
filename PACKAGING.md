# Packaging y distribución de Automation Center

Automation Center se distribuye mediante builds nativos en runners de la arquitectura objetivo. La release se ensambla únicamente cuando todos los gates de fuente, pruebas, arquitectura, seguridad y artefactos se completan correctamente.

## 1. Targets y artefactos

| Target | Runner nativo | Artefactos requeridos |
|---|---|---|
| Windows x64 | Windows x64 | `.exe`, `.zip` |
| Windows ARM64 | Windows ARM64 | `.exe`, `.zip` |
| Linux x64 | Linux x64 | `.deb`, `.tar.gz` |
| Linux ARM64 | Linux ARM64 | `.deb`, `.tar.gz` |
| macOS Intel | macOS x64 | `.dmg` |
| macOS Apple Silicon | macOS ARM64 | `.dmg` |

El contrato de release contiene diez distribuibles: dos por cada target Windows y Linux, y un DMG por cada target macOS. Los artefactos se generan en su plataforma objetivo; no se deben fabricar extensiones ni declarar una arquitectura como construida sin una ejecución nativa comprobada.

## 2. Pipeline de release

La pipeline `native-release-builds.yml` aplica la siguiente secuencia:

```text
integridad de fuente
  → pruebas backend y frontend
  → seis builds nativos
  → escaneo de artefactos
  → validación de arquitectura
  → ensamblado del contrato completo
  → SHA-256 y manifiesto
  → validación post-build
  → publicación condicionada
```

La publicación queda bloqueada si falta un target, falla un checksum, se detecta información privada, no pasa la arquitectura esperada o no se supera el gate de ensamblado completo. Los cambios de Phase 2.17 añaden además gates funcionales para el healthcheck frontend, autenticación de Public API n8n, E2E de `test-automation` y presencia de la documentación operativa.

## 3. Verificación de artefactos

Cada release incluye:

| Archivo | Finalidad |
|---|---|
| `release-manifest.json` | Versión, procedencia, plataforma, arquitectura, tamaño, estado y hash de cada artefacto. |
| `SHA256SUMS.txt` | Sumas SHA-256 independientes para los diez distribuibles. |
| Distribuibles nativos | Instaladores, archivos ZIP, paquetes DEB, tarballs y DMG del contrato. |

La verificación debe comprobar el mismo SHA-256 calculado desde el archivo descargado contra ambos metadatos. El escáner de packaging detecta nombres de archivos privados y patrones de secretos de alta confianza, pero no reemplaza una revisión de configuración privada local.

## 4. Build y validación local

Los scripts de packaging están separados por plataforma:

| Plataforma | Definición principal |
|---|---|
| Windows | `packaging/windows/build-windows.ps1` y `AutomationCenter.iss` |
| Linux | `packaging/linux/build-linux.sh` |
| macOS | `packaging/macos/build-macos.sh` |
| Validación común | `packaging/common/validate_definitions.py`, `scan_artifact.py`, `release_manifest.py` |

Ejecute los validadores comunes antes de un build. Los scripts rechazan arquitecturas de host incorrectas en lugar de producir artefactos falsos. Los directorios `dist/` contienen resultados locales y no deben añadirse al control de versiones.

## 5. Firma, seguridad y limitaciones

Actualmente la distribución aporta integridad mediante SHA-256, manifiesto de procedencia y escaneo de secretos. **No se debe afirmar que los binarios están firmados digitalmente si la release no contiene una firma verificable.** La ausencia de firma no invalida la comprobación SHA-256, pero es una limitación de distribución que debe comunicarse.

Las claves de n8n, runtime, PostgreSQL y backend son información privada. Nunca deben aparecer en el manifiesto, checksums, logs de CI, artefactos, backups de metadata ni documentación.

## 6. Publicación

La release no se publica hasta que los diez activos reales estén disponibles y todos los gates obligatorios sean positivos. Una release ya publicada no debe sobrescribirse para corregir defectos; el procedimiento correcto es crear una nueva versión candidata, validar sus builds y publicar un tag nuevo solo con evidencia completa.

Consulte [INSTALLATION.md](./INSTALLATION.md) para verificación de descargas y [UPGRADING.md](./UPGRADING.md) para actualizaciones seguras.
