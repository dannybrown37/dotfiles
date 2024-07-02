#!/usr/bin/bash -i

## invoke with no argument to install all VS Code extensions below
## invoke with --uninstall to uninstall all VS Code extensions

extensions_to_install=(
    # visual/dev improvements
    aaron-bond.better-comments
    eamodio.gitlens
    equinusocio.vsc-material-theme-icons
    johnpapa.vscode-peacock
    oderwat.indent-rainbow
    streetsidesoftware.code-spell-checker
    usernamehw.errorlens

    # command-palette tools
    alefragnani.bookmarks
    donjayamanne.githistory

    # python
    charliermarsh.ruff
    mgesbert.indent-nested-dictionary
    ms-python.python

    # bash
    timonwong.shellcheck

    # js/ts
    dbaeumer.vscode-eslint
    esbenp.prettier-vscode
    orta.vscode-jest

    # markdown and protocols
    DavidAnson.vscode-markdownlint
    redhat.vscode-yaml
    shd101wyy.markdown-preview-enhanced
    tamasfe.even-better-toml
    zainchen.json

    # autocompletion, llms, etc.
    christian-kohler.path-intellisense
    VisualStudioExptTeam.vscodeintellicode
    VisualStudioExptTeam.vscodeintellicode-completions
    codeium.codeium
)

installed_extensions=$(code --list-extensions)

if [[ $* == *--uninstall* ]]; then
    code --list-extensions | xargs -L 1 code --uninstall-extension
    exit 0
fi

for extension_id in "${extensions_to_install[@]}"; do
    if [[ -z "${extension_id}" || "${extension_id}" =~ ^# ]]; then
        continue
    fi
    if [[ ! "${installed_extensions}" == *"${extension_id}"* ]]; then
        echo "Installing extension: ${extension_id}"
        code --install-extension "${extension_id}"
    fi
done

echo "All extensions have been installed."
