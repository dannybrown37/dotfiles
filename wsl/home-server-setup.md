# Windows Pro Home Server Setup

Turn a Windows Pro machine into a headless home server with SSH and Remote Desktop access.

## 1. Enable Remote Desktop (PowerShell as Admin)

```powershell
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
```

## 2. Install & Enable OpenSSH Server (PowerShell as Admin)

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
```

### Open firewall for SSH

Loopback SSH works without this, but connections from other machines on the
network need an explicit inbound rule:

```powershell
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

## 3. Find the Server's IP

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' } | Select IPAddress, InterfaceAlias
```

## 4. Set a Static IP

DHCP reservation on the router is cleanest, but setting it on the machine
works fine. Avoid `Remove-NetIPAddress` / `Remove-NetRoute` over SSH — they
can hang even with `-Confirm:$false`.

### Option A: DHCP reservation (router-side)

Grab the MAC address, then add a reservation in your router admin:

```powershell
Get-NetAdapter | Where-Object Status -eq 'Up' | Select Name, MacAddress
```

### Option B: Static IP on the machine

Use `netsh` — it's reliable over SSH and won't hang:

```powershell
netsh interface ip set address "Ethernet" static 192.168.1.200 255.255.255.0 192.168.1.1
netsh interface ip set dns "Ethernet" static 192.168.1.1
```

Or via PowerShell cmdlets (run locally, not over SSH):

```powershell
$adapter = "Ethernet"
Get-NetIPAddress -InterfaceAlias $adapter -AddressFamily IPv4 | Remove-NetIPAddress -Confirm:$false
Get-NetRoute -InterfaceAlias $adapter -AddressFamily IPv4 | Remove-NetRoute -Confirm:$false
New-NetIPAddress -InterfaceAlias $adapter -IPAddress 192.168.1.200 -PrefixLength 24 -DefaultGateway 192.168.1.1
Set-DnsClientServerAddress -InterfaceAlias $adapter -ServerAddresses 192.168.1.1
```

## 5. Test from Another Machine

```bash
# SSH
ssh your-windows-username@<SERVER_IP>

# RDP (GUI)
mstsc /v:<SERVER_IP>
```

## 6. Go Headless

Once both connections work, unplug the monitor and move the server to its
permanent spot. Ethernet in, power on, SSH from your other machine.
