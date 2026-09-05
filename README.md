# PersonalCleaner ⚡

**Honest Windows Optimizer** — a tiny, transparent tool that keeps your Windows PC
fast and clean, and only ever does what **you** switch on.

```
      /     ____                                 _
     //    |  _ \ ___ _ __ ___  ___  _ __   __ _| |
    ///    | |_) / _ \ '__/ __|/ _ \| '_ \ / _` | |
   //////  |  __/  __/ |  \__ \ (_) | | | | (_| | |
    ///    |_|   \___|_|  |___/\___/|_| |_|\__,_|_|
    //       ____ _
    /       / ___| | ___  __ _ _ __   ___ _ __
           | |   | |/ _ \/ _` | '_ \ / _ \ '__|
           | |___| |  __/ (_| | | | |  __/ |
            \____|_|\___|\__,_|_| |_|\___|_|
```

Most "PC cleaners" are bloated, scary, or borderline scams. PersonalCleaner is the
opposite: small, transparent, opt-in, and reversible.

## Features

| | |
|---|---|
| 🧊 **Catch frozen apps** | Detects "Not Responding" programs and offers to close them safely |
| 🧠 **Free up RAM** | Purges the standby list to reclaim cached memory when RAM is high |
| 🧹 **Clean junk** | Removes old temp / Windows Error Reporting files and empties the Recycle Bin (only files older than 24h) |
| 🚀 **Speed up boot** | Enable/disable startup programs by their real names |
| ⚙️ **Pro tune-ups** | Antivirus (Defender) folder/process exclusions for faster dev builds; curated Windows service tuning |
| 🌙 **Background maintenance** | Optional silent upkeep on idle + daily, with a notification and history |
| 🔁 **Weekly idle restart** | Optional scheduled restart — only when you're away, with a cancellable warning |

## Why it's different

- ✅ **Opt-in** — nothing runs or deletes unless you tick it. Fresh install does nothing until you choose.
- ✅ **Safe** — critical Windows processes can never be closed; every action is reversible or cancellable.
- ✅ **Honest** — no fake "errors found!", no bundled junk, full activity log.
- ✅ **100% local** — no telemetry, no account, no network calls. Your data never leaves your PC.

## Download & run

1. Grab the latest **`PersonalCleaner-vX.Y.zip`** from the [Releases](../../releases) page.
2. Unzip, then **right-click `PersonalCleaner.exe` → Run as administrator**
   (admin needed for some actions — see each section below).
3. The window opens — **no CLI codes needed in the GUI.** Use the tabs.

> First launch shows a Windows SmartScreen prompt because the app isn't code-signed yet —
> click **More info → Run anyway**. See `READ-ME-FIRST.txt` in the download.

## Where everything lives (GUI = all 15 CLI codes)

*No codes to memorize in the GUI.* Use the tabs:

| Tab → Section (GUI) | What it does (CLI code) | How to use — terms / what happens |
|---|---|---|
| **Dashboard → Junk cleanup** | **Clean junk — scan/preview** (`M1` junk) | Click **Scan junk** — estimates reclaimable from the 4 categories you ticked in Clean (only temp/WER/Recycle Bin older than your Min age). Shows `Preview: would free X`. Output stays in its own Junk log. Nothing deleted until you click Clean. |
| **Dashboard → Junk cleanup** | **Clean junk — delete** (`M1` junk) | Click **Clean junk now** → deletes the ticked categories. Deleted bytes, skipped/locked count, and `Freed X MB` toast. Logged to `cleaner.log`. |
| **Dashboard → App health** | **Health scan** (`M1` health + `M4` context) | Click **Scan app health** — samples CPU `~1s`, checks every app for `NOT RESPONDING` / `HIGH MEM (≥400 MB)` / `HIGH CPU (≥20%)`, respects `BLOCKLIST` (explorer, lsass, etc. never closed). Lists `Found N problem(s)` with `CAN CLOSE` / reason. To close, go to Optimize → Close a stuck app. |
| **Dashboard → Activity log** | **View log** (`I1`) | **Refresh log file** reloads the last 40 lines from `%LOCALAPPDATA%\PersonalCleaner\cleaner.log` on disk (kept `~7` days, `3000` lines cap). `Clear display` only clears the view. |
| **Dashboard → Background run history** | **History** (`I2`) | Table `When/Disk/RAM/Hung` — `Refresh history` parses every `AUTO: freed X MB disk, Y MB RAM, N hung` line written by silent runs. Each row = one background run. |
| **Clean → Categories** | **Choose what A1 can touch** (`A1` `C1–C4`) | 4 checkboxes: User temp (`%TEMP%`), Windows temp, `WER`, Recycle Bin. Only ticked ones are touched by `--auto` or Clean. Toggle → auto-saves to `config.json`. |
| **Clean → Minimum file age** | **File age** (`A1` `A`) | `Minimum file age (hours):` `QSpinBox` (`0–8760`, default `24h`) → **Save**. Only files older than this are deletable. |
| **Clean → Preview / Clean now** | **Preview + Clean** (`M1` `A1`) | **Preview** — same scan as Dashboard junk, `would free X` toast. **Clean now** — deletes, frees, `Freed X` toast, refreshes `Free RAM` / `Startup items` counts. Output stays inside the Clean card. |
| **Optimize → Free RAM now** | **Purge standby list** (`M2`) | Click **Free RAM now** — purges Windows standby list (cached file data). Safe; needs admin for full effect. Shows `Freed X of RAM. Available now: Y` or `Denied` if not admin. `Available RAM` stat updates. |
| **Optimize → Close a stuck app** | **Task manager** (`M4`) | Table `Program/PID/MEM/Status` — top-20 by RAM, flags `NOT RESPONDING` / `protected`. **Refresh** reloads. Select row → **Close selected app** → confirm `Yes/No` → `terminate → wait 3s → kill`. Cannot close `BLOCKLIST` apps. |
| **Optimize → Restart Explorer** | **Fix taskbar** (`M5`) | Click **Restart Explorer (fix taskbar)** → confirm `Yes/No` → `taskkill /F /IM explorer.exe` + `explorer.exe` after `1s`. Taskbar blinks, File Explorer windows close. Logged. |
| **Startup** | **Startup manager** (`M3`) | Table `Name/Publisher/Status/Impact` — reads `HKCU/HKLM Run` + `StartupApproved` + publisher/impact. **Refresh / Enable / Disable** on selected row. Double-click toggles. Right-click menu. Reversible (same method as Task Manager). |
| **Settings → Appearance** | **Theme** | Dropdown `System / Light / Dark`. **System** = original `SYSTEM` grey `#F3F3F3` (no tint). **Light** = bluish lavender `#EBEFFF`. **Dark** = deep slate `#0F1419`. Persists to `config.json`. |
| **Settings → General** | **Notifications** | Toggle **Show a notification after each cleanup** → Save. Toast after each `Scan`/`Clean`/`Free RAM`. |
| **Settings → General** | **Auto-clean** (`A1` memory/process) | Card **Automatic actions (when A2 schedule runs)**: **`[x] Auto-free RAM when usage ≥ __%`** (`50–99`, default `85%`) + **`[x] Auto-close Not-Responding after __s`** (`5–300s`, default `20s`) + warning about unsaved work. Both `QSpinBox` values. |
| **Settings → General** | **Tray** | Toggle **Hide to tray when closed (runs in background)**. `toggled` live-creates the tray icon → `Close → ^` stays; `Show` restores; `Quit` exits. Persists; on admin vs normal runs the tray is per-session. **Save** commits `tray + notifications + memory/process + min_age`. |
| **Settings → About** | **About** (`I3`) | Shows `Honest Windows Optimizer — vX.Y. Free & open source (MIT).` + when Commercial: `Edition / Machine ID` + `View license` opens `LICENSE`. |
| **Pro → License** | **License** (`L1`) | **Get Machine ID** (copies `16`-char `machine_id`). **Enter license key** + **Activate** → `Licensed — all Pro features unlocked.` In free build buttons disabled with `Commercial features are not available`. |
| **Pro → Background schedule** | **Idle + Daily automation** (`A2`) | Shows `Status: Enabled/Disabled/Not installed`. Fields `Idle (min)` `1–1440` + `Daily time` `HH:MM` + **Install / Uninstall / Refresh** → `PersonalCleaner-Idle` (`ONIDLE`) + `PersonalCleaner-Daily` (`DAILY`). Only does what Clean categories ticked. Toast if nothing active. |
| **Pro → Weekly idle restart** | **Restart when away** (`A3`) | `Restart task: present/absent` + `Day` `SUN–SAT` + `Time` `HH:MM` + `Idle min` `1–1440` + **Enable restart / Disable / Refresh** → weekly `PersonalCleaner-Restart` (`schtasks WEEKLY`); runs only if idle `≥ threshold` with `120s` warning, `shutdown /a` can cancel. Pro-gated. |
| **Pro → Defender exclusions** | **AV exclusions** (`P1`) | Table `Type / Path` — `Defender status` + `Refresh`. **Add exclusion** → dialog `e.g. C:\Projects or code.exe` + type picker `path/process` → `defender_add`. **Remove selected**. Examples shown under title. Needs admin. Pro-gated. |
| **Pro → Service tuning** | **Tune services** (`P2`) | Table `Service / Friendly / Target / Current` — `Refresh` queries `SERVICE_TUNING` (`DiagTrack`, `WSearch`, … `Manual/Disabled`). **Tune selected** → `svc_set` to target. **Restore original** from `config.json services` map. Reversible. Needs admin. Pro-gated. |

Settings and logs are stored at `%LOCALAPPDATA%\PersonalCleaner\config.json` (`LOG_DIR`). Background runs write `cleaner.log`.

CLI equivalents for reference only: `MAINTENANCE: M1 Scan & fix, M2 Free RAM, M3 Startup, M4 Close app, M5 Restart Explorer / AUTOMATION: A1 Settings, A2 Background schedule, A3 Weekly restart / PRO TUNE-UPS: P1, P2 / INFO: I1 Log, I2 History / L1 License, Q Quit, TRAY: Minimize to tray (^)` — same features, now as GUI sections above.

## Build from source

Requires **Python 3.11+** on Windows.

```powershell
# GUI build (v1.3+ — main app, tray + scheduler fix, splash)
python -m pip install -r requirements.txt   # now includes PyQt6
python -m PyInstaller --noconfirm --clean --onefile --name PersonalCleaner --windowed --icon icon.ico --noupx --version-file version_info.txt --add-data "icon.ico;." --add-data "LICENSE;." --paths commercial --hidden-import licensing --hidden-import PyQt6.QtCore --hidden-import PyQt6.QtWidgets --hidden-import PyQt6.QtGui --hidden-import PyQt6.QtNetwork gui.py
```

The unified build ships free + Pro (gated). Pro features unlock with a key via `L1`.
CLI-only build (no GUI): `python -m PyInstaller --onefile --name PersonalCleaner --console --icon icon.ico --noupx --version-file version_info.txt --exclude-module licensing quick_fix.py`.
The executable is produced at `dist\PersonalCleaner.exe`. Main source: `gui.py` + `quick_fix.py`.

## Safety model

- **Blocklist** of critical OS processes (explorer, lsass, csrss, …) that can *never* be touched.
- Junk cleanup only deletes files **older than 24 hours** and skips anything in use.
- Startup / service changes and scheduled restarts are all **reversible**.
- Everything is written to a local activity log (kept ~7 days).

## Support

PersonalCleaner is free and open-source. If it's useful to you, you can support
development on **[Gumroad](https://observerly1.gumroad.com/l/ialzp)** (pay what you want, or grab it free). ☕

## License

[MIT](LICENSE) © 2026 Sanket Thakkar.
Future feature releases may ship under a different license; this version remains MIT.

## Disclaimer

Provided "as is", without warranty. You are responsible for how you use it. Closing a
frozen application or restarting can lose unsaved work — the tool always asks first, but
use your judgement.
