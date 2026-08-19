param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$inventory = Get-Content -Raw (Join-Path $ProjectRoot 'docs\WORKFLOW_CREDENTIAL_INVENTORY.json') | ConvertFrom-Json
$summary = foreach ($workflowGroup in ($inventory | Group-Object workflow_file | Sort-Object Name)) {
    $entries = @($workflowGroup.Group)
    $providers = @($entries.detected_providers | ForEach-Object { $_ } | Sort-Object -Unique)
    $credentialTypes = @($entries.credential_references | ForEach-Object { $_ } | ForEach-Object { $_.credential_type } | Where-Object { $_ } | Sort-Object -Unique)
    $nodes = @($entries.node_name | Sort-Object -Unique)
    [PSCustomObject]@{
        workflow_file = $workflowGroup.Name
        providers = ($providers -join ', ')
        credential_types = ($credentialTypes -join ', ')
        credential_nodes = ($nodes -join ' | ')
    }
}
$summary | ConvertTo-Json -Depth 4
