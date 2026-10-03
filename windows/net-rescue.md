# Net Rescue

Offline cheat sheet. Read it with `rescue` (bash or PowerShell) or `refs net-rescue`.

## Network

| Task                                           | Command               | Where                                      |
| ---------------------------------------------- | --------------------- | ------------------------------------------ |
| Diagnose, in order, with the fix per failure   | `net-doctor`          | bash or PowerShell                         |
| Show adapter / IP / gateway / DNS              | `net-show`            | PowerShell                                 |
| Save the working config, before changing it    | `net-snapshot`        | PowerShell                                 |
| Put DNS back from the last snapshot            | `net-restore`         | PowerShell, add `-Full` for IP + gateway   |
| Set DNS on the adapter that has the gateway    | `dns-set 192.168.1.1` | PowerShell                                 |

Ping by IP works but names do not resolve = DNS. The raw commands, in an
elevated PowerShell (Win+X, then "Terminal (Admin)"):

```powershell
Get-NetIPConfiguration
Set-DnsClientServerAddress -InterfaceAlias "<adapter>" -ServerAddresses 192.168.1.1
ipconfig /flushdns
```

A new Hyper-V external switch moves the IP and gateway onto an adapter named
"vEthernet (\<switch\>)" and can drop the static DNS server on the way.

WSL (mirrored networking) borrows Windows' network. Its resolver,
10.255.255.254, only relays Windows' DNS, so fix Windows first.

## WSL

| Task                           | Command                               | Note                     |
| ------------------------------ | ------------------------------------- | ------------------------ |
| Restart WSL                    | `wsl --shutdown`                      | then reopen the terminal |
| List distros and their state   | `wsl -l -v`                           |                          |
| WSL will not start             | use PowerShell: `net-doctor`, `rescue` |                          |

## Hyper-V

| Task                              | Command                            | Note     |
| --------------------------------- | ---------------------------------- | -------- |
| Open a VM console with no network | `vmconnect.exe localhost homestead` |          |
| List VMs                          | `Get-VM`                           | elevated |
| List virtual switches             | `Get-VMSwitch`                     | elevated |

## First Install

The PowerShell verbs are copied to `C:` by `just windows net-rescue` (from WSL, while it works).
