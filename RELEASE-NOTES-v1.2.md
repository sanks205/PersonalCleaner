# PersonalCleaner v1.2 — Release Notes

**The honest Windows cleaner, now with a clear Free / Pro split.**

PersonalCleaner is fully open source. No fake scan counts, no scareware, no
network calls. You can read every line.

## What's new in v1.2

- **One unified build.** The same `PersonalCleaner.exe` now ships free on
  GitHub and as the Pro base. No more "free ships everything unlocked" mistake.
- **Free features stay free:** M1–M5 (junk clean, RAM free, startup, close
  stuck apps, restart Explorer), A1 (manual cleanup), I1–I3 (menu, logs, about).
- **Pro features are now locked** until you enter a license key:
  - A2 — Background automation
  - A3 — Weekly idle restart
  - P1 — Defender exclusions
  - P2 — Service tuning
- **L1 menu** — shows your Machine ID and lets you paste a Pro key to unlock.
- Locked items show a 🔒 marker and a hint: "This needs a valid license (Pro)."

## Download

- **Free:** `PersonalCleaner-v1.2.zip` (this release) — or build from source.
- **Pro key ($15/yr/PC):** https://observerly1.gumroad.com/l/ialzp

## How Pro unlock works (offline, no account)

1. Open the app, type **L1** → copy your 16-char Machine ID.
2. Buy the Pro key on Gumroad and send us the Machine ID.
3. We reply with a key like `PC.ABCD1234....2027-08-06.XXXX`.
4. Open the app → **L1** → paste → "License saved and active". Done.

No cloud, no phone-home, no subscription auto-renew. The license is a local
HMAC-signed check tied to your machine.

## Honesty notes

- Not code-signed yet (small indie project). You'll see a one-time SmartScreen
  warning → "More info → Run anyway" is expected and safe.
- Pro licensing is **honor-based**, not DRM. The validation code is in the
  public repo so you can verify it. We'd rather you trust us than fight a lock.
- We make **zero network connections**. Ever.

## Upgrade from v1.1

Just replace your old exe with the v1.2 one. Your settings carry over. If you
bought Pro before, your key still works.

---

Full docs: `README.md`, `USER-GUIDE.txt` (in the zip).
Don't trust your PC cleaner. Verify it.
