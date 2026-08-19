param(
    [string]$WorkflowPath = (Join-Path $PSScriptRoot '..\automations\news\workflow.json')
)

$workflow = Get-Content -Raw $WorkflowPath | ConvertFrom-Json
$nodes = @($workflow.nodes | Where-Object { $_.type -eq 'n8n-nodes-base.httpRequest' })
foreach ($node in $nodes) {
    $url = [string]$node.parameters.url
    $safeUrl = $url -replace '\{\{[^}]+\}\}', '{{env}}'
    $authType = if ($node.credentials) { ($node.credentials.PSObject.Properties.Name -join ',') } else { 'none' }
    Write-Output "NODE=$($node.name)|URL=$safeUrl|CREDENTIAL_TYPES=$authType"
}
