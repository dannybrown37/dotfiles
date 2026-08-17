unalias make 2>/dev/null || true

function make() {  # @doc Run make, or just if a justfile exists and no Makefile | make <target>
    if [[ -f justfile || -f Justfile ]] && [[ ! -f Makefile && ! -f GNUmakefile ]]; then
        just "$@"
    else
        command make "$@"
    fi
}
