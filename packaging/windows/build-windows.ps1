[CmdletBinding()]
param(
    [ValidateSet('x64', 'arm64')]
    [string]$Architecture = 'x64',
    [switch]$ValidateOnly,
    [switch]$PortableOnly
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Version = (Get-Content (Join-Path $Root 'VERSION') -Raw).Trim()
$Output = Join-Path $Root "dist\windows-$Architecture"
$BuildRoot = Join-Path $Root "packaging\.build\windows-$Architecture"
$HostArchitecture = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } elseif ($env:PROCESSOR_ARCHITECTURE -in @('AMD64', 'IA64')) { 'x64' } else { $env:PROCESSOR_ARCHITECTURE.ToLowerInvariant() }

function Assert-RequiredFile([string]$Path) {
    if (-not (Test-Path $Path -PathType Leaf)) { throw "Required packaging file is missing: $Path" }
}

function Assert-LauncherArchitecture([string]$Path, [string]$ExpectedArchitecture) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 64 -or $bytes[0] -ne 0x4D -or $bytes[1] -ne 0x5A) { throw "Native launcher is not a valid PE file: $Path" }
    $peOffset = [System.BitConverter]::ToInt32($bytes, 0x3C)
    if ($peOffset -lt 0 -or $peOffset + 6 -gt $bytes.Length) { throw "Native launcher has an invalid PE header: $Path" }
    $machine = [System.BitConverter]::ToUInt16($bytes, $peOffset + 4)
    $expectedMachine = if ($ExpectedArchitecture -eq 'x64') { 0x8664 } else { 0xAA64 }
    if ($machine -ne $expectedMachine) { throw ("Native launcher architecture mismatch: expected {0}, got PE machine 0x{1:X4}" -f $ExpectedArchitecture, $machine) }
}

function Invoke-ReleaseRecord([string]$ArtifactPath, [string]$Format) {
    if (-not (Test-Path $ArtifactPath -PathType Leaf) -or (Get-Item $ArtifactPath).Length -le 0) {
        throw "Final artifact is missing or empty: $ArtifactPath"
    }
    & python (Join-Path $Root 'packaging\common\scan_artifact.py') $ArtifactPath
    if ($LASTEXITCODE -ne 0) { throw "Final artifact scan failed: $ArtifactPath" }
    & python (Join-Path $Root 'packaging\common\release_manifest.py') record --artifact $ArtifactPath --platform "windows-$Architecture" --architecture $Architecture --format $Format
    if ($LASTEXITCODE -ne 0) { throw "Release manifest recording failed: $ArtifactPath" }
}

function Copy-DistributionSource([string]$Destination) {
    $excludedDirectoryNames = @('.git', '.pytest_cache', 'node_modules', 'dist', 'output', 'postgres-data', '.n8n', '__pycache__', '.build', '.venv', 'venv', 'tests', 'test')
    $excludedFileNames = @('.env', 'runtime.env', 'vault.enc', 'system.key', 'id_rsa', 'id_ed25519', 'linkedin.json', 'jobs.json', 'jobs-history.json', 'infojobs-jobs.json', 'infojobs-history.json')
    $excludedExtensions = @('.pem', '.key', '.p12', '.pfx', '.log')

    function Copy-SafeDirectory([string]$Source, [string]$Target) {
        New-Item -ItemType Directory -Force -Path $Target | Out-Null
        foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
            if ($item.PSIsContainer) {
                if ($excludedDirectoryNames -contains $item.Name) { continue }
                Copy-SafeDirectory $item.FullName (Join-Path $Target $item.Name)
                continue
            }
            if ($excludedFileNames -contains $item.Name -or $item.Name -like '.env.*' -or $excludedExtensions -contains $item.Extension.ToLowerInvariant()) { continue }
            Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $Target $item.Name) -Force
        }
    }

    Remove-Item -LiteralPath $Destination -Recurse -Force -ErrorAction SilentlyContinue
    Copy-SafeDirectory $Root $Destination
}

if ($Architecture -ne $HostArchitecture) {
    throw "PLATFORM UNAVAILABLE: Windows $Architecture packages must be built on a matching Windows $Architecture host. Current host is $HostArchitecture."
}

Assert-RequiredFile (Join-Path $Root 'VERSION')
Assert-RequiredFile (Join-Path $Root 'docker-compose.prod.yml')
Assert-RequiredFile (Join-Path $Root 'packaging\common\service_manager.py')
Assert-RequiredFile (Join-Path $Root 'packaging\windows\AutomationCenter.iss')

if ($ValidateOnly) {
    Write-Output "BUILD VALIDATED: Windows $Architecture package definition $Version"
    exit 0
}

& python -m PyInstaller --version *> $null
$PyInstallerAvailable = $LASTEXITCODE -eq 0
$isccCandidates = @(
    (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    'C:\Program Files\Inno Setup 6\ISCC.exe'
) | Where-Object { $_ -and (Test-Path $_ -PathType Leaf) }
$IsccPath = $isccCandidates | Select-Object -First 1
if (-not $PyInstallerAvailable -or -not $IsccPath) {
    throw 'NOT BUILT: Python PyInstaller and Inno Setup 6 (ISCC.exe) are required to build a native Windows installer.'
}

Remove-Item -LiteralPath $BuildRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
$Stage = Join-Path $BuildRoot 'app'
Copy-DistributionSource $Stage

$LauncherDist = Join-Path $BuildRoot 'launcher'
& python -m PyInstaller --noconfirm --clean --onefile --name AutomationCenter --distpath $LauncherDist --workpath (Join-Path $BuildRoot 'pyinstaller-work') --specpath $BuildRoot (Join-Path $Root 'packaging\common\service_manager.py')
if ($LASTEXITCODE -ne 0) { throw 'Native launcher build failed.' }
Copy-Item -LiteralPath (Join-Path $LauncherDist 'AutomationCenter.exe') -Destination (Join-Path $Stage 'AutomationCenter.exe') -Force
Assert-LauncherArchitecture (Join-Path $Stage 'AutomationCenter.exe') $Architecture

& (Join-Path $Root 'packaging\common\scan-artifact.ps1') -Path $Stage
if ($LASTEXITCODE -ne 0) { throw 'Security scan blocked Windows packaging.' }

New-Item -ItemType Directory -Force -Path $Output | Out-Null
$artifactPrefix = "AutomationCenter-$Version-win-$Architecture"
Get-ChildItem -LiteralPath $Output -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "$artifactPrefix.*" } | Remove-Item -Force
$ZipPath = Join-Path $Output "$artifactPrefix.zip"
Compress-Archive -Path (Join-Path $Stage '*') -DestinationPath $ZipPath -Force
Invoke-ReleaseRecord $ZipPath 'zip'

if (-not $PortableOnly) {
    & $IsccPath "/DAppVersion=$Version" "/DAppArchitecture=$Architecture" "/DSourceRoot=$Stage" "/DOutputDir=$Output" (Join-Path $Root 'packaging\windows\AutomationCenter.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
    $InstallerPath = Join-Path $Output "$artifactPrefix.exe"
    Invoke-ReleaseRecord $InstallerPath 'exe'
}

& python (Join-Path $Root 'packaging\common\release_manifest.py') verify
if ($LASTEXITCODE -ne 0) { throw 'Release manifest verification failed.' }
Write-Output "PASS: Windows $Architecture genuine artifacts written to $Output"
