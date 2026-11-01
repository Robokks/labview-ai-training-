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
| Listens on the cable | DynasBrain relay, TCP `8766` | DynasBrain gateway, TCP `8765` |

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

## Step 6: the gateway on the offline PC (milestone L1)

The gateway serves DynasBrain's **read-only** tools on the cable, and only to a
**session token**: one per question, bound to one project, valid 30 minutes.

**Offline PC:**

```powershell
dynasbrain gateway --host 192.168.50.2               # port 8765, Ctrl+C to stop
```

**First test with Claude Code on the internet PC.** Use a **non-confidential test
project**, because Claude Code sends what it reads to Anthropic. On the offline PC,
issue a token (`--cloud-ok` = you allow a cloud AI for this token):

```powershell
dynasbrain gateway-token -p test-project --cloud-ok  # prints the token
```

**Internet PC:**

```powershell
Test-NetConnection 192.168.50.2 -Port 8765           # TcpTestSucceeded : True
claude mcp add --transport http --scope user dynasbrain-offline http://192.168.50.2:8765/mcp `
  --header "Authorization: Bearer <token>"
claude -p "Use dynasbrain-offline: list the projects, then explain the main VI."
claude mcp remove dynasbrain-offline                 # when done
```

Without a valid token the gateway answers `401`. Every call is logged on the offline PC in
`%USERPROFILE%\.dynasbrain\audit.jsonl`.

## Step 7: the relay (milestone L2)

With the relay, the engineer asks on the **offline PC's** Ask page and Claude Code on the
internet PC answers. Tokens are issued and revoked automatically.

**Internet PC** (Claude Code installed and signed in): allow the relay port from the
offline PC only, then start the relay.

```powershell
New-NetFirewallRule -DisplayName "DynasBrain relay (cable only)" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8766 `
  -RemoteAddress 192.168.50.2 -InterfaceAlias $nic -Profile Any
dynasbrain relay-key                                  # copy this key
dynasbrain relay --host 192.168.50.1 --gateway http://192.168.50.2:8765
```

**Offline PC** (the gateway from step 6 running):

```powershell
dynasbrain relay-connect http://192.168.50.1:8766 <key>   # checks the relay answers
dynasbrain serve --open                                    # then open Ask
```

On the Ask page, choose the project, tick **Allow sending this project's data to the cloud
AI** (projects are "Local AI only" by default), and ask. **Cancel** stops Claude Code on the
internet PC. To let a project use the cloud without the tick:
`dynasbrain privacy test-project --cloud-allowed`.

To stop using the relay: `dynasbrain relay-connect --off` and restart `dynasbrain serve`.

## Undoing the setup

```powershell
Remove-NetFirewallRule -DisplayName "DynasBrain gateway (cable only)"     # offline PC
Remove-NetFirewallRule -DisplayName "DynasBrain relay (cable only)"       # internet PC
Remove-NetFirewallRule -DisplayName "Ping from internet PC (cable)" -ErrorAction SilentlyContinue
Remove-NetIPAddress -InterfaceAlias $nic -Confirm:$false
```
