# Insight Engine - Start Frontend and Backend Servers
# Usage: .\start_servers.ps1

$ErrorActionPreference = "Stop"

Write-Host "`n=== Insight Engine Server Startup ===" -ForegroundColor Cyan

# Check if ports are already in use
$port8000 = netstat -ano | findstr ":8000.*LISTENING"
$port5173 = netstat -ano | findstr ":5173.*LISTENING"

if ($port8000) {
    Write-Host "⚠ Backend already running on port 8000" -ForegroundColor Yellow
} else {
    Write-Host "Starting backend server..." -ForegroundColor Green
    Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m","uvicorn","backend.api.main:app","--host","0.0.0.0","--port","8000"
    Start-Sleep -Seconds 3
    Write-Host "✓ Backend started at http://localhost:8000" -ForegroundColor Green
}

if ($port5173) {
    Write-Host "⚠ Frontend already running on port 5173" -ForegroundColor Yellow
} else {
    Write-Host "Starting frontend server..." -ForegroundColor Green
    $frontendPath = Join-Path $PWD "frontend"
    Push-Location $frontendPath
    Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run dev"
    Pop-Location
    Start-Sleep -Seconds 5
    Write-Host "✓ Frontend started at http://localhost:5173/" -ForegroundColor Green
}

Write-Host "`n=== Server Status ===" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: http://localhost:5173/" -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop this script (servers will keep running)`n" -ForegroundColor Yellow

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} catch {
    Write-Host "`nStopping server monitor..." -ForegroundColor Yellow
}