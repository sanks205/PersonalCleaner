# 🧹 PersonalCleaner

**The Windows cleaner that doesn't lie to you.**

PersonalCleaner is an honest, open-source Windows cleaner and optimizer. It
shows you what it actually finds and what it's about to change — no fake
"3,000 problems!", no scare tactics, no hidden data collection.

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

**Free forever · Open source (MIT) · No account · No telemetry · No network calls**

[Download from Releases](./releases) · [View Source](./quick_fix.py) ·
[Report an Issue](./issues) · [License](./LICENSE)

**Current release: [v1.2](./releases)** — free build with Pro gating (unlock via `L1`).

---

## Why PersonalCleaner?

You've seen the pattern: *"Your PC has 3,847 problems!"* — a scary number, a
flashing warning, and an upgrade prompt.

But what *is* a "problem"? Most cleaners never tell you. A meaningless count
isn't useful unless you understand what was actually found and what will happen
if you act on it.

PersonalCleaner takes the opposite approach.

### Show the user the evidence.

```
Scan  →  Review  →  Decide  →  Clean
```

Every number you see is a live measurement on your own machine — RAM usage, CPU
load, disk space, frozen apps — and every cleanup is a **preview you approve
before anything is deleted.**

---

## Features

### 🆓 Free (works immediately, no key)

| Feature | What it does | Why you'd care |
|---|---|---|
| 🧊 **Catch frozen apps** | Detects "Not Responding" programs and offers to close them | A hung app freezes your work — close it safely instead of fighting it |
| 🧠 **Free up RAM** | Purges the Windows standby list to reclaim cached memory | Recover cached RAM when memory is high (shows real before/after numbers) |
| 🧹 **Clean junk** | Removes old user temp, Windows temp, WER reports, and empties the Recycle Bin | Frees disk space — only files **older than 24h**, only in known temp folders, skips anything in use |
| 🚀 **Speed up boot** | Enable/disable startup programs by their real names | Fewer apps at boot = faster sign-in (same method Task Manager uses, fully reversible) |
| 🪟 **Close a stuck app** | Mini task manager — see the top memory hogs and close any non-critical app | Lower RAM usage by closing apps you don't need, with a confirmation first |
| 🔄 **Restart Explorer** | Fix a hung taskbar/desktop in one command | Recover from a frozen shell without a full reboot |
| 📊 **Activity log & history** | Timestamped local log of everything the app did | See exactly what happened and when (kept ~7 days) |

### 🔒 Pro (unlocks with a PersonalCleanerPro key)

| Feature | What it does | Why you'd care |
|---|---|---|
| 🌙 **Background automation** | Silent upkeep on idle + daily via Task Scheduler | Runs only the actions you ticked, logs everything, shows a toast |
| 🔁 **Weekly idle restart** | Optional scheduled restart — only when you're away | Clears long-session slowdowns, always with a cancellable warning |
| ⚙️ **Defender exclusions** | Add/remove Microsoft Defender folder & process exclusions | Stop Defender from slowing your dev builds and dev tools |
| 🔧 **Service tuning** | Sets a few noisy background services to Manual/Disabled | Cut background load; originals are captured and restorable |

> **Every feature is opt-in.** A fresh install does nothing on its own — nothing
> is deleted, closed, or scheduled until you switch it on.

---

## 🛒 How Pro works

The same portable app contains all features. Free maintenance (above) works
with no key. The four Pro features are **locked until you enter a license key.**

```
1. Run the app → type L1 → copy your Machine ID (16 characters)
2. Buy PersonalCleanerPro on Gumroad and send us the Machine ID
3. We reply with your key  (e.g. PC.BD831B957C258E78.2027-08-06.XXXX)
4. Open the app → L1 → paste the key → A2/A3/P1/P2 are unlocked
```

- **Pro:** [$15/year per PC](https://observerly1.gumroad.com/l/ialzp) — 1 key, 1 PC,
  100% offline, machine-locked. No subscription games, no cloud, no phone-home.

---

## 🔍 Transparency

- **M1 Scan & fix** measures live CPU/RAM per app and flags genuine problems
  (Not Responding, high memory, high CPU) — with the evidence shown for each one.
- **Junk cleanup runs as a preview first** — "Would free 240 MB" — and only
  deletes after you confirm.
- **Free RAM** reports the actual before/after numbers, and tells you honestly
  when freeing cache won't help (because your RAM is used by real apps, not cache).

---

## 🔐 Privacy & Trust

This is an open-source, local-first tool. The app makes **no network calls at
all** — inspect the source if you don't believe it.

- ✅ Open source (MIT) — read every line of [quick_fix.py](./quick_fix.py)
- ✅ No telemetry — no analytics, no usage collection
- ✅ No account — nothing to sign up for
- ✅ No cloud — no servers, no sync
- ✅ No phone-home — even the Pro license check is fully offline (HMAC-SHA256)
- ✅ Local storage — settings and logs live next to the app (or `%LOCALAPPDATA%`)

> Don't trust our marketing claims. Read the code.

---

## 🛡️ Security & Safety

- **A hardcoded blocklist** of critical OS processes (explorer, lsass, csrss,
  svchost, …) that can **never** be closed.
- **Junk cleanup only touches a hardcoded allowlist** of known temp folders, only
  deletes items **older than 24 hours**, and skips locked/in-use files.
- **A boundary guard** ensures cleanup can never escape its target folder.
- **Every destructive action asks first** — process termination, Explorer
  restart, and file deletion all require a `[y/n]` confirmation.
- **Reversible where it matters** — startup items and service changes are fully
  restorable; scheduled restarts show a warning you can cancel.
- **Local activity log** with 7-day retention.

> Honest caveat: junk file deletion is a one-way delete. That's why it always
> shows you a preview first — what you approve is what gets removed.

---

## 🚫 What PersonalCleaner Doesn't Do

- ❌ No fear-based messaging — no "your PC has thousands of problems!"
- ❌ No meaningless scare numbers — every figure is a real measurement
- ❌ No hidden cleanup — nothing runs or deletes unless you enable it
- ❌ No forced account — there is no account to create
- ❌ No unnecessary telemetry — no data leaves your PC
- ❌ No touching critical system files or processes

> We'd rather show you what we found than scare you into buying something.

---

## 📥 Download & Installation

**Supported:** Windows 10 / 11 · **Type:** portable — no installer.

1. Grab the latest **`PersonalCleaner-vX.Y.zip`** from the [Releases](./releases) page.
2. Extract the ZIP anywhere (a normal folder, not Program Files).
3. Right-click **`PersonalCleaner.exe` → Run as administrator**.
   Admin rights are needed for RAM trim, closing elevated apps, HKLM startup
   items, exclusions, service tuning, and scheduling.
4. A menu opens — type a code (e.g. `M1`) and press Enter.

**First launch:** Windows SmartScreen may warn (see below).

**Menu**

```
MAINTENANCE:   M1 Scan & fix   M2 Free RAM   M3 Startup programs
               M4 Close an app   M5 Restart Explorer
AUTOMATION:    A1 Settings   A2 Background schedule 🔒   A3 Weekly idle restart 🔒
PRO TUNE-UPS:  P1 Antivirus exclusions 🔒   P2 Service tuning 🔒
LICENSE:       L1 License status / enter key
INFO:          I1 Activity log   I2 Run history   I3 About
```

🔒 = requires a PersonalCleanerPro key.

**Update:** download the newest release ZIP and replace the exe — your settings
and log are preserved (they're stored next to the app / in `%LOCALAPPDATA%`).

**Uninstall:** it's portable, so just delete the folder. If you enabled
background tasks, turn off A2 and A3 first to remove the scheduled tasks.

**CLI / power users:** `--auto`, `--dry-run`, `--settings`, `--free-ram`,
`--startup`, `--tasks`, `--restart-explorer`, `--defender`, `--services`,
`--scheduled-restart`, `--install-scheduler`, `--uninstall-scheduler`.
(Pro features require a key even via CLI.)

---

## ⚠️ Windows SmartScreen / Code Signing

The executable is **not code-signed yet.** Because it's unsigned and new,
Windows SmartScreen may show a blue *"Windows protected your PC"* warning the
first time.

**This is expected and normal.** We do **not** recommend blindly bypassing
security. Instead:

1. Verify the download came from **this repository's Releases page.**
2. Optionally skim the source — it's one readable file: [quick_fix.py](./quick_fix.py).
3. Click **More info → Run anyway** on first launch. Once.

> If a signed build matters to you, that's exactly the kind of thing a Pro
> purchase would fund.

---

## 🛡️ Antivirus scan (VirusTotal)

We scan **every release** with [VirusTotal](https://www.virustotal.com) before
publishing — no exceptions.

- **v1.2 (current):** `0 / 67` engines flag it. Clean. ✅
- **Honesty note:** an earlier build once showed `1 / 71` — the single hit was
  **Microsoft Defender**. That's a known false positive for PyInstaller / unsigned
  Python apps (the bundler wraps a legit script; some AV heuristics trip on it).
  It is **not** malware, and later builds came back clean.

Unsigned software always draws extra scrutiny from AV and SmartScreen. That's
exactly what a code-signed build (funded by Pro) removes. Until then: scan the
exe yourself, read the source, and decide.

---

## 🧪 Try to Break PersonalCleaner

We'd rather users find a problem and report it than blindly trust us.

Found a bug? Did it clean something it shouldn't? Close something unsafe? Show a
misleading number? Miss a feature you need? **[Open an issue](./issues)** — include
what you did, what you expected, and what happened.

---

## 🗺️ Roadmap & Ideas

No formal roadmap yet. Ideas we're considering (not commitments):

- **GUI** — a graphical front-end on the same engine
- **Code signing** — remove the SmartScreen warning entirely
- **More cleanup categories** — with the same age/allowlist safeguards
- **Localization** — non-English menu translations

---

## 🤝 Contributing

- **Report a bug / request a feature:** [open an issue](./issues)
- **Contribute code:** fork → make a change → open a pull request

```powershell
# 1. Set up a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run from source to test (licensing.py is included in this repo)
python quick_fix.py

# 4. Build a one-file exe (bundles licensing for gating)
python -m PyInstaller --onefile --name PersonalCleaner --console --icon icon.ico --paths . quick_fix.py
```

---

## 🧑‍💻 Development

- **Language:** Python — `quick_fix.py` is the whole app (one readable file)
- **Runtime dep:** `psutil` (bundled into the exe)
- **Licensing:** `licensing.py` — offline HMAC-SHA256 key validation (no network)
- **Build tool:** PyInstaller
- **Python version:** 3.10+ · **Platform:** Windows 10 / 11

> Note for builders: because `licensing.py` is in the repo, a build from source
> is the same gated build. The signing secret is honour-based — this is not DRM,
> it's a trust barrier (see `licensing.py`).

---

## 📜 License

[MIT](./LICENSE) © 2026 Sanket Thakkar.

This version is MIT — free to use, modify, and share. The PersonalCleanerPro
**key/licensing system** is a separate commercial component on Gumroad. Future
feature releases may ship under a different license; this version remains MIT.

---

## ❤️ Why I Built This

I didn't want to build another application that tells people their computer has
thousands of "problems."

I wanted a Windows maintenance tool that was **useful, transparent, local, and
open source.** One that shows real numbers, never touches critical system files,
and — above all — doesn't lie to you. This is that tool.

---

<div align="center">

## Don't trust your PC cleaner. Verify it.

**Download it. Star it. Try to break it.**

[⬇ Download](./releases) · [⭐ Star](./) · [🐞 Report an Issue](./issues)

*Open source · Windows 10/11 · Local-first · No account · No telemetry*

</div>
