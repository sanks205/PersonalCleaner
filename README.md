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
   (admin rights are needed to close stuck apps, free RAM, and manage startup items).
3. Pick a menu code (e.g. `M1`) and press Enter.

> First launch shows a Windows SmartScreen prompt because the app isn't code-signed yet —
> click **More info → Run anyway**. See `READ-ME-FIRST.txt` in the download.

## Menu

```
MAINTENANCE:   M1 Scan & fix   M2 Free RAM   M3 Startup programs
AUTOMATION:    A1 Settings     A2 Background schedule   A3 Weekly idle restart
PRO TUNE-UPS:  P1 Antivirus exclusions   P2 Service tuning
INFO:          I1 Activity log   I2 Run history
TRAY:         Minimize to tray (^) — Close hides to system tray, click tray icon to restore
```

Settings and logs are stored next to the executable (portable).

## Build from source

Requires **Python 3.11+** on Windows.

```powershell
# GUI build (v1.3+ — main app, tray + scheduler fix, splash)
python -m pip install -r requirements.txt   # now includes PyQt6
python -m PyInstaller --noconfirm --clean --onefile --name PersonalCleaner --windowed --icon icon.ico --noupx --version-file version_info.txt --add-data "icon.ico;." --add-data "LICENSE;." --paths commercial --hidden-import licensing --collect-submodules PyQt6 --hidden-import PyQt6.QtCore --hidden-import PyQt6.QtWidgets --hidden-import PyQt6.QtGui --hidden-import PyQt6.QtNetwork gui.py
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
