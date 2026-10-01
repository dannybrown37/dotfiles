# Passthrough stubs for third-party tools installed via install/ (incl. install/extras/).
# These functions exist solely so the tools appear in `cmds` with documentation.
# Add a stub here whenever a new third-party tool is installed that should be discoverable.

asciinema() { command asciinema "$@"; } # @doc Record and replay terminal sessions | asciinema rec session.cast
atuin() { command atuin "$@"; }         # @doc Shell history search/sync (replaces Ctrl+R) | atuin search
bubblewrap() { command bwrap "$@"; } # @doc Run a command in a sandbox | bwrap --ro-bind / / <cmd>
cartoon() { command cartoon "$@"; }     # @doc Compress noisy CLI output for AI agents | cartoon pytest
chrome() { command google-chrome "$@"; } # @doc Google Chrome browser | chrome <url>
claude() { command claude "$@"; }       # @doc Claude Code coding agent | claude
copilot() { command copilot "$@"; }     # @doc GitHub Copilot CLI coding agent | copilot
chafa() { command chafa "$@"; }         # @doc Render an image as terminal ANSI art -- powers `screenshot pick` previews | chafa <image>
cowsay() { command cowsay "$@"; }       # @doc ASCII cow speech bubbles | echo hi | cowsay
croc() { command croc "$@"; }           # @doc Send files between machines securely | croc send <file>
deno() { command deno "$@"; }           # @doc Deno JavaScript/TypeScript runtime | deno run <file>
delta() { command delta "$@"; }         # @doc Syntax-highlighting pager for git diffs (replaces less)
difftastic() { command difft "$@"; }    # @doc Diff that understands syntax | difft <old> <new>
docker() { command docker "$@"; }       # @doc Containers -- Docker Engine in WSL or Docker Desktop on Windows | just extras docker-engine
eza() { command eza "$@"; }             # @doc Modern ls replacement with git status and icons
faker() { command faker "$@"; }         # @doc Generate fake test data | faker name
fastfetch() { command fastfetch "$@"; } # @doc System info summary (neofetch successor) | fastfetch
fd() { command fdfind "$@"; }           # @doc Fast find that respects .gitignore | fd <pattern>
fzf() { command fzf "$@"; }             # @doc Interactive fuzzy finder for any list
gh() { command gh "$@"; }                  # @doc GitHub CLI -- PRs, issues, workflows, and more
gh-dash() { command gh dash "$@"; }           # @doc Terminal GitHub dashboard -- PRs, issues, notifications | gh-dash
gh-stack() { command gh stack "$@"; }         # @doc GitHub stacked PRs; git ship links stacks with it | gh-stack view
git-absorb() { command git-absorb "$@"; } # @doc Auto-fixup commits by matching hunks to the right commit | git-absorb
git-open() { command git-open "$@"; }   # @doc Open current repo/branch in browser | git-open [remote] [branch]
glow() { command glow "$@"; }           # @doc Render markdown in the terminal | glow <file>
hyperfine() { command hyperfine "$@"; } # @doc Benchmark commands head-to-head | hyperfine 'cmd1' 'cmd2'
htmlq() { command htmlq "$@"; }         # @doc jq for HTML | htmlq <selector> < page.html
httpie() { command http "$@"; }         # @doc Friendly HTTP client (httpie) | http GET <url>
jless() { command jless "$@"; }         # @doc Pager for JSON | jless <file.json>
just() { command just "$@"; }           # @doc Command runner (modern Make alternative) | just <recipe>
lazygit() { command lazygit "$@"; }     # @doc TUI git client | lg (alias)
lolcat() { command lolcat "$@"; }       # @doc Rainbow text | echo hi | lolcat
mprocs() { command mprocs "$@"; }       # @doc Run several commands side by side | mprocs 'cmd1' 'cmd2'
neofetch() { command fastfetch "$@"; } # @doc Alias for fastfetch, for muscle memory | neofetch
pass() { command pass "$@"; }           # @doc Password store -- manage secrets via GPG | pass show <name>
rg() { command rg "$@"; }               # @doc Fast regex search across files (ripgrep) | rg <pattern>
socat() { command socat "$@"; }         # @doc Relay data between sockets, ports, and files | socat TCP-LISTEN:8080,fork TCP:host:80
starship() { command starship "$@"; }   # @doc Cross-shell prompt with git/lang context
terraform() { command terraform "$@"; } # @doc Provision infrastructure as code | terraform plan
tldr() { command tldr "$@"; }           # @doc Simplified man pages with practical examples | tldr <cmd>
tmux() { command tmux "$@"; }           # @doc Terminal multiplexer -- sessions, windows, panes
tokei() { command tokei "$@"; }         # @doc Count lines of code by language in current repo
win32yank() { command win32yank.exe "$@"; } # @doc Fast Windows clipboard bridge for WSL | echo foo | win32yank.exe -i
zoxide() { command zoxide "$@"; }       # @doc Smarter cd that learns your most-used directories (alias: cd)
