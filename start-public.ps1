param()

$root = "C:\Users\ngvhg\Downloads\Recognition_initialRace\Recognition_initialRace"

# 1) Backend
Start-Process powershell -ArgumentList @(
  '-NoExit',
  '-Command',
  "Set-Location '$root\backend'; Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force; ..\.venv\Scripts\Activate.ps1; python manage.py migrate; python manage.py runserver 0.0.0.0:8001"
)

# 2) Frontend (usa la configuracion actual de .env.local)
Start-Process powershell -ArgumentList @(
  '-NoExit',
  '-Command',
  "Set-Location '$root\frontend'; npm run start"
)

# 3) Tunel backend
Start-Process powershell -ArgumentList @(
  '-NoExit',
  '-Command',
  "cloudflared tunnel --url http://localhost:8001"
)

# 4) Tunel frontend
Start-Process powershell -ArgumentList @(
  '-NoExit',
  '-Command',
  "cloudflared tunnel --url http://localhost:3001"
)

Write-Host "Se abrieron 4 ventanas: backend, frontend, tunel backend y tunel frontend."
Write-Host "Revisa en las ventanas de cloudflared las URLs publicas (https://....trycloudflare.com)."
Write-Host "Si las URLs cambiaron, ejecuta set-public-urls.ps1 con las nuevas URLs y luego reinicia backend y frontend."
