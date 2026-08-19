[CmdletBinding()]
param(
    [string[]]$Images = @('tdr-assistent-ia-backend:latest', 'tdr-assistent-ia-frontend:latest', 'tdr-assistent-ia-playwright:latest'),
    [string]$EnvironmentFile = ''
)

$ErrorActionPreference = 'Stop'
if (-not $EnvironmentFile) {
    $root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    $EnvironmentFile = Join-Path $root '.env'
}
$patterns = @(
    '-----BEGIN ([A-Z ]+)?PRIVATE KEY-----',
    'AIza[0-9A-Za-z_-]{20,}',
    'sk-[A-Za-z0-9_-]{20,}',
    'xox[baprs]-[A-Za-z0-9-]{20,}',
    'gh[pousr]_[A-Za-z0-9]{20,}',
    'Bearer\s+[A-Za-z0-9._-]{20,}'
)
$secretValues = @()
if (Test-Path $EnvironmentFile -PathType Leaf) {
    $secretValues = Get-Content -LiteralPath $EnvironmentFile | Where-Object {
        $_ -match '^(.*(?:PASSWORD|SECRET|TOKEN|API_KEY|ENCRYPTION_KEY).*)=(.+)$' -and $matches[2].Length -gt 0
    } | ForEach-Object { $_.Split('=', 2)[1] } | Where-Object { $_.Length -ge 8 }
}

$findings = 0
foreach ($image in $Images) {
    docker image inspect $image *> $null
    if ($LASTEXITCODE -ne 0) { Write-Error "SECURITY SCAN FAILED: image is unavailable: $image"; exit 2 }
    $inspection = docker image inspect $image | Out-String
    $history = docker history --no-trunc $image | Out-String
    $material = $inspection + "`n" + $history
    foreach ($pattern in $patterns) { if ($material -match $pattern) { $findings++ } }
    foreach ($value in $secretValues) { if ($material.Contains($value)) { $findings++ } }
}

if ($findings -gt 0) {
    Write-Error "SECURITY SCAN FAILED: $findings possible secret exposure(s) found in image metadata or history. Matching values were not printed."
    exit 1
}
Write-Output 'DOCKER IMAGE SECURITY SCAN PASS: no local secret values or high-confidence secret patterns were found in image metadata/history.'
