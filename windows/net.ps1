## Offline network-rescue verbs for Windows PowerShell 5.1+. Dot-sourced from the
## PowerShell profile by `just windows net-rescue`, which copies this file to C: so it
## still loads when WSL is down.
##
##   net-doctor     diagnose in order, print the fix per failure
##   net-show       adapter / IP / gateway / DNS at a glance
##   net-snapshot   save the current config to ~\.net-snapshots
##   net-restore    reapply a snapshot (DNS only; -Full adds IP + gateway)
##   dns-set <ip>   set DNS on the adapter holding the default route
##   rescue         print the offline cheat sheet
##
## The Get-Net*Findings/Plan functions take data and return data, so the logic is
## tested without touching an adapter (scripts/test_net_ps1.py).

$script:NetInternetIp = '1.1.1.1'
$script:NetSnapshotDir = Join-Path $HOME '.net-snapshots'

function ConvertTo-NetQuoted([string]$Value) {
    return "'" + $Value.Replace("'", "''") + "'"
}

function Assert-NetIPv4([string]$Value) {
    $parsed = $null
    $isIPv4 = [System.Net.IPAddress]::TryParse($Value, [ref]$parsed) -and
        $parsed.AddressFamily -eq 'InterNetwork' -and
        $Value -match '^\d{1,3}(\.\d{1,3}){3}$'
    if (-not $isIPv4) { throw "'$Value' is not an IPv4 address" }
    return $Value
}

function Get-NetDnsCommand([string]$Alias, [string[]]$Servers) {
    $quoted = @($Servers | ForEach-Object { ConvertTo-NetQuoted (Assert-NetIPv4 $_) }) -join ','
    return "Set-DnsClientServerAddress -InterfaceAlias $(ConvertTo-NetQuoted $Alias) -ServerAddresses $quoted"
}

function New-NetFinding([string]$Status, [string]$Message, [string]$Fix = '') {
    return [pscustomobject]@{ Status = $Status; Message = $Message; Fix = $Fix }
}

function Get-NetDoctorFindings($Facts) {
    if (-not $Facts.Alias) {
        return @(New-NetFinding 'fail' 'No network adapter found.' 'Get-NetAdapter   (check the cable, or Device Manager)')
    }
    $alias = ConvertTo-NetQuoted $Facts.Alias
    $dnsServers = @($Facts.DnsServers | Where-Object { $_ })
    $findings = @()

    if ($Facts.LinkUp) {
        $findings += New-NetFinding 'ok' "Link is up on $alias."
    } else {
        $findings += New-NetFinding 'fail' "Adapter $alias is not up." "Enable-NetAdapter -Name $alias   (elevated; or check the cable)"
    }

    $addresses = @($Facts.IPv4 | Where-Object { $_ })
    if ($addresses) {
        $findings += New-NetFinding 'ok' "$alias has IPv4 address $($addresses -join ', ')."
    } else {
        $findings += New-NetFinding 'fail' "$alias has no IPv4 address." "net-restore -Full   (static)   or   ipconfig /renew   (DHCP)"
    }

    if ($Facts.Gateway) {
        $findings += New-NetFinding 'ok' "Default gateway is $($Facts.Gateway)."
        if ($Facts.GatewayReachable) {
            $findings += New-NetFinding 'ok' "Gateway $($Facts.Gateway) answers."
        } elseif ($Facts.InternetReachable) {
            $findings += New-NetFinding 'warn' "Gateway $($Facts.Gateway) ignores ping, but traffic gets through it."
        } else {
            $findings += New-NetFinding 'fail' "Gateway $($Facts.Gateway) does not answer." 'check the cable or Wi-Fi, then the router itself'
        }
    } else {
        $findings += New-NetFinding 'fail' 'No default gateway.' "New-NetRoute -InterfaceAlias $alias -DestinationPrefix 0.0.0.0/0 -NextHop <gateway-ip>   (elevated; or net-restore -Full)"
    }

    if ($Facts.InternetReachable) {
        $findings += New-NetFinding 'ok' "Internet is reachable by IP ($script:NetInternetIp)."
    } else {
        $findings += New-NetFinding 'fail' "Internet by IP: $script:NetInternetIp is unreachable." 'if the gateway answers, the fault is the router or ISP, not this machine'
    }

    if (-not $dnsServers) {
        $server = if ($Facts.Gateway) { $Facts.Gateway } else { '<dns-server-ip>' }
        $raw = if ($Facts.Gateway) { Get-NetDnsCommand $Facts.Alias @($Facts.Gateway) } else { "Set-DnsClientServerAddress -InterfaceAlias $alias -ServerAddresses <dns-server-ip>" }
        $findings += New-NetFinding 'fail' "No DNS server configured on $alias." "dns-set $server   (runs elevated: $raw)"
    } else {
        $findings += New-NetFinding 'ok' "DNS server configured: $($dnsServers -join ', ')."
        if ($Facts.DnsAnswers) {
            $findings += New-NetFinding 'ok' 'DNS answers (example.com resolves).'
        } else {
            $findings += New-NetFinding 'fail' "DNS server $($dnsServers -join ', ') is not answering." "dns-set $script:NetInternetIp   (tests with a public resolver; then ipconfig /flushdns)"
        }
    }
    return $findings
}

function Get-NetRestorePlan($Snapshot, $Current, [string]$TargetAlias, [switch]$Full) {
    $commands = @()
    $notes = @()
    $saved = @($Snapshot | Where-Object { $_.Alias -eq $TargetAlias })[0]
    if (-not $saved) { $saved = @($Snapshot | Where-Object { $_.Gateway })[0] }
    if (-not $saved) { $saved = @($Snapshot)[0] }
    $now = @($Current | Where-Object { $_.Alias -eq $TargetAlias })[0]

    if (-not $saved) {
        $notes += 'The snapshot is empty.'
        return [pscustomobject]@{ Commands = $commands; Notes = $notes }
    }

    $savedDns = @($saved.Dns | Where-Object { $_ })
    $nowDns = @($now.Dns | Where-Object { $_ })
    if (-not $savedDns) {
        $notes += "The snapshot has no DNS servers for '$($saved.Alias)'."
    } elseif (($savedDns -join ',') -ne ($nowDns -join ',')) {
        $commands += Get-NetDnsCommand $TargetAlias $savedDns
    }

    if ($Full) {
        $target = ConvertTo-NetQuoted $TargetAlias
        if ($saved.Alias -ne $TargetAlias) {
            $notes += "IP and gateway left alone: the snapshot is of '$($saved.Alias)', the gateway is now on '$TargetAlias'."
        } elseif ($saved.Dhcp) {
            $notes += 'IP and gateway left alone: the snapshot used DHCP. Run: ipconfig /renew'
        } elseif ($saved.IPv4 -ne $now.IPv4 -or $saved.Gateway -ne $now.Gateway) {
            $ip = ConvertTo-NetQuoted (Assert-NetIPv4 $saved.IPv4)
            $gateway = ConvertTo-NetQuoted (Assert-NetIPv4 $saved.Gateway)
            if ($now.IPv4) { $commands += "Remove-NetIPAddress -InterfaceAlias $target -AddressFamily IPv4 -Confirm:`$false" }
            if ($now.Gateway) { $commands += "Remove-NetRoute -InterfaceAlias $target -DestinationPrefix 0.0.0.0/0 -Confirm:`$false" }
            $commands += "New-NetIPAddress -InterfaceAlias $target -IPAddress $ip -PrefixLength $([int]$saved.PrefixLength) -DefaultGateway $gateway"
        }
    }
    return [pscustomobject]@{ Commands = $commands; Notes = $notes }
}

function Get-NetState {
    foreach ($config in @(Get-NetIPConfiguration | Where-Object { $_.NetAdapter.Status -eq 'Up' })) {
        $address = @($config.IPv4Address)[0]
        [pscustomobject]@{
            Alias        = $config.InterfaceAlias
            IPv4         = $address.IPAddress
            PrefixLength = $address.PrefixLength
            Gateway      = @($config.IPv4DefaultGateway)[0].NextHop
            Dns          = @($config.DNSServer | Where-Object { $_.AddressFamily -eq 2 } | ForEach-Object { $_.ServerAddresses })
            Dhcp         = $config.NetIPv4Interface.Dhcp -eq 'Enabled'
        }
    }
}

function Get-NetPrimaryAlias {
    $route = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
        Sort-Object { $_.RouteMetric + $_.InterfaceMetric } | Select-Object -First 1
    if ($route) { return $route.InterfaceAlias }
    $up = @(Get-NetAdapter | Where-Object { $_.Status -eq 'Up' })
    $real = @($up | Where-Object { $_.Name -notmatch 'Default Switch|WSL|Loopback|Bluetooth' })
    if ($real) { return $real[0].Name }
    if ($up) { return $up[0].Name }
    return @(Get-NetAdapter | Where-Object { $_.Name -notmatch 'Default Switch|WSL|Loopback|Bluetooth' })[0].Name
}

function Get-NetDoctorFacts {
    $alias = Get-NetPrimaryAlias
    if (-not $alias) { return [pscustomobject]@{ Alias = $null } }
    $route = Get-NetRoute -InterfaceAlias $alias -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
        Select-Object -First 1
    $gateway = $route.NextHop
    return [pscustomobject]@{
        Alias             = $alias
        LinkUp            = (Get-NetAdapter -Name $alias).Status -eq 'Up'
        IPv4              = @(Get-NetIPAddress -InterfaceAlias $alias -AddressFamily IPv4 -ErrorAction SilentlyContinue |
                Where-Object { $_.IPAddress -notlike '169.254.*' } | ForEach-Object { $_.IPAddress })
        Gateway           = $gateway
        GatewayReachable  = [bool]($gateway -and (Test-Connection -ComputerName $gateway -Count 1 -Quiet))
        InternetReachable = [bool](Test-Connection -ComputerName $script:NetInternetIp -Count 1 -Quiet)
        DnsServers        = @((Get-DnsClientServerAddress -InterfaceAlias $alias -AddressFamily IPv4 -ErrorAction SilentlyContinue).ServerAddresses)
        DnsAnswers        = [bool](Resolve-DnsName -Name 'example.com' -Type A -DnsOnly -QuickTimeout -ErrorAction SilentlyContinue)
    }
}

function Test-NetElevated {
    $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Every command reaching here was built by Get-NetDnsCommand / Get-NetRestorePlan
# from validated IPv4 addresses and a quoted adapter alias, never from raw input.
function Invoke-NetElevated([string[]]$Commands) {
    $Commands | ForEach-Object { Write-Host "  $_" -ForegroundColor Cyan }
    $script = "`$ErrorActionPreference = 'Stop'`n" + ($Commands -join "`n")
    if (Test-NetElevated) {
        & ([scriptblock]::Create($script))
        return
    }
    Write-Host 'Needs elevation: approve the UAC prompt.'
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
    Start-Process powershell -Verb RunAs -Wait -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', $encoded
}

function net-doctor {
    $icons = @{ ok = '[ OK ]'; warn = '[WARN]'; fail = '[FAIL]' }
    $colors = @{ ok = 'Green'; warn = 'Yellow'; fail = 'Red' }
    foreach ($finding in @(Get-NetDoctorFindings -Facts (Get-NetDoctorFacts))) {
        Write-Host "$($icons[$finding.Status]) $($finding.Message)" -ForegroundColor $colors[$finding.Status]
        if ($finding.Fix) { Write-Host "         fix: $($finding.Fix)" }
    }
}

function net-show {
    Get-NetState | Format-Table Alias, IPv4, PrefixLength, Gateway, @{ Name = 'Dns'; Expression = { $_.Dns -join ', ' } }, Dhcp -AutoSize
}

function net-snapshot {
    New-Item -ItemType Directory -Force -Path $script:NetSnapshotDir | Out-Null
    $file = Join-Path $script:NetSnapshotDir ("{0}.json" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
    ConvertTo-Json -Depth 4 -InputObject @(Get-NetState) | Set-Content -Path $file -Encoding UTF8
    Write-Host "Saved $file"
    net-show
}

function net-restore {
    param(
        [string]$Path,
        [switch]$Full,
        [switch]$Yes
    )
    if (-not $Path) {
        $latest = Get-ChildItem -Path $script:NetSnapshotDir -Filter '*.json' -ErrorAction SilentlyContinue |
            Sort-Object Name | Select-Object -Last 1
        if (-not $latest) {
            Write-Host "No snapshots in $script:NetSnapshotDir. Take one while the network works: net-snapshot"
            Write-Host 'Usage: net-restore [snapshot.json] [-Full] [-Yes]'
            return
        }
        $Path = $latest.FullName
    }
    $snapshot = Get-Content -Raw -Path $Path | ConvertFrom-Json
    $alias = Get-NetPrimaryAlias
    if (-not $alias) { Write-Host 'No network adapter found: run net-doctor'; return }

    Write-Host "Snapshot: $Path"
    @($snapshot) | Format-Table Alias, IPv4, Gateway, @{ Name = 'Dns'; Expression = { $_.Dns -join ', ' } } -AutoSize | Out-Host
    Write-Host 'Now:'
    net-show | Out-Host

    $plan = Get-NetRestorePlan -Snapshot @($snapshot) -Current @(Get-NetState) -TargetAlias $alias -Full:$Full
    $plan.Notes | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
    if (-not $plan.Commands) { Write-Host 'Nothing to restore.'; return }

    Write-Host 'Will run (elevated):'
    $plan.Commands | ForEach-Object { Write-Host "  $_" }
    if (-not $Yes) {
        if (-not [Environment]::UserInteractive) { throw 'net-restore: not interactive, pass -Yes to apply' }
        if ((Read-Host 'Apply? [y/N]') -notmatch '^[yY]') { Write-Host 'Nothing changed.'; return }
    }
    Invoke-NetElevated $plan.Commands
    net-show
}

function dns-set {
    param(
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Servers,
        [string]$Alias
    )
    if (-not $Alias) { $Alias = Get-NetPrimaryAlias }
    if (-not $Servers) {
        Write-Host 'Usage: dns-set <ip> [<ip>...] [-Alias "<adapter>"]'
        Write-Host "Sets the DNS servers on '$Alias' (the adapter holding the default route)."
        net-show
        return
    }
    if (-not $Alias) { Write-Host 'No network adapter found: run net-doctor'; return }
    Invoke-NetElevated @(Get-NetDnsCommand $Alias $Servers)
    ipconfig /flushdns | Out-Null
    net-show
}

function rescue {
    Get-Content -Path (Join-Path $PSScriptRoot 'net-rescue.md')
}
