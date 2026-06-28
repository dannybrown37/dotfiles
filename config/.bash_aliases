## Misc. Aliases

alias awsconfig='nvim ~/.aws/config'  # @doc Edit AWS config file in Neovim
alias cb='tee >(xclip -selection clipboard)' # @doc Copy stdin to clipboard. <command> | cb
alias du='du -h | sort -h'  # @doc Disk usage sorted and human-readable
alias epoch='epoch_timestamp'  # @doc Alias for epoch_timestamp
alias llmrules='pcat ~/projects/dotfiles/bin/llm_rules.txt | cb >/dev/null && echo "Copied to clipboard"' # @doc Copy LLM rules to clipboard for chatbot copy-paste
alias llmedit='nvim ~/projects/dotfiles/bin/llm_rules.txt' # @doc Edit LLM rules in Neovim
alias pcb='xclip -selection clipboard -o' # @doc Print clipboard contents
alias url='open_url_in_browser' # @doc Open a URL in the system browser
alias utc='utc_timestamp'  # @doc Alias for utc_timestamp
alias uuid='generate_random_uuid_and_put_in_clipboard'  # @doc Generate a random UUID and put it in the clipboard
alias vc="grep -v -E '^\s*$|^#' \"\${DOTFILES_DIR}/nvim/notes.txt\" | sort | fzf" # @doc Vim cheatsheet fuzzy finder
alias vsi='fzf -m --info=hidden --preview="batcat --color=always {}" | xargs -r nvim "{}"' # @doc Fuzzy find files and open in Neovim

# Tools I'm trying out

alias cinrec='asciinema rec session.cast'
alias cinplay='asciinema play session.cast'
alias crocsend='croc send'  # @doc Send a file via a Croc server | croc send <file>
alias crocinstall='curl https://getcroc.schollz.com | bash'  # @doc Install Croc

# Cargo package aliases

if [[ -n "${ON_WINDOWS}" ]]; then
    alias ahk='${DOTFILES_DIR}/ahk/ahk.sh' # @doc Run all AutoHotKey scripts (Windows only)
    alias beep='powershell.exe -c "[console]::beep(261, 300)"'  # @doc Play a beep sound (Windows only)
    alias komo='make -C "${DOTFILES_DIR}" komo' # @doc Reset komorebi window manager (Windows only)
fi

if [[ -f "${HOME}/.local/bin/zoxide" ]]; then
    eval "$(zoxide init bash --cmd cd)" # essentially alias cd=z
fi

if command -v eza &>/dev/null; then
    alias l="eza --ignore-glob=\${LS_IGNORE_GLOBS}"
    alias ll="eza -alh --ignore-glob=\${LS_IGNORE_GLOBS}"
    alias lsa="eza -alh"
    alias ls=ll
    alias tree="eza --tree -la --ignore-glob=\${LS_IGNORE_GLOBS}"  # @doc Show a tree view of files and directories
fi

if dpkg-query -W -f='${Status}' bat 2>/dev/null | grep -q "ok installed"; then
    alias cat="batcat"
    alias bat="batcat"
    alias pcat="batcat -p"
    alias pbat="batcat -p"
fi

# dotfiles
alias idf='sudo apt upgrade && sudo apt install -y curl && curl -s https://raw.githubusercontent.com/dannybrown37/dotfiles/main/install/this_repo.sh | bash'
alias cdf='code ~/projects/dotfiles'  # @doc Code Dot Files: Open the dotfiles repo in VSCode

# npm
alias ni='npm install'
alias nt='npm test'
alias nr='npm run'

# Deno
alias di='deno install'
alias dt='deno run test'
alias dr='deno run'
alias drp='deno run pytest'
alias drpk='deno run pytest -k'

# Bash
alias src='source ~/.bashrc' # @doc Reload bash configuration

# venv
alias pmv='python -m venv .venv && source .venv/bin/activate'
alias vba='source .venv/bin/activate'
alias nukevenv='deactivate ; rm -r .venv && python -m venv .venv && source .venv/bin/activate'
alias newdotenv='echo "source .venv/bin/activate" >> .env && echo "echo \"$(basename $(pwd)) env activated\"" >> .env && source .env'

# Git
alias ga='git add'
alias gaa='git add .'
alias gap='git add -p'
alias gb='git branch --sort=-committerdate | fzf | xargs git checkout' # @doc Fuzzy-find and checkout a git branch
alias gc='git commit -m'
alias gca='git commit --amend -m'
alias gcb='git checkout -b'
alias gcd='git checkout develop'
alias gcdf='git clone https://www.github.com/dannybrown37/dotfiles'
alias gcl='git checkout -'
alias gcm='git checkout main'
alias gco='git checkout'
__git_complete gco _git_checkout
alias gcr='git commit --amend --no-edit'
alias gcuemail='git config --global user.email "dannybrown37@gmail.com"'
alias gcuname='git config --global user.name "Danny Brown"'
unalias gitpurge 2>/dev/null
gitpurge() {  # @doc Delete all local branches except main, develop, and the current branch
    local current
    current=$(git rev-parse --abbrev-ref HEAD)
    git branch | sed 's/^[*+ ]*//' | while IFS= read -r branch; do
        case "$branch" in
            main|develop|bonfire|"$current") ;;
            *) git branch -D "$branch" ;;
        esac
    done
}
alias gl='git log'
alias gitlines='git ls-files | xargs wc -l'  # @doc Count lines of code in all files from curren branch
alias glo='git log -1 --pretty=%B'  # @doc Show last commit message (Git Log One-Line)
alias gp='git push'
alias gpf='git push -f'
alias gpo='git push -u origin'
alias gpup='git push -u origin HEAD && git open' # @doc Push new branch and open PR in browser
alias gpr='git pull rebase'
alias gra='git rebase --abort'
alias grc='git rebase --continue'
alias grd='git rebase develop'
alias gresethard='git reset --hard origin/develop'
alias grh='git rebase -i HEAD~'
alias grm='git rebase main'
alias gs='git status'
# alias gsi='git submodule update --init --recursive'
# alias gsu='git submodule update'

# GitHub CLI
alias ghd="BROWSER='cmd.exe /c start chrome' && export BROWSER && gh dash"
function ghpr() {
    gh pr list --limit 100 --json number,title,updatedAt,author --template \
        '{{range .}}{{tablerow .number .title .author.name (timeago .updatedAt)}}{{end}}' |
        fzf --height 25% --reverse |
        cut -f1 -d ' ' |
        xargs gh pr checkout
}

# Terraform
# alias tf='terraform'
# alias tfi='terraform init'
# alias tfv='terraform validate'
# alias tff='terraform fmt'
# alias tfp='terraform plan'
# alias tfpro='terraform providers'
# alias tfa='terraform apply'
# alias tfs='terraform show'
# alias tfsj='terraform show -json'
# alias tfo='terraform output'
# alias tfd='terraform destroy'
# alias tfr='terraform refresh'
# alias tfg='terraform graph | dot -Tsvg > graph.svg'
# alias tfav='terraform apply -var'
# alias tfavf='terraform apply -var-file *.tfvars'

# password-store
# alias psgsk='gpg -K'
# alias psgek='gpg --edit-key'
# alias psgpgout='gpg --armor --export > public.gpg && gpg --armor --export-secret-key > private.gpg'
# alias psscpkeys='scp -r username@ip_address:folder_with_keys_in_home_dir output_path'
# alias psi='pass insert'
# alias psgen='pass generate'
# alias pse='pass edit'
# alias psg='pass grep'
# alias pss='pass show'
# alias psc='pass show -c'
# alias psr='pass rm'
# alias psbashsecretsin='pass insert -m bash/secrets < .env'
# alias psahksecretsin='pass insert -m ahk/secrets < .env'
# alias psbashsecretsout='pass bash/secrets >> ~/projects/dotfiles/bash/.secrets'
# alias psahksecretsout='pass ahk/secrets >> ~/projects/dotfiles/ahk/secrets.ahk'

# SSH
# alias sshstart='sudo service ssh start'
# alias sshstop='sudo service ssh stop'
# alias sshstat='sudo service ssh status'
# alias sship='curl ifconfig.me'
# alias sshrestart='sudo service ssh restart'
# alias sshconfig='sudo vi /etc/ssh/sshd_config'
# alias sshenable='sudo systemctl enable ssh'
# alias sshsystemstatus='sudo systemctl status ssh'
# alias sshwslenable='sudo echo "[boot]\nsystemd=true" >> /etc/wsl.conf'

# WSL
alias editwslconf='sudo vi /etc/wsl.conf'

# Tmux
alias tms='tmux new -s Session || tmux attach -t Session' # @doc Start or attach to tmux Session
alias tmd='tmux detach'
alias tml='tmux ls'
alias tmconf='tmux source-file ~/.tmux.conf'  # @doc Reload tmux config

# Fixes for weird situations
# alias fixhashicorppublickey='wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg'
