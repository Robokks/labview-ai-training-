# 5. Network setup (direct cable)

Step by step for the cable between the two PCs. Run each block in an **administrator
PowerShell** on the PC named.

> **Before you start:** get IT's approval. This link lets an internet-connected PC send
> commands to the offline PC ([Privacy](03-privacy.md#the-cable-link)).

## Plan

| | Internet PC | Offline PC |
|---|---|---|
| Cable IP | `192.168.50.1/24` | `192.168.50.2/24` |
| Gateway on cable | none | **none** |
| DNS on cable | none | **none** |
| Listens on the cable | Relay (later) | DynasBrain gateway, TCP `8765` |

No gateway and no DNS on the cable means the offline PC still has **no route to the
internet**, and the internet PC keeps using its normal adapter for the internet.

## Step 1: find the cable adapter (both PCs)

Plug in the cable, then:

```powershell
Get-NetAdapter | Format-Table Name, InterfaceDescription, Status, LinkSpeed
```

Note the **Name** of the adapter that shows `Up` for the cable (e.g. `Ethernet 2`). It is
used as `$nic` below.

## Step 2: fixed IP addresses

**Internet PC:**

```powershell
$nic = "Ethernet 2"     # your cable adapter name from step 1
Remove-NetIPAddress -InterfaceAlias $nic -Confirm:$false -ErrorAction SilentlyContinue
New-NetIPAddress   -InterfaceAlias $nic -IPAddress 192.168.50.1 -PrefixLength 24
Set-DnsClientServerAddress -InterfaceAlias $nic -ResetServerAddresses
```

**Offline PC:**

```powershell
$nic = "Ethernet"       # your cable adapter name from step 1
Remove-NetIPAddress -InterfaceAlias $nic -Confirm:$false -ErrorAction SilentlyContinue
New-NetIPAddress   -InterfaceAlias $nic -IPAddress 192.168.50.2 -PrefixLength 24
Set-DnsClientServerAddress -InterfaceAlias $nic -ResetServerAddresses
```

Do **not** add `-DefaultGateway` on either PC's cable adapter.

## Step 3: network profile (both PCs)

A cable without a gateway shows up as "Unidentified network". Mark it Private so the
firewall rules below behave predictably:

```powershell
Set-NetConnectionProfile -InterfaceAlias $nic -NetworkCategory Private
```

## Step 4: firewall on the offline PC

Allow the DynasBrain port **only** from the internet PC, and only on the cable adapter:

```powershell
New-NetFirewallRule -DisplayName "DynasBrain gateway (cable only)" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 `
  -RemoteAddress 192.168.50.1 -InterfaceAlias $nic -Profile Any
```

Optional, for testing with `ping` from the internet PC:

```powershell
New-NetFirewallRule -DisplayName "Ping from internet PC (cable)" `
  -Direction Inbound -Action Allow -Protocol ICMPv4 -IcmpType 8 `
  -RemoteAddress 192.168.50.1 -InterfaceAlias $nic -Profile Any
```

## Step 5: check the link

From the **internet PC**:

```powershell
ping 192.168.50.2                                   # needs the optional ping rule
```

From the **offline PC**, confirm it still has no internet:

```powershell
Test-NetConnection 8.8.8.8 -Port 443                # must show TcpTestSucceeded : False
route print -4 | Select-String "0.0.0.0"            # no default route via the cable
```

## Step 6: first read-only test (milestone L1)

This works **with today's DynasBrain**, before the gateway is built.

**Offline PC:** serve DynasBrain on the cable address:

```powershell
dynasbrain serve --host 192.168.50.2 --port 8765
```

**Internet PC:** check the port, then connect Claude Code to it:

```powershell
Test-NetConnection 192.168.50.2 -Port 8765          # TcpTestSucceeded : True
claude mcp add --transport http --scope user dynasbrain-offline http://192.168.50.2:8765/mcp
claude -p "Use dynasbrain-offline: list the projects, then explain the main VI of one of them."
```

> **Caution:** today's `serve --host` has **no access key**, and it exposes the whole web UI
> and API, not only the read-only MCP tools. The firewall rule in step 4 is the only
> protection, which is acceptable for a short test. The gateway (L1/L2) adds the access key
> and serves only what is needed on the cable.
>
> With Claude Code, the answers are sent to Anthropic. Use a **non-confidential test
> project** for this step.

## Undoing the setup

```powershell
Remove-NetFirewallRule -DisplayName "DynasBrain gateway (cable only)"
Remove-NetFirewallRule -DisplayName "Ping from internet PC (cable)" -ErrorAction SilentlyContinue
Remove-NetIPAddress -InterfaceAlias $nic -Confirm:$false
```
