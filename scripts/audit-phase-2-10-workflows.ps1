param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$automationIds = @('email-assistant', 'laboral', 'news', 'personal-brand', 'playwright-jobs')
$credentialProviderMap = @{
    'postgres' = 'postgresql'
    'postgresql' = 'postgresql'
    'gmailOAuth2' = 'google'
    'googleCalendarOAuth2Api' = 'google'
    'googleDocsOAuth2Api' = 'google'
    'googleOAuth2Api' = 'google'
    'googlePalmApi' = 'gemini'
    'telegramApi' = 'telegram'
    'httpHeaderAuth' = 'header_auth'
    'openAiApi' = 'openai'
    'anthropicApi' = 'anthropic'
    'openRouterApi' = 'openrouter'
}

function Get-ProviderFromHost([string]$HostName) {
    $normalized = $HostName.ToLowerInvariant()
    if ($normalized -match 'graph\.facebook\.com') { return 'whatsapp_cloud' }
    if ($normalized -match 'generativelanguage\.googleapis\.com') { return 'gemini' }
    if ($normalized -match 'api\.telegram\.org') { return 'telegram' }
    if ($normalized -match 'googleapis\.com') { return 'google' }
    if ($normalized -match 'api\.openai\.com') { return 'openai' }
    if ($normalized -match 'api\.anthropic\.com') { return 'anthropic' }
    if ($normalized -match 'openrouter\.ai') { return 'openrouter' }
    return $null
}

function Get-EnvironmentReferences([object]$Value) {
    $found = New-Object System.Collections.Generic.HashSet[string]
    function Visit([object]$Item) {
        if ($null -eq $Item) { return }
        if ($Item -is [string]) {
            foreach ($match in [regex]::Matches($Item, '\$env\.([A-Za-z_][A-Za-z0-9_]*)')) {
                [void]$found.Add($match.Groups[1].Value)
            }
            return
        }
        if ($Item -is [System.Collections.IEnumerable] -and -not ($Item -is [System.Collections.IDictionary])) {
            foreach ($child in $Item) { Visit $child }
            return
        }
        if ($Item.PSObject) {
            foreach ($property in $Item.PSObject.Properties) { Visit $property.Value }
        }
    }
    Visit $Value
    return @($found | Sort-Object)
}

function Get-SourceWorkflowPath([string]$AutomationId) {
    $map = @{
        'email-assistant' = '01-email-manager.json'
        'laboral' = '02-laboral.json'
        'news' = '03-news.json'
        'personal-brand' = '04-personal-brand.json'
        'playwright-jobs' = '05-playwright-jobs.json'
    }
    return Join-Path $ProjectRoot (Join-Path 'workflows' $map[$AutomationId])
}

$rows = foreach ($automationId in $automationIds) {
    $workflowPath = Join-Path $ProjectRoot (Join-Path (Join-Path 'automations' $automationId) 'workflow.json')
    $sourcePath = Get-SourceWorkflowPath $automationId
    $workflow = Get-Content -Raw -LiteralPath $workflowPath | ConvertFrom-Json
    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash
    $copyHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $workflowPath).Hash

    foreach ($node in @($workflow.nodes)) {
        $credentialTypes = @()
        if ($node.credentials) { $credentialTypes = @($node.credentials.PSObject.Properties.Name | Sort-Object -Unique) }
        $providers = New-Object System.Collections.Generic.HashSet[string]
        foreach ($credentialType in $credentialTypes) {
            if ($credentialProviderMap.ContainsKey($credentialType)) { [void]$providers.Add($credentialProviderMap[$credentialType]) }
        }
        $environmentVariables = Get-EnvironmentReferences $node.parameters
        $httpHost = $null
        if ($node.parameters -and $node.parameters.url) {
            $urlText = [string]$node.parameters.url
            if ($urlText -match 'https?://([^/\{]+)') { $httpHost = $Matches[1] }
        }
        $hostProvider = if ($httpHost) { Get-ProviderFromHost $httpHost } else { $null }
        if ($hostProvider) { [void]$providers.Add($hostProvider) }

        $internalDependencies = New-Object System.Collections.Generic.HashSet[string]
        if ($credentialTypes -contains 'postgres' -or $node.type -match 'postgres') { [void]$internalDependencies.Add('postgresql') }
        if (($environmentVariables -match 'PLAYWRIGHT').Count -gt 0 -or $node.name -match 'Playwright' -or $node.type -match 'playwright') { [void]$internalDependencies.Add('playwright') }

        $requiredSecrets = @($credentialTypes | ForEach-Object { "n8n credential type: $_" })
        $requiredSecrets += @($environmentVariables | ForEach-Object { "environment variable: $_" })
        if ($providers.Count -gt 0 -or $credentialTypes.Count -gt 0 -or $environmentVariables.Count -gt 0 -or $internalDependencies.Count -gt 0) {
            [PSCustomObject]@{
                automation = $automationId
                copy_workflow = "automations/$automationId/workflow.json"
                source_workflow = "workflows/$([System.IO.Path]::GetFileName($sourcePath))"
                source_copy_same_hash = ($sourceHash -eq $copyHash)
                node = $node.name
                node_type = $node.type
                credential_types = $credentialTypes
                providers = @($providers | Sort-Object)
                required_secret_or_reference = @($requiredSecrets | Sort-Object -Unique)
                environment_variables = $environmentVariables
                http_host = $httpHost
                internal_dependencies = @($internalDependencies | Sort-Object)
                external_dependency = if ($httpHost) { $httpHost } else { $null }
                parameter_fields = if ($node.parameters) { @($node.parameters.PSObject.Properties.Name | Sort-Object) } else { @() }
            }
        }
    }
}

$outputPath = Join-Path $ProjectRoot 'docs\PHASE_2_10_WORKFLOW_AUDIT.json'
$rows | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 -LiteralPath $outputPath
$summary = $rows | Group-Object automation | ForEach-Object {
    [PSCustomObject]@{
        automation = $_.Name
        relevant_nodes = $_.Count
        providers = @($_.Group.providers | ForEach-Object { $_ } | Sort-Object -Unique)
        environment_variables = @($_.Group.environment_variables | ForEach-Object { $_ } | Sort-Object -Unique)
        source_copy_same_hash = (@($_.Group.source_copy_same_hash | Select-Object -Unique) -join ',')
    }
}
$summary | ConvertTo-Json -Depth 5
Write-Output "AUDIT_OUTPUT=docs/PHASE_2_10_WORKFLOW_AUDIT.json;AUTOMATIONS=$($summary.Count);RELEVANT_NODES=$($rows.Count)"
