$ErrorActionPreference = 'Stop'
$testName = "e2e-backup-restore-$(New-Guid)"
$backup = @{
    kind = 'automation-center-metadata-backup'
    schema_version = '1.0'
    exported_at = (Get-Date).ToUniversalTime().ToString('o')
    automations = @()
    credential_metadata = @()
    settings = @()
    profile_templates = @()
    manifests = @()
    profiles = @(@{
        name = $testName
        description = 'Perfil temporal aislado para validar restore idempotente.'
        profession_name = 'QA'
        profession_sector = 'Software'
        profession_level = 'Test'
        goals = @('validacion')
        languages = @('es')
        excluded_topics = @()
        is_enabled = $true
        preference = @{
            news_frequency = 'daily'
            relevance_level = 'high'
            sources = @()
            preferred_schedule = $null
            notifications_enabled = $true
            additional_settings = @{}
        }
        interests = @(@{ name = 'testing'; weight = 5 })
        skills = @('qa')
        companies = @()
        locations = @()
        topics = @()
        automations = @()
    })
}

$body = @{ backup = $backup; dry_run = $false } | ConvertTo-Json -Depth 100
$createdId = $null
try {
    $first = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/v1/backup/restore' -ContentType 'application/json' -Body $body
    $second = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/v1/backup/restore' -ContentType 'application/json' -Body $body
    $profiles = (Invoke-RestMethod -Method Get -Uri 'http://localhost:8000/api/v1/profiles').profiles
    $matching = @($profiles | Where-Object { $_.name -eq $testName })
    if ($matching.Count -ne 1) { throw "Se esperó un único perfil temporal y se encontraron $($matching.Count)." }
    $createdId = $matching[0].id
    if ($first.profiles -ne 1 -or $second.profiles -ne 0) { throw 'La restauración no fue idempotente.' }
    Write-Output "RESTORE_IDEMPOTENT=True;FIRST_PROFILES=$($first.profiles);SECOND_PROFILES=$($second.profiles);TEMP_PROFILE_COUNT=$($matching.Count)"
}
finally {
    if ($createdId) {
        Invoke-WebRequest -Method Delete -Uri "http://localhost:8000/api/v1/profiles/$createdId" -UseBasicParsing | Out-Null
        Write-Output 'TEMP_PROFILE_CLEANUP=True'
    }
}
