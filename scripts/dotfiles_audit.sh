#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091
# Audits the state of all dotfiles system dependencies.
# Read-only — does not install or modify anything.
# Usage: ./scripts/dotfiles_audit.sh

PASS="✅"
FAIL="❌"
WARN="⚠️ "
FAILURES=0

DOTFILES_DIR="${HOME}/projects/dotfiles"

# ── Helpers ───────────────────────────────────────────────────────────────────

ok() {
    local label="$1" version="$2"
    printf "  %s  %-32s %s\n" "$PASS" "$label" "$version"
}

fail() {
    local label="$1" hint="$2"
    printf "  %s  %-32s not found  →  %s\n" "$FAIL" "$label" "$hint"
    FAILURES=$((FAILURES + 1))
}

warn() {
    local label="$1" msg="$2"
    printf "  %s %-32s %s\n" "$WARN" "$label" "$msg"
}

check() {
    local label="$1" cmd="$2" hint="$3"
    local version
    if version=$(eval "$cmd" 2>/dev/null); then
        ok "$label" "$version"
    else
        fail "$label" "$hint"
    fi
}

check_apt() {
    local pkg="$1"
    if dpkg -s "$pkg" &>/dev/null; then
        local ver
        ver=$(dpkg -s "$pkg" 2>/dev/null | awk '/^Version:/{print $2}')
        ok "$pkg" "$ver"
    else
        fail "$pkg" "sudo apt install $pkg"
    fi
}

check_symlink() {
    local label="$1" link="$2" target="$3"
    if [[ -L "$link" ]]; then
        local actual
        actual=$(readlink "$link")
        if [[ "$actual" == "$target" ]]; then
            ok "$label" "→ $actual"
        else
            warn "$label" "exists but points to '$actual' (expected '$target')"
        fi
    elif [[ -f "$link" ]]; then
        warn "$label" "$link is a real file, not a symlink — run: make bash"
    else
        fail "$label" "run: make bash"
    fi
}

section() {
    echo ""
    echo "  $1"
    printf "  %s\n" "$(printf '─%.0s' {1..55})"
}

# ── Header ────────────────────────────────────────────────────────────────────

echo ""
echo "  ╔═══════════════════════════════════════════════════════╗"
echo "  ║          Dotfiles System Environment Audit            ║"
echo "  ╚═══════════════════════════════════════════════════════╝"

# ── System Info ───────────────────────────────────────────────────────────────

section "System Info"
DISTRO=$(grep "^PRETTY_NAME=" /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '"')
KERNEL=$(uname -r)
TOTAL_RAM=$(free -h | awk '/Mem:/{print $2}')
CPU_CORES=$(nproc)
DISK_FREE=$(df -h / | awk 'NR==2{print $4 " free of " $2}')

ok "distro"  "${DISTRO}"
ok "kernel"  "${KERNEL}"
ok "RAM"     "${TOTAL_RAM} total  •  ${CPU_CORES} cores"
ok "disk"    "${DISK_FREE} on /"

if [[ -n "${WSL_DISTRO_NAME:-}" ]]; then
    WSL_VER=$(wslinfo --wsl-version 2>/dev/null || echo "unknown")
    ok "WSL" "version ${WSL_VER}  (distro: ${WSL_DISTRO_NAME})"
fi

# ── Apt Packages ──────────────────────────────────────────────────────────────

section "Apt Packages"
apt_packages=(
    asciinema bash-completion bat cowsay curl direnv faker fd-find fzf git gh
    httpie jq make man-db lolcat neofetch openssh-server pass pipx rename
    ripgrep shellcheck shfmt tldr tmux unzip wget xclip zip
)
for pkg in "${apt_packages[@]}"; do
    check_apt "$pkg"
done

# ── Core CLI Tools ────────────────────────────────────────────────────────────

section "Core CLI Tools"
check "eza"        "eza --version | grep -oE 'v[0-9]+\\.[0-9]+\\.[0-9]+' | head -1"  "cargo install eza  (or: make bash)"
check "tokei"      "tokei --version | awk '{print \$2}'"                    "make bash"
check "hyperfine"  "hyperfine --version | awk '{print \$2}'"                "make bash"
check "glow"       "glow --version | awk '{print \$3}'"                     "make bash"
check "zoxide"     "zoxide --version | awk '{print \$2}'"                   "make bash  (installs to ~/.local/bin)"
check "delta"      "delta --version | awk '{print \$2}'"                    "make bash"
check "atuin"      "atuin --version | awk '{print \$2}'"                    "make bash"
check "croc"       "croc --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+'" "make bash  (installs to ~/.local/bin)"
check "starship"   "starship --version | head -1 | awk '{print \$2}'"       "make wsl-fonts"
check "lazygit"    "lazygit --version 2>&1 | grep -oE '[^a-z]version=[0-9.]+' | head -1 | cut -d= -f2" "make lazygit"
check "nvim"       "nvim --version | head -1 | awk '{print \$2}'"           "make nvim"

# ── GitHub & Auth ─────────────────────────────────────────────────────────────

section "GitHub & Auth"
check "gh" "gh --version | head -1 | awk '{print \$3}'" "sudo apt install gh"

GH_AUTH=$(gh auth status 2>&1)
if echo "$GH_AUTH" | grep -q "Logged in to"; then
    GH_USER=$(echo "$GH_AUTH" | grep "Logged in to" | awk '{print $NF}' | head -1)
    ok "gh auth" "logged in as ${GH_USER:-<unknown>}"
else
    fail "gh auth" "run: gh auth login"
fi

if [[ -f "$HOME/.ssh/id_ed25519.pub" ]]; then
    ok "SSH key" "$HOME/.ssh/id_ed25519.pub exists"
else
    warn "SSH key" "$HOME/.ssh/id_ed25519.pub not found"
fi

GIT_NAME=$(git config user.name 2>/dev/null)
GIT_EMAIL=$(git config user.email 2>/dev/null)
if [[ -n "$GIT_NAME" ]]; then
    ok "git user.name" "$GIT_NAME"
else
    fail "git user.name" "run: git config --global user.name \"Your Name\""
fi
if [[ -n "$GIT_EMAIL" ]]; then
    ok "git user.email" "$GIT_EMAIL"
else
    fail "git user.email" "run: git config --global user.email \"you@example.com\""
fi

# ── Config Symlinks ───────────────────────────────────────────────────────────

section "Config Symlinks"
check_symlink ".bashrc"            "$HOME/.bashrc"              "$DOTFILES_DIR/config/.bashrc"
check_symlink ".gitconfig"         "$HOME/.gitconfig"           "$DOTFILES_DIR/config/.gitconfig"
check_symlink ".gitignore_global"  "$HOME/.gitignore_global"    "$DOTFILES_DIR/config/.gitignore_global"
check_symlink ".ruff.toml"         "$HOME/.ruff.toml"           "$DOTFILES_DIR/config/.ruff.toml"
check_symlink ".eslintrc"          "$HOME/.eslintrc"            "$DOTFILES_DIR/config/.eslintrc"
check_symlink ".inputrc"           "$HOME/.inputrc"             "$DOTFILES_DIR/config/.inputrc"
check_symlink ".tmux.conf"         "$HOME/.tmux.conf"           "$DOTFILES_DIR/config/.tmux.conf"
check_symlink "starship.toml"      "$HOME/.config/starship.toml" "$DOTFILES_DIR/config/starship.toml"
check_symlink "lazygit config"     "$HOME/.config/lazygit/config.yml" "$DOTFILES_DIR/config/lazygit.yml"
check_symlink "nvim config"        "$HOME/.config/nvim"         "$DOTFILES_DIR/nvim"
check_symlink ".password-store"    "$HOME/.password-store"      "$DOTFILES_DIR/pass"

if [[ -d "$HOME/.tmux/plugins/tpm" ]]; then
    ok "tmux tpm" "installed"
else
    fail "tmux tpm" "run: make bash  (or: git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm)"
fi

# ── Node / NPM ────────────────────────────────────────────────────────────────

section "Node / NPM"
check "n"    "n --version"                          "curl -fsSL https://raw.githubusercontent.com/tj/n/master/bin/n | sudo bash -s 22"
check "node" "node --version | sed 's/v//'"         "make node"
check "npm"  "npm --version"                         "comes with node"

NODE_VER=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1)
if [[ -n "$NODE_VER" && "$NODE_VER" != "22" ]]; then
    warn "node version" "expected v22, got v${NODE_VER} — run: sudo n 22"
fi

# ── Python / uv ───────────────────────────────────────────────────────────────

section "Python / uv"
check "uv"    "uv --version | awk '{print \$2}'"    "curl -LsSf https://astral.sh/uv/install.sh | sh"
check "python" "python3 --version | awk '{print \$2}'" "uv python install"

uv_tools=(pre-commit cookiecutter ruff bashate)
for tool in "${uv_tools[@]}"; do
    if uv tool list 2>/dev/null | grep -q "^${tool} "; then
        ver=$(uv tool list 2>/dev/null | grep "^${tool} " | awk '{print $2}' | head -1)
        ok "uv tool: $tool" "${ver:-installed}"
    elif command -v "$tool" &>/dev/null; then
        ver=$("$tool" --version 2>/dev/null | head -1 | awk '{print $NF}')
        ok "uv tool: $tool" "${ver:-installed}"
    else
        fail "uv tool: $tool" "uv tool install $tool"
    fi
done

# ── Go ────────────────────────────────────────────────────────────────────────

section "Go"
check "go" "go version | awk '{print \$3}' | sed 's/go//'" "make golang"

if [[ -d "/usr/local/go" ]]; then
    ok "GOROOT" "/usr/local/go"
else
    fail "GOROOT" "/usr/local/go missing — run: make golang"
fi

# ── Rust ──────────────────────────────────────────────────────────────────────

section "Rust"
check "rustup"  "rustup --version 2>&1 | head -1 | awk '{print \$2}'"  "make rust"
check "cargo"   "cargo --version | awk '{print \$2}'"         "make rust"
check "rustc"   "rustc --version | awk '{print \$2}'"         "make rust"

cargo_tools=(htmlq jless mprocs)
for tool in "${cargo_tools[@]}"; do
    if command -v "$tool" &>/dev/null; then
        ver=$("$tool" --version 2>/dev/null | head -1 | awk '{print $NF}' || echo "installed")
        ok "cargo: $tool" "$ver"
    else
        fail "cargo: $tool" "cargo install $tool"
    fi
done

# ── Dev Tooling ───────────────────────────────────────────────────────────────

section "Dev Tooling"
check "pre-commit" "pre-commit --version | awk '{print \$2}'" "uv tool install pre-commit"

if [[ -f "${DOTFILES_DIR}/.git/hooks/pre-commit" ]]; then
    ok "pre-commit hooks" "installed"
else
    warn "pre-commit hooks" "not installed — run: pre-commit install  (in $DOTFILES_DIR)"
fi

check "pass" "pass --version 2>&1 | grep -oE 'v[0-9]+\\.[0-9]+\\.[0-9]+'" "sudo apt install pass"

if [[ -d "$HOME/.password-store" ]]; then
    ok "password-store" "present"
else
    warn "password-store" "~/.password-store missing — run: make bash"
fi

if grep -q "systemd=true" /etc/wsl.conf 2>/dev/null; then
    ok "wsl.conf systemd" "enabled"
elif [[ -n "${WSL_DISTRO_NAME:-}" ]]; then
    warn "wsl.conf systemd" "not enabled — add to /etc/wsl.conf: [boot] systemd=true"
fi

# ── VS Code Extensions ────────────────────────────────────────────────────────

section "VS Code Extensions"
EXTENSIONS_SCRIPT="${DOTFILES_DIR}/.vscode/vsc_extensions.sh"

if [[ ! -f "$EXTENSIONS_SCRIPT" ]]; then
    warn "VS Code" ".vscode/vsc_extensions.sh not found"
else
    # Parse extension IDs directly from the install array in the script
    mapfile -t expected_exts < <(
        awk '/^extensions_to_install=\(/,/^\)/{print}' "$EXTENSIONS_SCRIPT" \
            | grep -v '^#' \
            | grep -Eo '[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+'
    )

    EXT_DIR="$HOME/.vscode-server/extensions"
    if [[ ! -d "$EXT_DIR" ]]; then
        warn "VS Code extensions" "$EXT_DIR not found — has VS Code connected to WSL yet?"
    else
        for ext in "${expected_exts[@]}"; do
            matched=""
            for dir in "$EXT_DIR"/*; do
                base=$(basename "$dir")
                if [[ "${base,,}" == "${ext,,}-"* ]]; then
                    matched="$base"
                    break
                fi
            done
            if [[ -n "$matched" ]]; then
                ver=$(echo "$matched" | sed "s/^${ext}-//i" | sed 's/-linux.*$//')
                ok "$ext" "$ver"
            else
                fail "$ext" "code --install-extension ${ext}  (or: make vscode)"
            fi
        done
    fi
fi

# ── Environment Variables ─────────────────────────────────────────────────────

section "Environment Variables"
if [[ "${DOTFILES_DIR:-}" == "$HOME/projects/dotfiles" ]]; then
    ok "DOTFILES_DIR" "$DOTFILES_DIR"
else
    fail "DOTFILES_DIR" "expected $HOME/projects/dotfiles, got '${DOTFILES_DIR:-unset}'"
fi

if [[ -n "${NOTES_DIR:-}" ]]; then
    ok "NOTES_DIR" "$NOTES_DIR"
else
    warn "NOTES_DIR" "not set — add to .bashrc: export NOTES_DIR=\$HOME/notes"
fi

if [[ "${EDITOR:-}" == "nvim" ]]; then
    ok "EDITOR" "$EDITOR"
else
    warn "EDITOR" "expected 'nvim', got '${EDITOR:-unset}'"
fi

if echo "$PATH" | grep -q "${DOTFILES_DIR}/bin"; then
    ok "PATH includes dotfiles/bin" "${DOTFILES_DIR}/bin"
else
    fail "PATH includes dotfiles/bin" "source ~/.bashrc or check PATH in .bashrc"
fi

if echo "$PATH" | grep -q "${HOME}/.local/bin"; then
    ok "PATH includes ~/.local/bin" "${HOME}/.local/bin"
else
    warn "PATH includes ~/.local/bin" "not on PATH — may miss uv, zoxide, croc, atuin"
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "  ───────────────────────────────────────────────────────"
if [[ $FAILURES -eq 0 ]]; then
    echo "  ✅  All checks passed — environment looks good!"
else
    echo "  ❌  ${FAILURES} check(s) failed — see hints above"
fi
echo ""
