# Actualización de Automation Center

Esta guía describe actualizaciones locales sin sobrescribir perfiles, metadata ni volúmenes de usuario. Una actualización no debe usarse para crear, reemplazar o exponer credenciales.

## 1. Preparación

Antes de instalar una versión nueva, verifique el SHA-256 del instalador y cree un backup de metadata desde el launcher:

```text
AutomationCenter backup-metadata --json
```

El backup contiene metadata no sensible. El guard de seguridad rechaza exportaciones que incluyan claves, tokens, contraseñas u otros campos sensibles. Conserve el archivo de backup en un almacenamiento local protegido.

| Elemento | Comportamiento durante una actualización normal |
|---|---|
| Perfiles | Se preservan en la instancia privada local. |
| Metadata de automatizaciones | Se preserva y puede respaldarse antes de actualizar. |
| Volúmenes Docker de PostgreSQL y n8n | Se preservan; una actualización normal no ejecuta `down --volumes`. |
| Claves y tokens | Permanecen en la configuración privada o almacenamiento seguro local; no se incorporan al backup de metadata. |
| Instalación del programa | Se reemplaza por la versión nueva en el directorio de aplicación. |

## 2. Actualización en sitio

1. Cierre la interfaz de Automation Center si está abierta.
2. Verifique el checksum del instalador nuevo.
3. Ejecute el instalador para la misma arquitectura sobre la instalación existente.
4. Espere a que finalice y ejecute `AutomationCenter health --json`.
5. Compruebe que el perfil activo y el directorio de backups siguen disponibles.
6. Ejecute el preflight de las automatizaciones antes de habilitar o ejecutar cualquier workflow.

La reinstalación debe reutilizar la configuración privada existente. Si una actualización informa que necesita inicializar una configuración distinta, deténgase y revise la ruta de datos antes de continuar.

## 3. Compatibilidad de n8n Public API

La Public API key de n8n no se genera automáticamente. Después de una actualización, el preflight puede bloquearse si la clave fue revocada, caducó o no se migró la configuración privada. Cree una nueva clave mediante el mecanismo oficial de n8n y guárdela sin eco:

```text
AutomationCenter configure-n8n-api-key
```

Reinicie los servicios tras cambiarla. No incluya una key en archivos de configuración versionados, comandos con historial, tickets o logs.[1]

## 4. Rollback seguro

Un rollback solo debe aplicarse a una versión previamente verificada y de la misma arquitectura.

1. Cree un backup de metadata.
2. Detenga la instancia local con el launcher.
3. Instale la versión previa verificada sobre la misma instalación, sin eliminar datos.
4. Arranque la instancia y ejecute `AutomationCenter health --json`.
5. Verifique perfiles, backups y el preflight de las automatizaciones.

> No use `remove-data --confirm-remove-data` como paso de rollback. Ese comando es destructivo y está reservado para una eliminación explícita de datos y volúmenes de la instancia indicada.

## 5. Desinstalación y datos

La desinstalación normal conserva los datos privados para permitir una reinstalación o recuperación. La eliminación total exige una confirmación explícita desde el launcher; no se realiza automáticamente durante upgrades, reparaciones ni pruebas.

Para incidencias de contenedor, revise [TROUBLESHOOTING_INSTALLATION.md](./TROUBLESHOOTING_INSTALLATION.md) antes de eliminar nada.

## Referencias

[1] [Autenticación de la Public API de n8n](https://docs.n8n.io/connect/n8n-api/authentication/)
