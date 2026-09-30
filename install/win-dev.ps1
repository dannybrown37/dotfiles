## Install Windows-side dev tooling (git, uv, node, typescript, etc.)
##
## -List          Print name<TAB>installed(0/1)<TAB>description for each item
## -Only a,b,c    Install only the named items (default: all)

param(
    [switch]$List,
    [string]$Only = ""
)

function Update-Path {
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
}

Update-Path

# Cmd is what Get-Command looks for; $null falls back to `winget list`
$wingetPackages = @(
    @{ Name = "git";        Id = "Git.Git";                    Cmd = "git";  Desc = "Git for Windows" }
    @{ Name = "gh";         Id = "GitHub.cli";                 Cmd = "gh";   Desc = "GitHub CLI" }
    @{ Name = "pwsh";       Id = "Microsoft.PowerShell";       Cmd = "pwsh"; Desc = "PowerShell 7" }
    @{ Name = "terminal";   Id = "Microsoft.WindowsTerminal";  Cmd = "wt";   Desc = "Windows Terminal" }
    @{ Name = "vscode";     Id = "Microsoft.VisualStudioCode"; Cmd = "code"; Desc = "VS Code" }
    @{ Name = "uv";         Id = "astral-sh.uv";               Cmd = "uv";   Desc = "Python package manager" }
    @{ Name = "node";       Id = "OpenJS.NodeJS.LTS";          Cmd = "node"; Desc = "Node.js LTS" }
    @{ Name = "7zip";       Id = "7zip.7zip";                  Cmd = "7z";   Desc = "Archive tool" }
    @{ Name = "jq";         Id = "jqlang.jq";                  Cmd = "jq";   Desc = "JSON processor" }
    @{ Name = "ripgrep";    Id = "BurntSushi.ripgrep.MSVC";    Cmd = "rg";   Desc = "Fast grep" }
    @{ Name = "fd";         Id = "sharkdp.fd";                 Cmd = "fd";   Desc = "Fast find" }
    @{ Name = "bat";        Id = "sharkdp.bat";                Cmd = "bat";  Desc = "cat with syntax highlighting" }
    @{ Name = "fzf";        Id = "junegunn.fzf";               Cmd = "fzf";  Desc = "Fuzzy finder" }
    @{ Name = "autohotkey"; Id = "AutoHotkey.AutoHotkey";      Cmd = $null;  Desc = "AutoHotkey v2" }
)
$npmGlobals = @("typescript", "ts-node", "npx")
$uvTools = @("ruff", "cookiecutter")

function Test-Winget($pkg) {
    if ($pkg.Cmd) {
        return [bool](Get-Command $pkg.Cmd -ErrorAction SilentlyContinue)
    }
    $listed = winget list --id $pkg.Id --exact --accept-source-agreements 2>$null | Out-String
    return $listed -match [regex]::Escape($pkg.Id)
}

function Test-NpmGlobals {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { return $false }
    npm list --global @npmGlobals *> $null
    return $LASTEXITCODE -eq 0
}

function Test-UvTools {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { return $false }
    $listed = uv tool list 2>$null | Out-String
    foreach ($tool in $uvTools) {
        if ($listed -notmatch "(?m)^$([regex]::Escape($tool)) ") { return $false }
    }
    return $true
}

function Install-NpmGlobals {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-Host "WARNING: node/npm not found — skipping npm globals" -ForegroundColor Yellow
        return
    }
    foreach ($pkg in $npmGlobals) {
        npm list --global $pkg *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Installing npm global: $pkg ..."
            npm install --global $pkg
        } else {
            Write-Host "npm global $pkg already installed, skipping"
        }
    }
}

function Install-UvTools {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "WARNING: uv not found — skipping uv tools" -ForegroundColor Yellow
        return
    }
    foreach ($tool in $uvTools) {
        Write-Host "Installing uv tool: $tool ..."
        uv tool install $tool
    }
}

$groups = @(
    @{ Name = "npm-globals"; Desc = "npm globals: $($npmGlobals -join ', ')"; Test = ${function:Test-NpmGlobals}; Install = ${function:Install-NpmGlobals} }
    @{ Name = "uv-tools";    Desc = "uv tools: $($uvTools -join ', ')";       Test = ${function:Test-UvTools};    Install = ${function:Install-UvTools} }
)

if ($List) {
    foreach ($pkg in $wingetPackages) {
        "{0}`t{1}`t{2}" -f $pkg.Name, [int](Test-Winget $pkg), $pkg.Desc
    }
    foreach ($group in $groups) {
        "{0}`t{1}`t{2}" -f $group.Name, [int](& $group.Test), $group.Desc
    }
    exit 0
}

$wanted = @($Only -split "," | Where-Object { $_ })
$known = @($wingetPackages.Name) + @($groups.Name)
$unknown = @($wanted | Where-Object { $_ -notin $known })
if ($unknown) {
    Write-Host "unknown item(s): $($unknown -join ' ')" -ForegroundColor Red
    Write-Host "available: $($known -join ' ')"
    exit 2
}

function Test-Wanted($name) { return (-not $wanted) -or ($name -in $wanted) }

foreach ($pkg in $wingetPackages) {
    if (-not (Test-Wanted $pkg.Name)) { continue }
    if (Test-Winget $pkg) {
        Write-Host "$($pkg.Id) already installed, skipping"
    } else {
        Write-Host "Installing $($pkg.Id) ..."
        winget install --id $pkg.Id --exact --accept-source-agreements --accept-package-agreements
    }
}

# npm globals and uv tools need node/uv on PATH from the winget step
Update-Path

foreach ($group in $groups) {
    if (Test-Wanted $group.Name) { & $group.Install }
}

Write-Host "`nWindows dev tooling setup complete." -ForegroundColor Green
