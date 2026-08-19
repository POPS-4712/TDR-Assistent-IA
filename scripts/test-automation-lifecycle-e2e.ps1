$ErrorActionPreference = 'Stop'
$api = 'http://localhost:8000/api/v1/automations/test-automation'
$installed = $false
$enabled = $false
try {
    $install = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$api/install"
    if ($install.StatusCode -ne 200) { throw "Install devolvió $($install.StatusCode)" }
    $installed = $true

    $enable = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$api/enable"
    if ($enable.StatusCode -ne 200) { throw "Enable devolvió $($enable.StatusCode)" }
    $enabled = $true

    $webhook = Invoke-WebRequest -UseBasicParsing -Method Post -Uri 'http://localhost:5678/webhook/automation-center-e2e-test' -ContentType 'application/json' -Body '{"source":"automation-center-e2e"}'
    if ($webhook.StatusCode -ne 200) { throw "Webhook devolvió $($webhook.StatusCode)" }

    $disable = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$api/disable"
    if ($disable.StatusCode -ne 200) { throw "Disable devolvió $($disable.StatusCode)" }
    $enabled = $false

    $uninstall = Invoke-WebRequest -UseBasicParsing -Method Delete -Uri $api
    if ($uninstall.StatusCode -ne 200) { throw "Uninstall devolvió $($uninstall.StatusCode)" }
    $installed = $false
    Write-Output 'E2E_LIFECYCLE=PASS;INSTALL=200;ENABLE=200;WEBHOOK=200;DISABLE=200;UNINSTALL=200'
}
finally {
    if ($enabled) { try { Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$api/disable" | Out-Null } catch {} }
    if ($installed) { try { Invoke-WebRequest -UseBasicParsing -Method Delete -Uri $api | Out-Null } catch {} }
}
