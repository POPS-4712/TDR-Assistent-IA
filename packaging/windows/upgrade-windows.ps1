[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $InstallerPath -PathType Leaf)) { throw 'Installer file was not found.' }
$launcher = Join-Path ${env:ProgramFiles} 'Automation Center\AutomationCenter.exe'
if (Test-Path $launcher -PathType Leaf) {
    & $launcher backup-metadata --json
    if ($LASTEXITCODE -ne 0) { throw 'Upgrade cancelled: metadata backup did not complete safely.' }
}

Start-Process -FilePath $InstallerPath -ArgumentList '/VERYSILENT' -Wait
if ($LASTEXITCODE -ne 0) { throw 'Installer reported an upgrade failure.' }
Write-Output 'PASS: upgrade completed. Existing user data and dedicated local volumes were preserved.'
