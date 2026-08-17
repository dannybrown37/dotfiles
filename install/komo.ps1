## @just 43 Environment-Specific | Install komorebi/whkd if needed, then (re)start it
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
    komorebic fetch-application-specific-configuration
}

# --- phantom window reset -------------------------------------------------
# Phantom (ghost) tiles are windows komorebi still tracks but that are cloaked,
# minimized or already destroyed. They survive a naive restart because
# `komorebic start` re-applies a dumped state file from the previous instance,
# and because a hard taskkill skips the un-cloaking that `stop` performs.

if (Get-Process komorebi -ErrorAction SilentlyContinue) {
    # Snapshot the tracked windows first so a recurring offender can be
    # identified after the fact and given a permanent ignore rule.
    $report = Join-Path $env:TEMP "komorebi-visible-windows.json"
    komorebic visible-windows 2>$null | Set-Content -Path $report -Encoding UTF8
    Write-Host "Tracked windows before reset written to: $report"
    Write-Host "  If a phantom tile keeps returning, find its exe/class/title there and run:"
    Write-Host "    komorebic ignore-rule exe <name.exe>"

    # Un-cloak everything komorebi hid, so nothing is left invisible if the
    # graceful stop below does not complete.
    komorebic restore-windows 2>$null | Out-Null
}

komorebic stop --whkd --bar 2>$null | Out-Null

# Give komorebi a chance to exit cleanly (restoring windows as it goes) before
# resorting to force.
$deadline = (Get-Date).AddSeconds(10)
while ((Get-Date) -lt $deadline -and (Get-Process komorebi -ErrorAction SilentlyContinue)) {
    Start-Sleep -Milliseconds 250
}

foreach ($proc in @("komorebi", "whkd", "komorebi-bar")) {
    if (Get-Process $proc -ErrorAction SilentlyContinue) {
        Write-Host "$proc did not stop cleanly, forcing..."
        taskkill /f /im "$proc.exe" 2>$null | Out-Null
    }
}

# Drop any dumped state left behind by the previous instance; --clean-state
# tells komorebi not to reload it, and deleting it stops a later crash-restart
# from picking it up either.
Get-ChildItem -Path $env:TEMP -Filter "komorebi*.state*" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

komorebic start --whkd --bar --clean-state

# Re-tile from the freshly built state so no empty tiles are left over.
Start-Sleep -Seconds 2
komorebic retile 2>$null | Out-Null
