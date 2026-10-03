## Offline network recovery. Everything here must work with no network: the fix
## for a dead connection can't live on the internet.
##
## Under WSL (mirrored networking) this distro borrows the Windows host's address,
## gateway and DNS, and the resolver at 10.255.255.254 only relays Windows' DNS.
## A failure seen here is nearly always a Windows-side fault, so net-doctor hands
## over to the PowerShell net-doctor in windows/net.ps1, which names the adapter.

_net_fix() {
    local linux_fix="$1" wsl_fix="$2"
    if [[ -n "${ON_WINDOWS:-}" ]]; then
        echo "   →  fix (Windows side): ${wsl_fix}"
    else
        echo "   →  fix: ${linux_fix}"
    fi
}

_net_windows_doctor() {
    local dotfiles_dir="${DOTFILES_DIR:-$HOME/projects/dotfiles}"
    echo ""
    if ! command -v powershell.exe &>/dev/null; then
        echo "WSL borrows Windows' network: open Windows PowerShell and run: net-doctor"
        return
    fi
    echo "WSL borrows Windows' network. Checking the Windows side:"
    echo ""
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \
        ". '$(wslpath -w "${dotfiles_dir}/windows/net.ps1")'; net-doctor" | tr -d '\r'
    echo ""
    echo "Windows all ✅ but WSL still failing?  →  fix: wsl.exe --shutdown, then reopen the terminal"
}

net-doctor() { # @doc Diagnose a dead network in order (link, IP, gateway, internet, DNS) and print each fix | net-doctor
    local resolv_conf="${NET_DOCTOR_RESOLV_CONF:-/etc/resolv.conf}"
    local internet_ip="1.1.1.1" windows_dns="dns-set <dns-server-ip>, e.g. the gateway"
    local route gateway iface address nameservers problems=0 internet_up=""

    route="$(ip -4 route show default 2>/dev/null | head -1)"
    gateway="$(awk '{for (i = 1; i < NF; i++) if ($i == "via") print $(i + 1)}' <<<"${route}")"
    iface="$(awk '{for (i = 1; i < NF; i++) if ($i == "dev") print $(i + 1)}' <<<"${route}")"
    if [[ -z "${iface}" ]]; then
        iface="$(ip -br link show up 2>/dev/null | awk '$1 != "lo" {sub(/@.*/, "", $1); print $1; exit}')"
    fi

    if [[ -z "${iface}" ]]; then
        echo "❌ No network interface is up."
        _net_fix "sudo ip link set <interface> up   (list them: ip -br link)" \
            "net-doctor in PowerShell names the adapter"
        [[ -n "${ON_WINDOWS:-}" ]] && _net_windows_doctor
        return 1
    fi
    echo "✅ Link is up on ${iface}."

    address="$(ip -4 -br addr show dev "${iface}" 2>/dev/null | awk '{print $3}')"
    if [[ -n "${address}" ]]; then
        echo "✅ ${iface} has IPv4 address ${address}."
    else
        echo "❌ ${iface} has no IPv4 address."
        _net_fix "sudo dhclient ${iface}" "net-restore -Full, or ipconfig /renew"
        problems=$((problems + 1))
    fi

    if [[ -n "${gateway}" ]]; then
        echo "✅ Default gateway is ${gateway}."
    else
        echo "❌ No default gateway."
        _net_fix "sudo ip route add default via <gateway-ip> dev ${iface}" "net-restore -Full"
        problems=$((problems + 1))
    fi

    ping -c 1 -W 2 "${internet_ip}" &>/dev/null && internet_up=1

    if [[ -n "${gateway}" ]]; then
        if ping -c 1 -W 2 "${gateway}" &>/dev/null; then
            echo "✅ Gateway ${gateway} answers."
        elif [[ -n "${internet_up}" ]]; then
            echo "⚠️  Gateway ${gateway} ignores ping, but traffic gets through it."
        else
            echo "❌ Gateway ${gateway} does not answer."
            echo "   →  fix: check the cable or Wi-Fi, then the router itself"
            problems=$((problems + 1))
        fi
    fi

    if [[ -n "${internet_up}" ]]; then
        echo "✅ Internet is reachable by IP (${internet_ip})."
    else
        echo "❌ Internet by IP: ${internet_ip} is unreachable."
        echo "   →  fix: if the gateway answers, the fault is the router or ISP, not this machine"
        problems=$((problems + 1))
    fi

    nameservers="$(awk '$1 == "nameserver" {print $2}' "${resolv_conf}" 2>/dev/null | paste -sd ' ')"
    if [[ -z "${nameservers}" ]]; then
        echo "❌ No DNS server configured in ${resolv_conf}."
        _net_fix "echo 'nameserver ${gateway:-<dns-server-ip>}' | sudo tee ${resolv_conf}" "${windows_dns}"
        problems=$((problems + 1))
    else
        echo "✅ DNS server configured: ${nameservers}."
        if timeout 5 getent ahostsv4 example.com &>/dev/null; then
            echo "✅ DNS answers (example.com resolves)."
        elif [[ -n "${ON_WINDOWS:-}" ]]; then
            echo "❌ DNS server ${nameservers} is not answering. It only relays Windows' DNS."
            echo "   →  fix (Windows side): ${windows_dns}"
            problems=$((problems + 1))
        else
            echo "❌ DNS server ${nameservers} is not answering."
            echo "   →  fix: echo 'nameserver ${internet_ip}' | sudo tee ${resolv_conf}   (tests with a public resolver)"
            problems=$((problems + 1))
        fi
    fi

    ((problems == 0)) && return 0
    [[ -n "${ON_WINDOWS:-}" ]] && _net_windows_doctor
    return 1
}

rescue() { # @doc Offline cheat sheet: network recovery, Hyper-V console, restarting WSL | rescue
    cat "${DOTFILES_DIR:-$HOME/projects/dotfiles}/windows/net-rescue.md"
}
