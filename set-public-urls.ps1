param(
  [Parameter(Mandatory=$true)][string]$BackendUrl,
  [Parameter(Mandatory=$true)][string]$FrontendUrl
)

$root = "C:\Users\ngvhg\Downloads\Recognition_initialRace\Recognition_initialRace"
$backendHost = ($BackendUrl -replace '^https?://','') -replace '/$',''
$frontendOrigin = $FrontendUrl -replace '/$',''
$backendApi = ($BackendUrl -replace '/$','') + '/api/v1'

# Frontend env
$envFile = Join-Path $root 'frontend\.env.local'
"NEXT_PUBLIC_API_URL=$backendApi" | Set-Content -Encoding UTF8 $envFile

# Backend settings
$settings = Join-Path $root 'backend\config\settings.py'
$content = Get-Content $settings -Raw

if ($content -notmatch [regex]::Escape($backendHost)) {
  $content = $content.Replace('ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.1.6"', "ALLOWED_HOSTS = [\"localhost\", \"127.0.0.1\", \"192.168.1.6\", \"$backendHost\"")
  $content = $content.Replace('ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.1.6", "london-spelling-sauce-exceptional.trycloudflare.com"]', "ALLOWED_HOSTS = [\"localhost\", \"127.0.0.1\", \"192.168.1.6\", \"$backendHost\"]")
}

# Replace CORS list ending by inserting/updating frontend origin
if ($content -notmatch [regex]::Escape($frontendOrigin)) {
  $content = [regex]::Replace(
    $content,
    'CORS_ALLOWED_ORIGINS\s*=\s*\[(?s).*?\]',
    "CORS_ALLOWED_ORIGINS = [`n    \"http://localhost:3001\",`n    \"http://127.0.0.1:3001\",`n    \"http://localhost:3000\",`n    \"http://127.0.0.1:3000\",`n    \"http://192.168.1.6:3001\",`n    \"$frontendOrigin\",`n]"
  )
}

Set-Content -Path $settings -Value $content -Encoding UTF8

Write-Host "Configurado:"
Write-Host "  NEXT_PUBLIC_API_URL=$backendApi (frontend/.env.local)"
Write-Host "  ALLOWED_HOSTS incluye: $backendHost"
Write-Host "  CORS_ALLOWED_ORIGINS incluye: $frontendOrigin"
Write-Host ""
Write-Host "IMPORTANTE: como cambio NEXT_PUBLIC_API_URL debes reconstruir el frontend:"
Write-Host "  cd frontend; npm run build; npm run start (reinicia la ventana del frontend)"
Write-Host "Y reinicia el backend (Ctrl+C y python manage.py runserver 0.0.0.0:8001)."
