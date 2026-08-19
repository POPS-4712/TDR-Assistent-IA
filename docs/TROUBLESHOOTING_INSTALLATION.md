# Resolución de problemas de instalación

Automation Center proporciona comprobaciones de compatibilidad en la primera ejecución y un panel **System** para revisar el estado local. Los diagnósticos muestran arquitectura, versión, servicios, espacio disponible, puertos preferidos, migraciones y estado de almacenamiento seguro. No muestran tokens, contraseñas, claves API ni valores de configuración privada.

## Errores de compatibilidad

| Síntoma | Causa probable | Acción segura |
|---|---|---|
| El instalador indica arquitectura incompatible | Se utilizó un paquete x64 en ARM64 o el inverso. | Descargue o construya el paquete nativo de la arquitectura indicada. No fuerce la instalación. |
| El runtime local no está disponible | Docker Desktop o Docker Engine no está iniciado o no es accesible. | Inicie o repare el runtime local y vuelva a abrir Automation Center. |
| Un puerto preferido está ocupado | Otro proceso ya usa 3001, 8000, 5432, 5678 o 3000. | Identifique el proceso y elija una configuración alternativa; no finalice procesos no relacionados. |
| Falta espacio | El directorio de usuario o el runtime no dispone de espacio suficiente. | Libere espacio local antes de iniciar los servicios. |

## Servicios locales

La pantalla **System** clasifica cada servicio como saludable, iniciando, detenido o con error. En el uso normal se muestran estados de backend, PostgreSQL, n8n y Playwright sin detalles internos de Docker.

| Servicio | Qué comprueba | Si aparece con error |
|---|---|---|
| Backend | HTTP local `/health` | Compruebe que el runtime local pudo crear el servicio. |
| PostgreSQL | Consulta local de conectividad | No borre el volumen; ejecute Repair o revise espacio y runtime. |
| n8n | Health check interno | Espere al primer arranque; si persiste, revise el panel System. |
| Playwright | Endpoint local `/health` | Compruebe que el runtime contiene una imagen compatible. |

El **Advanced mode** solo habilita acciones sobre contenedores etiquetados como Automation Center cuando la instalación local lo autoriza explícitamente. Si las acciones no aparecen o figuran como deshabilitadas, utilice el lanzador o la reparación del instalador. Esta restricción evita controlar contenedores ajenos.

## Primera ejecución

La primera ejecución requiere que el runtime local y el almacenamiento de usuario estén disponibles. Un perfil inicial es necesario para finalizar el asistente, pero las cuentas externas pueden omitirse. Si se cerró la aplicación antes de terminar, ábrala de nuevo: el asistente continúa mientras no exista el marcador de finalización local.

Si una cuenta externa no está configurada, las automatizaciones reales permanecen en `Blocked`. Esto no impide abrir la aplicación ni crear perfiles. Conecte la cuenta desde **Accounts** cuando disponga de sus credenciales reales; el preflight se repite automáticamente.

## Actualización o desinstalación

Una actualización normal conserva los datos. Si el backup de metadata falla, no continúe con una actualización automatizada. Revise que el backend esté saludable y que el directorio de datos sea escribible.

La desinstalación estándar retira la aplicación y conserva perfiles, configuración, backups y volúmenes. La eliminación total exige confirmación explícita y utiliza el lanzador con `remove-data --confirm-remove-data`. Esta operación elimina únicamente el directorio privado de Automation Center y los volúmenes de su proyecto; no actúa sobre datos de otros proyectos Docker.

## Diagnóstico avanzado para soporte local

Las siguientes operaciones se reservan para usuarios técnicos o soporte local. Deben ejecutarse desde la carpeta de la aplicación o el lanzador, nunca pegando secretos en una consola o informe.

| Finalidad | Operación de referencia | Resultado esperado |
|---|---|---|
| Diagnóstico no sensible | `AutomationCenter diagnose --json` | Estado de runtime, puertos, espacio y servicios sin valores de secretos. |
| Estado de servicios | `AutomationCenter status --json` | Estado de los cinco servicios del producto. |
| Backup previo | `AutomationCenter backup-metadata --json` | Archivo de metadata seguro en la carpeta de backups. |
| Comprobación UI | Abrir `http://localhost:3001` | Interfaz local disponible cuando el frontend esté iniciado. |

No adjunte archivos `runtime.env`, keyrings, volúmenes n8n, tokens OAuth, claves API ni contraseñas a un informe de soporte.
