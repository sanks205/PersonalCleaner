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
| 🪟 **Close a stuck app** | Mini task manager — see top memory hogs and close any non-critical app |
| 🔄 **Restart Explorer** | Fix a hung taskbar / desktop in one command |
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
               M4 Close an app   M5 Restart Explorer
AUTOMATION:    A1 Settings     A2 Background schedule   A3 Weekly idle restart
PRO TUNE-UPS:  P1 Antivirus exclusions   P2 Service tuning
INFO:          I1 Activity log   I2 Run history   I3 About
```

Settings and logs are stored next to the executable (portable).

## Build from source

Requires **Python 3.11+** on Windows.

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --onefile --name PersonalCleaner --console --icon icon.ico quick_fix.py
```

The executable is produced at `dist\PersonalCleaner.exe`. Main source: `quick_fix.py`.

## Safety model

- **Blocklist** of critical OS processes (explorer, lsass, csrss, …) that can *never* be touched.
- Junk cleanup only deletes files **older than 24 hours** and skips anything in use.
- Startup / service changes and scheduled restarts are all **reversible**.
- Everything is written to a local activity log (kept ~7 days).

## Support

PersonalCleaner is free and open-source. If it's useful to you, a paid
**Pro version** (background automation, weekly idle restart, Defender
exclusions and service tuning) is available on **[Gumroad](https://observerly1.gumroad.com/l/ialzp)**. ☕

## License

[MIT](LICENSE) © 2026 Sanket Thakkar.
Future feature releases may ship under a different license; this version remains MIT.

## Disclaimer

Provided "as is", without warranty. You are responsible for how you use it. Closing a
frozen application or restarting can lose unsaved work — the tool always asks first, but
use your judgement.
