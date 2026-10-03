## Install the PowerShell network-rescue verbs (net-doctor, dns-set, rescue) to C:.
## Run as the `net-rescue` item of `just windows`, via install/win-dev.ps1.
##
## Copies windows/ to ~\.dotfiles rather than linking into WSL: the verbs exist for
## the day WSL or the network is down, when a \\wsl.localhost path cannot load.
## Idempotent. Re-run after editing windows/: `just windows` shows it unticked when the copy is stale.

$ErrorActionPreference = 'Stop'

$source = Join-Path (Split-Path $PSScriptRoot -Parent) 'windows'
$target = Join-Path $HOME '.dotfiles'

New-Item -ItemType Directory -Force -Path $target | Out-Null
foreach ($name in 'net.ps1', 'net-rescue.md') {
    $destination = Join-Path $target $name
    Copy-Item -Path (Join-Path $source $name) -Destination $destination -Force
    Unblock-File -Path $destination
    Write-Host "Copied $name to $target"
}

$profileLine = '. "$HOME\.dotfiles\net.ps1"  # dotfiles: network-rescue verbs (just windows net-rescue)'
$documents = [Environment]::GetFolderPath('MyDocuments')
foreach ($hostDir in 'WindowsPowerShell', 'PowerShell') {
    $profileDir = Join-Path $documents $hostDir
    $profilePath = Join-Path $profileDir 'profile.ps1'
    if ((Test-Path $profilePath) -and (Select-String -Path $profilePath -SimpleMatch '.dotfiles\net.ps1' -Quiet)) {
        Write-Host "$profilePath already loads the verbs, skipping"
        continue
    }
    New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
    Add-Content -Path $profilePath -Value $profileLine
    Write-Host "Added the verbs to $profilePath"
}

# This script runs under -ExecutionPolicy Bypass, so the Process scope says nothing
# about what a normal PowerShell window will do. -List is in precedence order.
$persistent = @(Get-ExecutionPolicy -List | Where-Object { $_.Scope -ne 'Process' -and $_.ExecutionPolicy -ne 'Undefined' })
$effective = if ($persistent) { $persistent[0] } else { $null }
if ($effective -and $effective.ExecutionPolicy -notin 'Restricted', 'AllSigned') {
    Write-Host "Execution policy is $($effective.ExecutionPolicy) ($($effective.Scope)), profiles already load"
} elseif ($effective -and $effective.Scope -in 'MachinePolicy', 'UserPolicy') {
    Write-Host "WARNING: group policy sets execution policy $($effective.ExecutionPolicy); the profile will not load." -ForegroundColor Yellow
    Write-Host "         Run the verbs with: powershell -ExecutionPolicy Bypass -NoExit -File `"$target\net.ps1`""
} else {
    try {
        Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
    } catch [System.Security.SecurityException] {
        # Raised because this process is Bypass; the CurrentUser value is still written.
    }
    if ((Get-ExecutionPolicy -Scope CurrentUser) -ne 'RemoteSigned') {
        throw 'Could not set the CurrentUser execution policy to RemoteSigned'
    }
    Write-Host 'Set execution policy to RemoteSigned for the current user, so the profile loads'
}

. (Join-Path $target 'net.ps1')
if (-not (Get-ChildItem -Path (Join-Path $HOME '.net-snapshots') -Filter '*.json' -ErrorAction SilentlyContinue)) {
    Write-Host "`nNo network snapshot yet, taking the first one:"
    net-snapshot
}

Write-Host "`nDone. Open a new PowerShell window and run: net-doctor, net-show, net-snapshot, net-restore, dns-set, rescue" -ForegroundColor Green
