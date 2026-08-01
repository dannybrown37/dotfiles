## Docker Desktop helpers for WSL.
##
## Docker Desktop runs on the Windows side and injects its socket into this distro.
## Nothing here sets DOCKER_HOST or touches /var/run/docker.sock -- a hand-set
## DOCKER_HOST in a dotfile outlives the problem it solved and breaks confusingly.
##
## The Windows-side settings file is treated as strictly read-only: Docker Desktop
## owns it and rewrites it on exit, clobbering anything edited while it runs.

_docker_desktop_exe() {
    printf '%s' "/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe"
}

_docker_desktop_settings() {
    printf '%s' "/mnt/c/Users/${WINDOWS_USERNAME}/AppData/Roaming/Docker/settings.json"
}

_docker_require_wsl() {
    if [[ -z "${ON_WINDOWS:-}" ]]; then
        echo "${1}: only meaningful under WSL with Docker Desktop on the Windows host" >&2
        return 1
    fi
}

# Readiness is "the daemon serves a valid Server section", never process presence or
# socket existence. A starting or wedged engine keeps the socket open and answers 500,
# so a probe that only checks the exit code of a bare `docker info` reports false ready.
_docker_daemon_ready() {
    local server_version
    server_version="$(docker info --format '{{.ServerVersion}}' 2>/dev/null)" || return 1
    [[ -n "${server_version}" ]]
}

_docker_desktop_running() {
    tasklist.exe /FI "IMAGENAME eq Docker Desktop.exe" 2>/dev/null |
        tr -d '\r' | grep -q "Docker Desktop.exe"
}

docker-up() { # @doc Start Docker Desktop from WSL and block until the daemon answers | docker-up [timeout_seconds]
    _docker_require_wsl "docker-up" || return 1

    local timeout="${1:-90}"
    if [[ ! "${timeout}" =~ ^[0-9]+$ ]]; then
        echo "docker-up: timeout must be a whole number of seconds" >&2
        return 1
    fi

    if _docker_daemon_ready; then
        echo "Docker is already up."
        return 0
    fi

    # Launching a second Docker Desktop while one is still starting wedges the engine
    # into answering 500 on every API route, so only launch when nothing is running.
    if _docker_desktop_running; then
        echo "Docker Desktop is already running; waiting for the engine..."
    else
        local exe
        exe="$(_docker_desktop_exe)"
        if [[ ! -f "${exe}" ]]; then
            echo "docker-up: Docker Desktop not found at ${exe}" >&2
            return 1
        fi

        echo "Starting Docker Desktop (engine takes ~10-30s)..."
        # Subshell keeps this out of the shell's job table; the exe returns immediately.
        ("${exe}" >/dev/null 2>&1 &)
    fi

    local waited=0
    while ((waited < timeout)); do
        sleep 2
        waited=$((waited + 2))
        if _docker_daemon_ready; then
            printf '\nDocker is up after %ss.\n' "${waited}"
            return 0
        fi
        printf '.'
    done

    printf '\n'
    echo "docker-up: daemon did not respond within ${timeout}s. Run docker-doctor." >&2
    return 1
}

docker-doctor() { # @doc Diagnose why the docker CLI can't reach a daemon under WSL | docker-doctor
    _docker_require_wsl "docker-doctor" || return 1

    local settings problems=0
    settings="$(_docker_desktop_settings)"

    if _docker_daemon_ready; then
        echo "✅ Daemon is reachable (server $(docker info --format '{{.ServerVersion}}'))."
        return 0
    fi

    echo "❌ The daemon is not serving a valid response. Checking the three causes that look identical from the CLI:"
    echo ""

    if ! command -v docker &>/dev/null; then
        echo "❌ No docker CLI on PATH. Docker Desktop puts its shims in"
        echo "   /mnt/c/Program Files/Docker/Docker/resources/bin — check WSL interop is on."
        return 1
    fi

    if _docker_desktop_running; then
        echo "✅ Docker Desktop is running on the Windows host."
    else
        echo "❌ Docker Desktop is not running.  →  fix: docker-up"
        problems=$((problems + 1))
    fi

    if [[ ! -r "${settings}" ]]; then
        echo "⚠️  Can't read ${settings} — skipping the WSL integration checks."
        return 1
    fi

    local wsl_engine integrate_default integrated
    wsl_engine="$(jq -r '.wslEngineEnabled // false' "${settings}")"
    integrate_default="$(jq -r '.enableIntegrationWithDefaultWslDistro // false' "${settings}")"
    integrated="$(jq -r '.integratedWslDistros // [] | join(", ")' "${settings}")"

    if [[ "${wsl_engine}" == "true" ]]; then
        echo "✅ wslEngineEnabled: true"
    else
        echo "❌ wslEngineEnabled is false — Docker Desktop is in Windows-containers mode."
        echo "   →  fix (Windows side): Docker Desktop → Settings → General → use WSL 2 engine."
        problems=$((problems + 1))
    fi

    if [[ ",${integrated}," == *",${WSL_DISTRO_NAME},"* ]]; then
        echo "✅ ${WSL_DISTRO_NAME} is in integratedWslDistros [${integrated}]"
    elif [[ "${integrate_default}" == "true" ]]; then
        echo "⚠️  ${WSL_DISTRO_NAME} is not listed in integratedWslDistros [${integrated}],"
        echo "   but integration with the default distro is on. Confirm ${WSL_DISTRO_NAME} is"
        echo "   the default:  wsl.exe -l -v"
    else
        echo "❌ ${WSL_DISTRO_NAME} is not integrated [listed: ${integrated:-none}]"
        echo "   →  fix (Windows side): Docker Desktop → Settings → Resources → WSL integration."
        problems=$((problems + 1))
    fi

    echo ""
    if ((problems == 0)); then
        echo "Settings look correct but the daemon is still unreachable."
        echo "Try: docker-up, then restart Docker Desktop from Windows if that times out."
    fi
    echo "Note: ${settings} is read-only here — Docker Desktop rewrites it on exit."
    return 1
}
