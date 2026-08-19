[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = 'Stop'
$target = Resolve-Path $Path
$patterns = @(
    '-----BEGIN ([A-Z ]+)?PRIVATE KEY-----',
    'AIza[0-9A-Za-z_-]{20,}',
    'sk-[A-Za-z0-9_-]{20,}',
    'xox[baprs]-[A-Za-z0-9-]{20,}',
    'gh[pousr]_[A-Za-z0-9]{20,}',
    'Bearer\s+[A-Za-z0-9._-]{20,}'
)
$textExtensions = @('.env', '.txt', '.json', '.yaml', '.yml', '.ini', '.cfg', '.conf', '.py', '.ps1', '.sh', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.md', '.iss', '.xml')
$forbiddenNames = @('.env', 'runtime.env', 'id_rsa', 'id_ed25519', '.n8n')
$violations = 0

function Test-Content([string]$Name, [string]$Content) {
    foreach ($pattern in $patterns) {
        if ($Content -match $pattern) { return $true }
    }
    return $false
}

function Test-Entry([string]$Name, [scriptblock]$ReadContent) {
    $leaf = [System.IO.Path]::GetFileName($Name).ToLowerInvariant()
    if ($forbiddenNames -contains $leaf -or $Name -match '(^|[\\/])\.n8n([\\/]|$)') {
        return $true
    }
    $extension = [System.IO.Path]::GetExtension($Name).ToLowerInvariant()
    if ($textExtensions -notcontains $extension) { return $false }
    try {
        return Test-Content $Name (& $ReadContent)
    } catch {
        return $true
    }
}

if ((Get-Item $target).PSIsContainer) {
    $files = Get-ChildItem -LiteralPath $target -File -Recurse -Force
    foreach ($file in $files) {
        if (Test-Entry $file.FullName { Get-Content -LiteralPath $file.FullName -Raw -ErrorAction Stop }) { $violations++ }
    }
} elseif ($target.Path.EndsWith('.zip', [StringComparison]::OrdinalIgnoreCase)) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($target)
    try {
        foreach ($entry in $archive.Entries) {
            if ($entry.Length -eq 0) { continue }
            if (Test-Entry $entry.FullName {
                $reader = [System.IO.StreamReader]::new($entry.Open())
                try { $reader.ReadToEnd() } finally { $reader.Dispose() }
            }) { $violations++ }
        }
    } finally {
        $archive.Dispose()
    }
} else {
    throw 'Unsupported artifact type. Provide a staging directory or ZIP archive.'
}

if ($violations -gt 0) {
    Write-Error "SECURITY SCAN FAILED: $violations potential secret or private-data issue(s) detected. No matching values were printed."
    exit 1
}
Write-Output 'SECURITY SCAN PASS: no forbidden private files or high-confidence secret patterns were detected.'
