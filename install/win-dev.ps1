## Install Windows-side dev tooling (git, uv, node, typescript, etc.)

$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

# ── winget packages ──────────────────────────────────────────────────────────
# Each entry: [winget ID, command to check]
$wingetPackages = @{
    "Git.Git"                    = "git"
    "GitHub.cli"                 = "gh"
    "Microsoft.PowerShell"       = "pwsh"
    "Microsoft.WindowsTerminal"  = "wt"
    "Microsoft.VisualStudioCode" = "code"
    "astral-sh.uv"              = "uv"
    "OpenJS.NodeJS.LTS"         = "node"
    "7zip.7zip"                 = "7z"
    "jqlang.jq"                 = "jq"
    "BurntSushi.ripgrep.MSVC"   = "rg"
    "sharkdp.fd"                = "fd"
    "sharkdp.bat"               = "bat"
    "junegunn.fzf"              = "fzf"
}

foreach ($id in $wingetPackages.Keys) {
    $cmd = $wingetPackages[$id]

    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "Installing $id ..."
        winget install --id $id --exact --accept-source-agreements --accept-package-agreements
    } else {
        Write-Host "$cmd already installed, skipping"
    }
}

# Refresh PATH after winget installs
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

# ── npm global packages (need node) ─────────────────────────────────────────

if (Get-Command npm -ErrorAction SilentlyContinue) {
    $npmGlobals = @("typescript", "ts-node", "npx")

    foreach ($pkg in $npmGlobals) {
        $installed = npm list --global $pkg 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Installing npm global: $pkg ..."
            npm install --global $pkg
        } else {
            Write-Host "npm global $pkg already installed, skipping"
        }
    }
} else {
    Write-Host "WARNING: node/npm not found after install — skipping npm globals" -ForegroundColor Yellow
}

# ── uv tools (need uv) ──────────────────────────────────────────────────────

if (Get-Command uv -ErrorAction SilentlyContinue) {
    $uvTools = @("ruff", "cookiecutter")

    foreach ($tool in $uvTools) {
        Write-Host "Installing uv tool: $tool ..."
        uv tool install $tool
    }
} else {
    Write-Host "WARNING: uv not found after install — skipping uv tools" -ForegroundColor Yellow
}

Write-Host "`nWindows dev tooling setup complete." -ForegroundColor Green
