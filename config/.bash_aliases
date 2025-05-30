##
## Aliases
##

alias awsconfig='nvim ~/.aws/config'
alias cb='tee >(xclip -selection clipboard)' # clip board
alias chrome='google-chrome 2>/dev/null &'
alias csi='fzf -m --preview="batcat --color=always {}" | xargs -r -I {} code "{}"' # code search interactive
alias du='du -h | sort -h'
alias eds='echo $DEV_STACK'
alias epoch='epoch_timestamp'
alias ff='fzf --preview="batcat --color=always {}"' # file find, just reviews, selection does nothing
alias gap='git add -p'
alias gg='google'
alias pcb='xclip -selection clipboard -o' # print clip board
alias rc='source ~/.bashrc'
alias url='open_url_in_browser'
alias utc='utc_timestamp'
alias uuid='generate_random_uuid_and_put_in_clipboard'
alias vc="grep -v -E '^\s*$|^#' \"\${DOTFILES_DIR}/nvim/notes.txt\" | sort | fzf" # vim cheat
alias vsd='rg --hidden --no-ignore -l "" | grep -Ev "$(echo $LS_IGNORE_GLOBS | tr "|" "\n")" 2>/dev/null | sed "s|^$HOME/projects/||" | fzf -m --info=hidden --preview="batcat --color=always {}" | xargs -r -I {} nvim -d "{}"'
alias vsi='fzf -m --info=hidden --preview="batcat --color=always {}" | xargs -r -I {} nvim "{}"' # vim search interactive

# Cargo package aliases

alias yless='jless --yaml'

alias dlog='git -c diff.external=difft log -p --ext-diff' # git log with patches shown with difftastic
alias dshow='git -c diff.external=difft show --ext-diff'  # Show the most recent commit with difftastic.
alias ddiff='git -c diff.external=difft diff'             # `git diff` with difftastic.

if [[ -n "${ON_WINDOWS}" ]]; then
    alias ahk='${DOTFILES_DIR}/ahk/ahk.sh'
    alias beep_c4='powershell.exe -c "[console]::beep(261, 300)"'
    alias beep_d4='powershell.exe -c "[console]::beep(294, 300)"'
    alias beep_e4='powershell.exe -c "[console]::beep(330, 300)"'
    alias beep_f4='powershell.exe -c "[console]::beep(349, 300)"'
    alias beep_g4='powershell.exe -c "[console]::beep(392, 300)"'
    alias beep_a4='powershell.exe -c "[console]::beep(440, 300)"'
    alias beep_b4='powershell.exe -c "[console]::beep(494, 300)"'
    alias beep_c5='powershell.exe -c "[console]::beep(523, 300)"'
    alias beep='beep_g4'
    alias ascend='beep_c4; beep_e4; beep_g4; beep_c5'
    alias descend='beep_c5; beep_g4; beep_e4; beep_c4'
    alias melody='beep_c5; beep_g4; beep_a4; beep_g4; beep_c4; beep_c5; beep_c4'
    alias monks='beep_a4; beep_a4; beep_g4; beep_g4; beep_f4; beep_e4; beep_a4; beep_c5; beep_b4; beep_a4; beep_a4; beep_g4; beep_a4'
fi

if [[ -f "${HOME}/.local/bin/zoxide" ]]; then
    eval "$(zoxide init bash --cmd cd)"  # essentially alias cd=z
fi

if dpkg-query -W -f='${Status}' exa eza 2>/dev/null | grep -q "ok installed"; then
    # https://the.exa.website/features/filtering
    alias l="exa --ignore-glob=\${LS_IGNORE_GLOBS}"
    alias ll="exa -alh --ignore-glob=\${LS_IGNORE_GLOBS}"
    alias lsa="exa -alh"
    alias ls=ll
    alias tree="exa --tree -la --ignore-glob=\${LS_IGNORE_GLOBS}"
fi

if dpkg-query -W -f='${Status}' bat 2>/dev/null | grep -q "ok installed"; then
    alias cat="batcat"
    alias bat="batcat"
    alias pcat="batcat -p"
    alias pbat="batcat -p"
fi

# dotfiles
alias idf='sudo apt upgrade && sudo apt install -y curl && curl -s https://raw.githubusercontent.com/dannybrown37/dotfiles/main/install/this_repo.sh | bash'
alias cdf='code ~/projects/dotfiles'

# npm
alias n='npm'
alias ni='npm install'
alias nt='npm test'
alias nr='npm run'
alias ns='npm start'
alias nsa='npm start -- --'
alias nrpk='npm run pytest -- -s -vv -k'

# Deno
alias di='deno install'
alias dt='deno run test'
alias dr='deno run'
alias drp='deno run pytest'
alias drpk='deno run pytest -k'

# Bash
alias src='source ~/.bashrc'
alias crc='code ~/.bashrc'
alias vrc='nvim ~/.bashrc'

# Python
alias rst='ruff check src tests'
alias rfst='ruff format src tests'
alias pv='python --version'
alias repl='uv run python'

# venv
alias pmv='python -m venv .venv && source .venv/bin/activate'
alias vba='source .venv/bin/activate'
alias nukevenv='deactivate ; rm -r .venv && python -m venv .venv && source .venv/bin/activate'
alias newdotenv='echo "source .venv/bin/activate" >> .env && echo "echo \"$(basename $(pwd)) env activated\"" >> .env && source .env'

# pytest
alias ptt='pytest tests'
alias ptu='pytest tests/unit'
alias pte='pytest tests/e2e'
alias ptc='pytest tests/e2e/cloud'
alias ptl='pytest tests/e2e/local'
alias ptff='pytest --ff'
alias ptlf='pytest --lf'

# pip
alias pir='pip install -r requirements.txt --require-virtualenv'
alias pirdev='pip install -r requirements.dev.txt --require-virtualenv'
alias pirdocs='pip install -r requirements.docs.txt --require-virtualenv'
alias pie='pip install -e . --require-virtualenv'
alias pf='pip freeze'
alias puf='pip freeze | xargs pip uninstall -y'
alias pup='python -m pip install --upgrade pip'

# Git
alias ga='git add'
alias gaa='git add .'
alias gap='git add -p'
alias gb='git branch --sort=-committerdate | fzf | xargs git checkout'
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
alias gitpurge='git branch | grep -v -e "main" -e "develop" -e "magic" -e "sword" -e "$(git rev-parse --abbrev-ref HEAD)" | xargs git branch -D'
alias gl='git log'
alias glinecount='git ls-files | xargs wc -l'
alias glo='git log -1 --pretty=%B'
alias gp='git push'
alias gpf='git push -f'
alias gpo='git push -u origin'
alias gpup='git push -u origin HEAD && git open'
alias gpr='git pull rebase'
alias gra='git rebase --abort'
alias grc='git rebase --continue'
alias grd='git rebase develop'
alias gresethard='git reset --hard origin/develop'
alias grh='git rebase -i HEAD~'
alias grm='git rebase main'
alias gs='git status'
alias gsi='git submodule update --init --recursive'
alias gsu='git submodule update'

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
alias tf='terraform'
alias tfi='terraform init'
alias tfv='terraform validate'
alias tff='terraform fmt'
alias tfp='terraform plan'
alias tfpro='terraform providers'
alias tfa='terraform apply'
alias tfs='terraform show'
alias tfsj='terraform show -json'
alias tfo='terraform output'
alias tfd='terraform destroy'
alias tfr='terraform refresh'
alias tfg='terraform graph | dot -Tsvg > graph.svg'
alias tfav='terraform apply -var'
alias tfavf='terraform apply -var-file *.tfvars'

# password-store
alias psgsk='gpg -K'
alias psgek='gpg --edit-key'
alias psgpgout='gpg --armor --export > public.gpg && gpg --armor --export-secret-key > private.gpg'
alias psscpkeys='scp -r username@ip_address:folder_with_keys_in_home_dir output_path'
alias psi='pass insert'
alias psgen='pass generate'
alias pse='pass edit'
alias psg='pass grep'
alias pss='pass show'
alias psc='pass show -c'
alias psr='pass rm'
alias psbashsecretsin='pass insert -m bash/secrets < .env'
alias psahksecretsin='pass insert -m ahk/secrets < .env'
alias psbashsecretsout='pass bash/secrets >> ~/projects/dotfiles/bash/.secrets'
alias psahksecretsout='pass ahk/secrets >> ~/projects/dotfiles/ahk/secrets.ahk'

# SSH
alias sshstart='sudo service ssh start'
alias sshstop='sudo service ssh stop'
alias sshstat='sudo service ssh status'
alias sship='curl ifconfig.me'
alias sshrestart='sudo service ssh restart'
alias sshconfig='sudo vi /etc/ssh/sshd_config'
alias sshenable='sudo systemctl enable ssh'
alias sshsystemstatus='sudo systemctl status ssh'
alias sshwslenable='sudo echo "[boot]\nsystemd=true" >> /etc/wsl.conf'

# WSL
alias editwslconf='sudo vi /etc/wsl.conf'

# Tmux
alias tms='tmux new -s Session || tmux attach -t Session'
alias tmd='tmux detach'
alias tml='tmux ls'
alias tmconf='tmux source-file ~/.tmux.conf'

# Fixes for weird situations
alias fixhashicorppublickey='wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg'
