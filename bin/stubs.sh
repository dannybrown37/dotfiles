# Passthrough stubs for third-party tools installed via install/bash.sh or install/lazygit.sh.
# These functions exist solely so the tools appear in `cmds` with documentation.
# Add a stub here whenever a new third-party tool is installed that should be discoverable.

asciinema() { command asciinema "$@"; }  # @doc Record and replay terminal sessions | asciinema rec session.cast
atuin() { command atuin "$@"; }          # @doc Shell history search/sync (replaces Ctrl+R) | atuin search
croc() { command croc "$@"; }            # @doc Send files between machines securely | croc send <file>
delta() { command delta "$@"; }          # @doc Syntax-highlighting pager for git diffs (replaces less)
eza() { command eza "$@"; }              # @doc Modern ls replacement with git status and icons
fd() { command fdfind "$@"; }            # @doc Fast find that respects .gitignore | fd <pattern>
fzf() { command fzf "$@"; }              # @doc Interactive fuzzy finder for any list
gh() { command gh "$@"; }               # @doc GitHub CLI -- PRs, issues, workflows, and more
git-open() { command git-open "$@"; }   # @doc Open current repo/branch in browser | git-open [remote] [branch]
glow() { command glow "$@"; }            # @doc Render markdown in the terminal | glow <file>
hyperfine() { command hyperfine "$@"; }  # @doc Benchmark commands head-to-head | hyperfine 'cmd1' 'cmd2'
lazygit() { command lazygit "$@"; }      # @doc TUI git client | lg (alias)
pass() { command pass "$@"; }            # @doc Password store -- manage secrets via GPG | pass show <name>
rg() { command rg "$@"; }               # @doc Fast regex search across files (ripgrep) | rg <pattern>
starship() { command starship "$@"; }    # @doc Cross-shell prompt with git/lang context
tldr() { command tldr "$@"; }            # @doc Simplified man pages with practical examples | tldr <cmd>
tmux() { command tmux "$@"; }            # @doc Terminal multiplexer -- sessions, windows, panes
tokei() { command tokei "$@"; }          # @doc Count lines of code by language in current repo
zoxide() { command zoxide "$@"; }        # @doc Smarter cd that learns your most-used directories (alias: cd)
