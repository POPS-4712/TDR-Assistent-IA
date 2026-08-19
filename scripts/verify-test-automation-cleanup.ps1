$ErrorActionPreference = 'Stop'
Invoke-RestMethod -Method Get -Uri 'http://localhost:8000/api/v1/automations/discover' | Out-Null
$response = Invoke-RestMethod -Method Get -Uri 'http://localhost:8000/api/v1/automations/test-automation'
$status = $response.automation.status
if ($status -ne 'discovered') { throw "El estado final esperado era discovered y se recibió '$status'." }
Write-Output "TEST_AUTOMATION_FINAL_STATUS=$status"
