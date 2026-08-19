$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$bytes = New-Object byte[] 48
$rng.GetBytes($bytes)
$rng.Dispose()
$n8nKey = [Convert]::ToBase64String($bytes).Replace('+','A').Replace('/','B').Replace('=','')
$alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
$dbPassword = -join (1..32 | ForEach-Object { $alphabet[(Get-Random -Minimum 0 -Maximum $alphabet.Length)] })
Write-Output "N8N_ENCRYPTION_KEY=$n8nKey"
Write-Output "POSTGRES_PASSWORD=$dbPassword"
