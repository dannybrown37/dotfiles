# Passthrough stubs for third-party tools installed via install/bash.sh or install/lazygit.sh.
# These functions exist solely so the tools appear in `cmds` with documentation.
# Add a stub here whenever a new third-party tool is installed that should be discoverable.

delta() { command delta "$@"; }        # @doc Syntax-highlighting pager for git diffs (replaces less)
fd() { command fdfind "$@"; }          # @doc Fast find that respects .gitignore | fd <pattern>
glow() { command glow "$@"; }          # @doc Render markdown in the terminal | glow <file>
hyperfine() { command hyperfine "$@"; } # @doc Benchmark commands head-to-head | hyperfine 'cmd1' 'cmd2'
lazygit() { command lazygit "$@"; }    # @doc TUI git client | lg (alias)
tokei() { command tokei "$@"; }        # @doc Count lines of code by language in current repo
