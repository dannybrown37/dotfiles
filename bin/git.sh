unalias gc 2>/dev/null || true
gc() { # @doc Git commit with implicit quoting: gc fix the thing
    git commit -m "$*"
}
