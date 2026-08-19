param(
    [string]$ProjectRoot = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'
$key = (Get-Clipboard -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($key) -or $key -notmatch '^eyJ[A-Za-z0-9._-]+$') {
    throw 'La clave de Public API no está disponible en el portapapeles con el formato esperado.'
}

$envPath = Join-Path $ProjectRoot '.env'
if (-not (Test-Path $envPath)) {
    throw 'No se encontró el archivo .env del proyecto.'
}

$lines = Get-Content -Path $envPath
$updated = $false
$output = foreach ($line in $lines) {
    if ($line -match '^\s*N8N_API_KEY\s*=') {
        $updated = $true
        "N8N_API_KEY=$key"
    } else {
        $line
    }
}
if (-not $updated) {
    $output += "N8N_API_KEY=$key"
}

$tempPath = "$envPath.tmp"
[System.IO.File]::WriteAllLines($tempPath, [string[]]$output, [System.Text.UTF8Encoding]::new($false))
Move-Item -Path $tempPath -Destination $envPath -Force
$key = $null
Set-Clipboard -Value ' '
Write-Output 'N8N_API_KEY_UPDATED_FROM_CLIPBOARD'
