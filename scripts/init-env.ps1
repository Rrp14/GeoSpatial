$ErrorActionPreference = 'Stop'
$destination = Join-Path $PSScriptRoot '../.env'
if (Test-Path -LiteralPath $destination) {
    Write-Host '.env already exists; keeping it.'
    exit 0
}
function New-Secret {
    $bytes = New-Object byte[] 32
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}
$databaseSecret = New-Secret
$rootSecret = New-Secret
$applicationSecret = New-Secret
@"
POSTGRES_PASSWORD=$databaseSecret
MINIO_ROOT_USER=geo-admin
MINIO_ROOT_PASSWORD=$rootSecret
MINIO_ACCESS_KEY=geo-api
MINIO_SECRET_KEY=$applicationSecret
"@ | Set-Content -LiteralPath $destination -Encoding ascii
Write-Host 'Created .env with random local credentials.'
