$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$outputDir = Join-Path $root 'artifacts'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$backupPath = Join-Path $outputDir 'backup-verification.json'

$export = Invoke-RestMethod -Method Get -Uri 'http://localhost:8000/api/v1/backup/export'
$export | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 $backupPath
$serialized = Get-Content -Raw $backupPath
$markers = @('api_key','apikey','access_token','refresh_token','token','secret','password','authorization','private_key','encryption_key')
$matches = @($markers | Where-Object { $serialized -match ('"' + [regex]::Escape($_) + '[^" ]*"\\s*:') })

$validation = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/v1/backup/validate' -ContentType 'application/json' -Body (@{ backup = $export } | ConvertTo-Json -Depth 100)
$dryRun = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/v1/backup/restore' -ContentType 'application/json' -Body (@{ backup = $export; dry_run = $true } | ConvertTo-Json -Depth 100)

Write-Output ("BACKUP_VALID={0};AUTOMATIONS={1};PROFILES={2};SETTINGS={3};MANIFESTS={4};SECRET_MARKERS={5};DRY_RUN={6}" -f $validation.valid,$validation.automations,$validation.profiles,$validation.settings,$validation.manifests,$matches.Count,$dryRun.dry_run)
