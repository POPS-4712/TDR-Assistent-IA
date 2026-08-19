[CmdletBinding()]
param(
    [string]$InstallerPath = ''
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $InstallerPath) {
    $InstallerPath = Join-Path $Root 'dist\windows-x64\AutomationCenter-1.0.0-win-x64.exe'
}
$ProjectName = 'automation-center'
$Port = 3102
$TestRoot = Join-Path $env:TEMP ('automation-center-installer-test-' + [guid]::NewGuid().ToString())
$InstallDir = Join-Path $TestRoot 'program'
$LocalDataParent = Join-Path $TestRoot 'local-app-data'
$DataRoot = Join-Path $LocalDataParent 'AutomationCenter'
$OriginalLocalAppData = $env:LOCALAPPDATA
$OriginalUiPort = $env:AUTOMATION_CENTER_UI_PORT
$createdRuntime = $false

function Invoke-Installer([string]$Path) {
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$InstallDir`"")
    $process = Start-Process -FilePath $Path -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Installer exited with code $($process.ExitCode)" }
}

function Wait-ForHttp([string]$Url, [int]$Expected = 200, [int]$Attempts = 90) {
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $status = curl.exe -sS -o NUL -w '%{http_code}' $Url
            if ([int]$status -eq $Expected) { return }
        } catch {}
        Start-Sleep -Seconds 5
    }
    throw "Endpoint did not return HTTP ${Expected}: $Url"
}

function Find-SensitiveBackupKeys([object]$Value, [string]$Path = 'backup') {
    $matches = @()
    if ($Value -is [System.Management.Automation.PSCustomObject]) {
        foreach ($property in $Value.PSObject.Properties) {
            if ($property.Name -match '(?i)api_key|apikey|access_token|refresh_token|token|secret|password|authorization|private_key|encryption_key') {
                $matches += "$Path.$($property.Name)"
            }
            $matches += Find-SensitiveBackupKeys $property.Value "$Path.$($property.Name)"
        }
    } elseif ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        $index = 0
        foreach ($item in $Value) {
            $matches += Find-SensitiveBackupKeys $item "$Path[$index]"
            $index++
        }
    }
    return $matches
}

try {
    if (-not (Test-Path $InstallerPath -PathType Leaf) -or (Get-Item $InstallerPath).Length -le 0) {
        throw 'Installer artifact is missing or empty.'
    }
    New-Item -ItemType Directory -Force -Path $TestRoot, $LocalDataParent | Out-Null
    $env:LOCALAPPDATA = $LocalDataParent
    $env:AUTOMATION_CENTER_UI_PORT = [string]$Port
    Invoke-Installer $InstallerPath
    $Launcher = Join-Path $InstallDir 'AutomationCenter.exe'
    $RuntimeEnv = Join-Path $DataRoot 'config\runtime.env'
    if (-not (Test-Path $Launcher -PathType Leaf) -or -not (Test-Path $RuntimeEnv -PathType Leaf)) {
        throw 'Installer did not create the expected program or private runtime configuration.'
    }
    $suffixLine = Get-Content -LiteralPath $RuntimeEnv | Where-Object { $_ -like 'AUTOMATION_CENTER_INSTANCE_SUFFIX=*' } | Select-Object -First 1
    $instanceSuffix = $suffixLine -replace '^AUTOMATION_CENTER_INSTANCE_SUFFIX=', ''
    if ($instanceSuffix -notmatch '^-[0-9a-f]{16}$') { throw 'Installer runtime configuration did not create a valid isolated instance identifier.' }
    $ProjectName = "automation-center$instanceSuffix"

    & $Launcher start --json | ConvertFrom-Json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Installed launcher could not start local services.' }
    $createdRuntime = $true
    Wait-ForHttp "http://localhost:${Port}/health"
    Wait-ForHttp "http://localhost:${Port}/api/v1/system/status"
    Wait-ForHttp "http://localhost:${Port}/profiles"
    Wait-ForHttp "http://localhost:${Port}/automations"
    Wait-ForHttp "http://localhost:${Port}/accounts"

    $profilePayload = @{ name = 'Phase 2.13 installer test profile'; activate = $true } | ConvertTo-Json -Compress
    $profile = Invoke-RestMethod -Method Post -Uri "http://localhost:${Port}/api/v1/profiles" -ContentType 'application/json' -Body $profilePayload
    if (-not $profile.id) { throw 'Installer test profile was not created.' }

    $preflight = Invoke-RestMethod -Method Post -Uri "http://localhost:${Port}/api/v1/automations/preflight"
    if ($preflight.mutations_applied -ne $false) { throw 'Preflight unexpectedly mutated workflows during installer test.' }
    $backup = & $Launcher backup-metadata --json | ConvertFrom-Json
    if (-not $backup.success) { throw 'Metadata backup did not complete after installation.' }
    $backupFiles = @(Get-ChildItem -LiteralPath (Join-Path $DataRoot 'backups') -File -ErrorAction Stop)
    if ($backupFiles.Count -lt 1) { throw 'Metadata backup file was not created.' }
    $backupContent = $backupFiles | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw }
    $backupObject = $backupContent | ConvertFrom-Json
    $sensitiveBackupKeys = @(Find-SensitiveBackupKeys $backupObject)
    if ($sensitiveBackupKeys.Count -gt 0) { throw "Metadata backup contains forbidden sensitive key path(s): $($sensitiveBackupKeys -join ', ')." }

    Invoke-Installer $InstallerPath
    $profileAfterUpgrade = Invoke-RestMethod "http://localhost:${Port}/api/v1/profiles/$($profile.id)"
    if ($profileAfterUpgrade.id -ne $profile.id) { throw 'Profile did not survive the in-place installer upgrade test.' }
    if (-not (Test-Path (Join-Path $DataRoot 'backups') -PathType Container)) { throw 'Backup directory did not survive the installer upgrade test.' }

    $Uninstaller = Join-Path $InstallDir 'unins000.exe'
    if (-not (Test-Path $Uninstaller -PathType Leaf)) { throw 'Uninstaller was not created.' }
    $uninstallProcess = Start-Process -FilePath $Uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru
    if ($uninstallProcess.ExitCode -ne 0) { throw "Uninstaller exited with code $($uninstallProcess.ExitCode)" }
    if (-not (Test-Path (Join-Path $DataRoot 'config\runtime.env') -PathType Leaf) -or -not (Test-Path (Join-Path $DataRoot 'backups') -PathType Container)) {
        throw 'Normal uninstallation did not preserve isolated user data.'
    }

    Write-Output 'INSTALL_TEST=PASS'
    Write-Output 'UPGRADE_TEST=PASS'
    Write-Output 'UNINSTALL_TEST=PASS'
    Write-Output 'FIRST_RUN_RUNTIME=PASS'
    Write-Output 'PROFILE_PERSISTENCE=PASS'
    Write-Output 'METADATA_BACKUP_SECURITY=PASS'
} finally {
    if ($createdRuntime -and (Test-Path (Join-Path $DataRoot 'config\runtime.env'))) {
        $cleanupErrorPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            docker-compose --project-name $ProjectName --env-file (Join-Path $DataRoot 'config\runtime.env') -f (Join-Path $Root 'docker-compose.prod.yml') down --remove-orphans *> $null
            $null = $LASTEXITCODE
        } catch {}
        finally { $ErrorActionPreference = $cleanupErrorPreference }
    }
    Remove-Item -LiteralPath $TestRoot -Recurse -Force -ErrorAction SilentlyContinue
    $env:LOCALAPPDATA = $OriginalLocalAppData
    $env:AUTOMATION_CENTER_UI_PORT = $OriginalUiPort
}
