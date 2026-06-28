$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

$wslDir = Split-Path -Parent $PSScriptRoot
$wslDir = Join-Path $wslDir "wsl"

Copy-Item -Path (Join-Path $wslDir "komorebi.json") -Destination "$env:USERPROFILE\komorebi.json" -Force
Copy-Item -Path (Join-Path $wslDir "komorebi.bar.json") -Destination "$env:USERPROFILE\komorebi.bar.json" -Force

komorebic stop
taskkill /f /im komorebi.exe
taskkill /f /im whkd.exe
taskkill /f /im komorebi-bar.exe
komorebic start --whkd --bar
