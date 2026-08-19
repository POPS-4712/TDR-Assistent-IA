param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$patterns = @(
    (Join-Path $ProjectRoot 'workflows\*.json'),
    (Join-Path $ProjectRoot 'automations\*\workflow.json')
)
$files = @($patterns | ForEach-Object { Get-ChildItem -Path $_ -File -ErrorAction SilentlyContinue }) |
    Sort-Object FullName -Unique

function Get-ProviderFromSignal([string]$signal) {
    $normalized = $signal.ToLowerInvariant()
    if ($normalized -match 'whatsapp|graph\.facebook\.com') { return 'whatsapp_cloud' }
    if ($normalized -match 'telegram') { return 'telegram' }
    if ($normalized -match 'postgres') { return 'postgresql' }
    if ($normalized -match 'gemini|generativelanguage') { return 'gemini' }
    if ($normalized -match 'google|gmail|docs|drive') { return 'google' }
    if ($normalized -match 'openai') { return 'openai' }
    if ($normalized -match 'anthropic') { return 'anthropic' }
    if ($normalized -match 'openrouter') { return 'openrouter' }
    if ($normalized -match 'header') { return 'header_auth' }
    return 'unknown'
}

$inventory = foreach ($file in $files) {
    $workflow = Get-Content -Raw -LiteralPath $file.FullName | ConvertFrom-Json
    foreach ($node in @($workflow.nodes)) {
        $credentialProperties = @()
        if ($node.credentials) {
            foreach ($property in $node.credentials.PSObject.Properties) {
                $credentialProperties += [PSCustomObject]@{
                    credential_type = $property.Name
                    credential_name = if ($property.Value.name) { '[configured-name]' } else { $null }
                    provider = Get-ProviderFromSignal $property.Name
                }
            }
        }
        $parameterKeys = @()
        if ($node.parameters) { $parameterKeys = @($node.parameters.PSObject.Properties.Name | Sort-Object) }
        $urlHost = $null
        if ($node.parameters -and $node.parameters.url) {
            $urlValue = [string]$node.parameters.url
            if ($urlValue -match 'https?://([^/\{]+)') { $urlHost = $Matches[1] }
        }
        $providerSignals = @($credentialProperties.provider)
        if ($urlHost -and $node.type -eq 'n8n-nodes-base.httpRequest') { $providerSignals += Get-ProviderFromSignal $urlHost }
        $providers = @($providerSignals | Where-Object { $_ -and $_ -ne 'unknown' } | Sort-Object -Unique)
        if ($credentialProperties.Count -gt 0 -or $providers.Count -gt 0) {
            [PSCustomObject]@{
                workflow_file = $file.FullName.Substring($ProjectRoot.Length + 1).Replace('\', '/')
                workflow_name = $workflow.name
                node_name = $node.name
                node_type = $node.type
                credential_references = $credentialProperties
                detected_providers = $providers
                parameter_fields = $parameterKeys
                http_host = $urlHost
            }
        }
    }
}

$outputPath = Join-Path $ProjectRoot 'docs\WORKFLOW_CREDENTIAL_INVENTORY.json'
$inventory | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 -LiteralPath $outputPath
$summary = $inventory | Group-Object { $_.workflow_file } | ForEach-Object {
    [PSCustomObject]@{ workflow_file = $_.Name; credential_nodes = $_.Count }
}
$summary | ConvertTo-Json -Depth 4
Write-Output "AUDIT_OUTPUT=docs/WORKFLOW_CREDENTIAL_INVENTORY.json;WORKFLOW_FILES=$($summary.Count);CREDENTIAL_NODES=$($inventory.Count)"
