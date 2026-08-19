param(
  [string]$Container = 'ai-personal-assistant-n8n'
)

$ErrorActionPreference = 'Stop'
$files = Get-ChildItem -LiteralPath "$PSScriptRoot\..\workflows" -Filter '*.json' | Sort-Object Name

if (-not (docker container inspect $Container 2>$null)) {
  throw "No existe el contenedor '$Container'. Ejecuta primero: docker compose up -d"
}

foreach ($file in $files) {
  Write-Host "Importando $($file.Name)..."
  docker cp $file.FullName "${Container}:/tmp/$($file.Name)"
  if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar $($file.Name)" }
  docker exec $Container n8n import:workflow --input="/tmp/$($file.Name)"
  if ($LASTEXITCODE -ne 0) { throw "No se pudo importar $($file.Name)" }
}

Write-Host 'Importación terminada. Configura las credenciales y activa los workflows desde n8n.'
