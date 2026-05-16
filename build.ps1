# build.ps1 — Genera el .exe de Spotify Sync Manager
# Uso: .\build.ps1
# Resultado: dist\Spotify Sync Manager\Spotify Sync Manager.exe

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "`n=== Spotify Sync Manager — Build ===" -ForegroundColor Cyan

# 1. Buildear el frontend React
Write-Host "`n[1/3] Construyendo frontend React..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\gui\frontend"
npm run build
if ($LASTEXITCODE -ne 0) { throw "npm run build falló" }
Set-Location $PSScriptRoot

# 2. Verificar que pyinstaller esté instalado
Write-Host "`n[2/3] Verificando PyInstaller..." -ForegroundColor Yellow
python -m PyInstaller --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Instalando PyInstaller..." -ForegroundColor Gray
    pip install pyinstaller
}

# 3. Generar el exe
Write-Host "`n[3/3] Empaquetando con PyInstaller..." -ForegroundColor Yellow
python -m PyInstaller spotify_sync.spec --noconfirm

Write-Host "`n=== Build completo ===" -ForegroundColor Green
Write-Host "Ejecutable: dist\`"Spotify Sync Manager`"\`"Spotify Sync Manager.exe`"" -ForegroundColor Cyan
Write-Host "Para distribuir, comprimí la carpeta dist\`"Spotify Sync Manager`" en un .zip`n"
