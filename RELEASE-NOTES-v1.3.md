# PersonalCleaner v1.3 — Release Notes

**The honest Windows cleaner, now with a smooth tray experience and fixed scheduler.**

PersonalCleaner is fully open source. No fake scan counts, no scareware, no network calls. You can read every line.

## What's new in v1.3 — UI related changes — tray, window & splash updates

- **Tray, Laragon-like** — Close hides to the system tray (^). Click the tray icon to restore; right-click → Quit. Works on admin and normal runs, and stays after Close → Open → Close.
- **Settings actually save** — "Hide to tray when closed" now persists across restarts (saved to %LOCALAPPDATA%\PersonalCleaner\config.json).
- **Smaller, centered window** — 960×620 instead of 1100×720 fullscreen feel; centered on screen; maximize available.
- **Loading feel** — Splash (460×300) with spinner shows immediately during the 5s PyQt6 unpack — no more blank wait.
- **Scheduler fix** — 10-min idle + daily tasks run silently (headless). No window pops up.

## Download

- **Free:** `PersonalCleaner-v1.3.zip` (this release) — or build from source.
- **Pro key:** https://observerly1.gumroad.com/l/ialzp

## Upgrade from v1.2

Just replace your old exe with the v1.3 one. Your settings carry over.

---

Full docs: `README.md`. Don't trust your PC cleaner. Verify it.
