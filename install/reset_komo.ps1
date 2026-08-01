$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

if (-not (Get-Command komorebic -ErrorAction SilentlyContinue)) {
    Write-Host "komorebic not found, installing komorebi + whkd..."
    winget install LGUG2Z.komorebi
    winget install LGUG2Z.whkd
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
}

$wslDir = Split-Path -Parent $PSScriptRoot
$wslDir = Join-Path $wslDir "wsl"

Copy-Item -Path (Join-Path $wslDir "komorebi.json") -Destination "$env:USERPROFILE\komorebi.json" -Force
Copy-Item -Path (Join-Path $wslDir "komorebi.bar.json") -Destination "$env:USERPROFILE\komorebi.bar.json" -Force

$whkdConfigDir = Join-Path $env:USERPROFILE ".config"
New-Item -ItemType Directory -Path $whkdConfigDir -Force | Out-Null
Copy-Item -Path (Join-Path $wslDir "whkdrc") -Destination (Join-Path $whkdConfigDir "whkdrc") -Force

if (-not (Test-Path "$env:USERPROFILE\applications.json")) {
    Write-Host "applications.json not found, fetching application-specific configuration..."
    komorebic fetch-asc
}

komorebic stop
taskkill /f /im komorebi.exe
taskkill /f /im whkd.exe
taskkill /f /im komorebi-bar.exe
komorebic start --whkd --bar
