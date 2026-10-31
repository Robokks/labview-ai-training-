# 4. Sandbox on the offline PC

When the AI creates VIs or runs scripts, it does so **only on the offline PC**, inside
layered limits.

## Why not Windows Sandbox?

Windows Sandbox (a throwaway virtual machine) is available on Windows 10 Pro. It is
**not practical here**: LabVIEW, its licence, drivers and NI hardware do not run inside it
easily, and it is wiped on every close. So the sandbox is built from several layers on the
normal Windows installation.

## The layers

| # | Layer | Rule |
|---|---|---|
| 1 | **Workspace folder** | The AI can write only inside `D:\AI-Workspace\` (configurable). Real project folders are read-only, through DynasBrain's tools. |
| 2 | **Snapshot before every change** | The gateway makes a git commit of the workspace before every write, so any change can be undone with `git` or a "Revert" button. |
| 3 | **Approval** | Every create, edit or run shows **Allow / Deny** on the offline PC, with the tool name and its inputs. Reads (search, describe) run without asking. No answer in 2 minutes means Deny. |
| 4 | **Restricted runner** | No free-form shell. Only PowerShell (`.ps1`) and Python (`.py`) scripts saved in the workspace, run with the workspace as the working folder and a time limit (default 5 minutes). |
| 5 | **Limited Windows user** | Scripts run as a limited local account (e.g. `ai-runner`) that can write only to the workspace and cannot change system settings. |
| 6 | **No network** | The offline PC has no internet route, so a script cannot send data out. |

## Setting up the limited user (Windows 10 Pro)

> These steps are for when milestone L4 is built. They change Windows accounts and
> permissions, so do them with IT.

Run in an **administrator** PowerShell on the offline PC:

```powershell
# 1. Create the limited account (you will be asked for a password)
$pw = Read-Host -AsSecureString "Password for ai-runner"
New-LocalUser -Name "ai-runner" -Password $pw -Description "Runs AI-created scripts" -AccountNeverExpires
# It is a standard user by default: do NOT add it to Administrators.

# 2. Create the workspace and give ai-runner Modify rights on it only
New-Item -ItemType Directory -Force "D:\AI-Workspace" | Out-Null
icacls "D:\AI-Workspace" /grant "ai-runner:(OI)(CI)M"

# 3. Initialise the snapshot history
git -C "D:\AI-Workspace" init
```

Other folders already deny writes to a standard user by default (Windows, Program
Files, other users' profiles). Check that your project drives, e.g. `D:\LabVIEW\`, do not
grant write access to "Users" or "Everyone": `icacls "D:\LabVIEW"`.

## LabVIEW-generated VIs

VIs created through labview-mcp are written by **LabVIEW itself**, which runs as the normal
user. Layers 1–3 apply to them: the gateway only passes workspace paths to labview-mcp, takes
a snapshot first, and asks for approval. Layer 5 applies to PowerShell and Python scripts.

## Recovering from a bad change

```powershell
git -C "D:\AI-Workspace" log --oneline        # list snapshots
git -C "D:\AI-Workspace" checkout <id> -- .   # restore the workspace to a snapshot
```
