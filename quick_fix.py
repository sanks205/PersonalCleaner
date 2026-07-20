"""
quick_fix.py — Windows application-health + junk-cleanup optimizer.

MODES (selected by command-line flag; double-clicking opens the main menu):

  (no flag)             Main menu (all features).
  --settings            Open the settings screen directly.
  --free-ram            Purge the standby list to free cached RAM.
  --startup             Open the startup-programs manager.
  --dry-run             Scan + preview cleanup (deletes nothing).
  --auto                Silent background run for the scheduler: does only the
                        actions enabled in config, logs everything, no prompts,
                        no window. Run windowless by Task Scheduler.
  --scheduled-restart   Task action: restart only if enabled and user is idle.
  --install-scheduler   Register the on-idle + daily background tasks.
  --uninstall-scheduler Remove those scheduled tasks.

SAFETY
  * Junk cleanup only touches a hardcoded allowlist of known-temp folders,
    only deletes items older than MIN_AGE_HOURS, skips locked/in-use files,
    and can never escape the target folder.
  * Process termination only happens in interactive mode, always behind a
    [y/n] confirmation, never for BLOCKLIST processes.
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timedelta

try:
    import psutil
except ImportError:
    print("[FATAL] The 'psutil' package is not installed.  Run: pip install psutil")
    time.sleep(5)
    sys.exit(1)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# --- Junk cleanup ----------------------------------------------------------- #

# Only delete items whose most-recent modification is older than this many
# hours. Protects files an application is actively using right now.
MIN_AGE_HOURS = 24

# --- Per-application health thresholds -------------------------------------- #

HEAVY_MEM_MB = 400          # flag HIGH MEMORY at/above this RSS (MB)
CPU_BUSY_PCT = 20.0         # flag HIGH CPU at/above this normalized %
CPU_SAMPLE_SECONDS = 1.0    # CPU sampling window
KILL_HUNG = True            # hung, non-blocklisted apps eligible to close
CONFIRM_BEFORE_KILL = True  # ask [y/n] before every termination

# --- System context (informational only) ----------------------------------- #

PRESSURE_PERCENT = 80.0
NEAR_LIMIT_RATIO = 0.75
TOP_PROCESS_COUNT = 8
FINAL_PAUSE_SECONDS = 5

# --- Scheduler defaults ----------------------------------------------------- #

TASK_PREFIX = "PersonalCleaner"
DEFAULT_IDLE_MINUTES = 10
DEFAULT_DAILY_TIME = "03:00"

APP_NAME = "PersonalCleaner"
APP_TAGLINE = "Honest Windows Optimizer"
APP_VERSION = "1.0"

# ASCII-art logo (figlet "standard" font), stacked Personal / Cleaner.
BANNER = [
    ' ____                                 _',
    '|  _ \\ ___ _ __ ___  ___  _ __   __ _| |',
    "| |_) / _ \\ '__/ __|/ _ \\| '_ \\ / _` | |",
    '|  __/  __/ |  \\__ \\ (_) | | | | (_| | |',
    '|_|   \\___|_|  |___/\\___/|_| |_|\\__,_|_|',
    '',
    '  ____ _',
    ' / ___| | ___  __ _ _ __   ___ _ __',
    "| |   | |/ _ \\/ _` | '_ \\ / _ \\ '__|",
    '| |___| |  __/ (_| | | | |  __/ |',
    ' \\____|_|\\___|\\__,_|_| |_|\\___|_|',
]

# Lightning-bolt emblem (our icon) shown to the left of the logo.
# Tapered: thin tips -> thick kink (row 5, between Personal / Cleaner) -> thin.
EMBLEM = [
    '',
    '',
    '     /',
    '    //',
    '   ///',
    '  //////',
    '    ///',
    '    //',
    '    /',
    '',
    '',
]

# --- Logging ---------------------------------------------------------------- #

# Store settings/log in a FIXED, WRITABLE location so they persist regardless of
# how the app is launched (elevated or not, any account). Prefer beside the exe
# (portable); if that folder is read-only (e.g. exe in Program Files), fall back
# to %LOCALAPPDATA% then the home folder.
def _pick_data_dir() -> str:
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.dirname(sys.executable))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(os.path.join(local, "PersonalCleaner"))
    candidates.append(os.path.join(os.path.expanduser("~"), "PersonalCleaner"))
    candidates.append(os.getcwd())
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".pc_write_test")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("ok")
            os.remove(probe)
            return d
        except OSError:
            continue
    return os.getcwd()


LOG_DIR = _pick_data_dir()
LOG_FILE = os.path.join(LOG_DIR, "cleaner.log")
CONFIG_FILE = os.path.join(LOG_DIR, "config.json")
LOG_RETENTION_DAYS = 7   # keep ~1 week of activity in the log
MAX_LOG_LINES = 3000     # hard safety cap regardless of dates

# The cleanup categories the user can tick. Order = display order.
CLEANUP_CATEGORIES = [
    ("user_temp",    "User temp        (%TEMP%, LOCALAPPDATA\\Temp)"),
    ("windows_temp", "Windows temp     (C:\\Windows\\Temp)"),
    ("wer",          "Windows Error Reporting (WER)"),
    ("recycle_bin",  "Recycle Bin"),
]

# Safe default: EVERYTHING unchecked. The background agent cleans nothing until
# the user explicitly ticks categories in --settings.
DEFAULT_CONFIG = {
    "cleanup": {key: False for key, _ in CLEANUP_CATEGORIES},
    "min_age_hours": MIN_AGE_HOURS,
    "memory": {
        "trim_on_pressure": False,   # opt-in: purge standby list in --auto
        "pressure_percent": 85,      # ...when RAM usage reaches this %
        "purge_standby": True,       # the safe trim (cached file data)
        "empty_working_sets": False, # aggressive (config-file only); can slow apps
    },
    "process": {
        "auto_close_hung": False,    # opt-in: close Not-Responding apps in --auto
        "hung_grace_seconds": 20,    # must still be hung after this delay
    },
    "restart": {
        "enabled": False,            # opt-in: weekly restart when idle
        "day": "SUN",                # schtasks day code (SUN..SAT)
        "time": "04:00",             # 24h HH:MM
        "idle_minutes": 60,          # only restart after this much user idle
        "warn_seconds": 120,         # warning countdown before restart
    },
    "notifications": True,           # show a toast after each background run
    "services": {},                  # original start modes captured before tuning
}

# Curated, well-known-safe services to defer. (service, friendly, why, target)
# target: "manual" (start on demand) or "disabled". Only ones that EXIST are shown.
SERVICE_TUNING = [
    ("DiagTrack", "Connected User Experiences & Telemetry",
     "Microsoft usage/diagnostics telemetry", "disabled"),
    ("dmwappushservice", "WAP Push Routing (telemetry)",
     "Device-management telemetry", "disabled"),
    ("RemoteRegistry", "Remote Registry",
     "Lets others edit your registry remotely (safer off)", "disabled"),
    ("RetailDemo", "Retail Demo Service",
     "Store demo mode - not needed at home", "disabled"),
    ("SysMain", "SysMain (Superfetch)",
     "Preloads apps into RAM; often unneeded on SSDs", "manual"),
    ("WSearch", "Windows Search (indexing)",
     "Background file indexing", "manual"),
    ("Fax", "Fax", "Fax service (rarely used)", "manual"),
    ("MapsBroker", "Downloaded Maps Manager",
     "Offline maps updates", "manual"),
    ("WMPNetworkSvc", "WMP Network Sharing",
     "Media streaming to other devices", "manual"),
    ("lfsvc", "Geolocation Service", "Tracks device location", "manual"),
    ("XblAuthManager", "Xbox Live Auth Manager",
     "Xbox sign-in (only for gaming)", "manual"),
    ("XblGameSave", "Xbox Live Game Save",
     "Xbox cloud saves (only for gaming)", "manual"),
    ("XboxNetApiSvc", "Xbox Live Networking",
     "Xbox networking (only for gaming)", "manual"),
]

# --- Safety lists ----------------------------------------------------------- #

BLOCKLIST = {
    "explorer.exe", "svchost.exe", "lsass.exe", "services.exe", "wininit.exe",
    "csrss.exe", "spoolsv.exe", "taskhostw.exe", "smss.exe", "winlogon.exe",
    "dwm.exe", "system", "registry", "fontdrvhost.exe",
}
ALLOWLIST = {
    "chrome.exe", "msedge.exe", "node.exe", "slack.exe", "teams.exe",
    "discord.exe",
}
IGNORE_NAMES = {"system idle process"}
IGNORE_PIDS = {0}

# Set True while running interactively (controls the final "press Enter" wait).
INTERACTIVE = False
# The menu manages its own pauses, so it disables the single final wait.
_FINAL_WAIT = True


# --------------------------------------------------------------------------- #
# Colour + logging
# --------------------------------------------------------------------------- #

RED = YELLOW = GREEN = RESET = BOLD = CYAN = ""


def _enable_ansi() -> bool:
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:  # noqa: BLE001
        return False


def _init_colors() -> None:
    global RED, YELLOW, GREEN, RESET, BOLD, CYAN
    if _enable_ansi():
        RED, YELLOW, GREEN, RESET = "\033[91m", "\033[93m", "\033[92m", "\033[0m"
        BOLD, CYAN = "\033[1m", "\033[96m"


def _color(text: str, color: str) -> str:
    return f"{color}{text}{RESET}" if color else text


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


_LOG_TS_RE = re.compile(r"^\[(\d{4})-(\d{2})-(\d{2}) ")


def _rotate_log() -> None:
    """
    Keep only the last LOG_RETENTION_DAYS of entries (by their timestamp),
    with MAX_LOG_LINES as a hard safety cap. Continuation lines (no timestamp)
    stay with their parent entry. Rewrites only if something was dropped.
    """
    try:
        if not os.path.exists(LOG_FILE):
            return
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        if not lines:
            return
        cutoff = (datetime.now() - timedelta(days=LOG_RETENTION_DAYS)).date()
        kept, keep_current = [], True
        for ln in lines:
            m = _LOG_TS_RE.match(ln)
            if m:
                try:
                    d = datetime(int(m[1]), int(m[2]), int(m[3])).date()
                    keep_current = d >= cutoff
                except ValueError:
                    keep_current = True
            if keep_current:
                kept.append(ln)
        if len(kept) > MAX_LOG_LINES:
            kept = kept[-MAX_LOG_LINES:]
        if len(kept) != len(lines):
            with open(LOG_FILE, "w", encoding="utf-8") as fh:
                fh.writelines(kept)
    except OSError:
        pass


def log(msg: str, to_console: bool = True) -> None:
    """Append a timestamped line to the log file (and optionally the console)."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean = _ANSI_RE.sub("", msg)  # never store colour codes in the log file
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"[{stamp}] {clean}\n")
    except OSError:
        pass
    if to_console:
        print(msg)


def _register_aumid() -> None:
    """Register an AppUserModelID so toasts show under a friendly name."""
    try:
        import winreg
        key = r"Software\Classes\AppUserModelId\PersonalCleaner.App"
        k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, "Personal Cleaner")
        winreg.CloseKey(k)
    except OSError:
        pass


def show_toast(title: str, message: str) -> bool:
    """Show a Windows toast notification. Returns True if it was dispatched."""
    try:
        import subprocess

        def esc(s: str) -> str:
            return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    .replace("'", "&apos;").replace('"', "&quot;"))

        _register_aumid()
        xml = ("<toast><visual><binding template=\"ToastGeneric\">"
               f"<text>{esc(title)}</text><text>{esc(message)}</text>"
               "</binding></visual></toast>")
        ps = (
            "$ErrorActionPreference='SilentlyContinue';"
            "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]>$null;"
            "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom,ContentType=WindowsRuntime]>$null;"
            f"$x=[Windows.Data.Xml.Dom.XmlDocument]::new();$x.LoadXml('{xml}');"
            "$t=[Windows.UI.Notifications.ToastNotification]::new($x);"
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('PersonalCleaner.App').Show($t);"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
             "-Command", ps],
            capture_output=True, text=True, creationflags=0x08000000)  # CREATE_NO_WINDOW
        return res.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _mb(num_bytes: float) -> float:
    return num_bytes / (1024 * 1024)


def _gb(num_bytes: float) -> float:
    return num_bytes / (1024 ** 3)


# --------------------------------------------------------------------------- #
# Junk cleanup
# --------------------------------------------------------------------------- #

def load_config() -> dict:
    """Load settings, merged over defaults. Missing/corrupt file -> defaults."""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
    except (OSError, ValueError):
        return cfg
    if isinstance(saved.get("cleanup"), dict):
        for key in cfg["cleanup"]:
            if key in saved["cleanup"]:
                cfg["cleanup"][key] = bool(saved["cleanup"][key])
    if isinstance(saved.get("min_age_hours"), (int, float)):
        cfg["min_age_hours"] = saved["min_age_hours"]
    if isinstance(saved.get("memory"), dict):
        for key in cfg["memory"]:
            if key in saved["memory"]:
                cfg["memory"][key] = saved["memory"][key]
    if isinstance(saved.get("process"), dict):
        for key in cfg["process"]:
            if key in saved["process"]:
                cfg["process"][key] = saved["process"][key]
    if isinstance(saved.get("restart"), dict):
        for key in cfg["restart"]:
            if key in saved["restart"]:
                cfg["restart"][key] = saved["restart"][key]
    if isinstance(saved.get("notifications"), bool):
        cfg["notifications"] = saved["notifications"]
    if isinstance(saved.get("services"), dict):
        cfg["services"] = {str(k): str(v) for k, v in saved["services"].items()}
    return cfg


def save_config(cfg: dict) -> bool:
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
        return True
    except OSError:
        return False


def _category_paths() -> dict:
    """Map each folder-based category to the existing directories it covers."""
    env = os.environ
    raw = {
        "user_temp": [env.get("TEMP"), env.get("TMP"),
                      os.path.join(env.get("LOCALAPPDATA", ""), "Temp")],
        "windows_temp": [os.path.join(env.get("WINDIR", r"C:\Windows"), "Temp")],
        "wer": [os.path.join(env.get("PROGRAMDATA", ""),
                             "Microsoft", "Windows", "WER", "ReportQueue"),
                os.path.join(env.get("PROGRAMDATA", ""),
                             "Microsoft", "Windows", "WER", "ReportArchive")],
    }
    out = {}
    for key, paths in raw.items():
        seen, dirs = set(), []
        for p in paths:
            if not p:
                continue
            ap = os.path.abspath(p)
            if ap.lower() in seen or not os.path.isdir(ap):
                continue
            seen.add(ap.lower())
            dirs.append(ap)
        out[key] = dirs
    return out


def estimate_category(key: str, min_age: float) -> int:
    """Bytes that cleaning this category would free right now (dry-run walk)."""
    if key == "recycle_bin":
        return recycle_bin_size()
    total = 0
    for base in _category_paths().get(key, []):
        _, freed, _ = clean_location(base, True, min_age)
        total += freed
    return total


def _age_hours(path: str) -> float:
    try:
        return (time.time() - os.path.getmtime(path)) / 3600.0
    except OSError:
        return 0.0


def _tree_size(path: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def clean_location(base: str, dry_run: bool, min_age: float) -> tuple:
    """Clean one folder. Returns (items_removed, bytes_freed, errors)."""
    removed = errors = 0
    freed = 0
    base = os.path.abspath(base)
    try:
        entries = os.listdir(base)
    except OSError:
        return 0, 0, 1

    for name in entries:
        path = os.path.join(base, name)
        # Boundary guard: never act outside the target folder.
        if not os.path.abspath(path).startswith(base + os.sep):
            continue
        try:
            if _age_hours(path) < min_age:
                continue
            if os.path.isdir(path) and not os.path.islink(path):
                size = _tree_size(path)
                if not dry_run:
                    shutil.rmtree(path, ignore_errors=True)
                removed += 1
                freed += size
            else:
                size = os.path.getsize(path) if os.path.isfile(path) else 0
                if not dry_run:
                    os.remove(path)
                removed += 1
                freed += size
        except (PermissionError, OSError):
            errors += 1  # locked / in use -> skip
            continue
    return removed, freed, errors


def recycle_bin_size() -> int:
    try:
        import ctypes
        from ctypes import wintypes

        class SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD),
                        ("i64Size", ctypes.c_int64),
                        ("i64NumItems", ctypes.c_int64)]

        info = SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
        if ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info)) == 0:
            return int(info.i64Size)
    except Exception:  # noqa: BLE001
        pass
    return 0


def empty_recycle_bin(dry_run: bool) -> int:
    """Empty the Recycle Bin. Returns bytes that were freed (best effort)."""
    size = recycle_bin_size()
    if dry_run or size == 0:
        return size
    try:
        import ctypes
        # NOCONFIRMATION | NOPROGRESSUI | NOSOUND
        flags = 0x1 | 0x2 | 0x4
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
    except Exception:  # noqa: BLE001
        return 0
    return size


def run_cleanup(dry_run: bool, cfg: dict) -> int:
    """Clean only the categories enabled in cfg. Returns total bytes freed."""
    enabled = cfg.get("cleanup", {})
    min_age = cfg.get("min_age_hours", MIN_AGE_HOURS)
    verb = "Would free" if dry_run else "Freed"
    label_map = dict(CLEANUP_CATEGORIES)
    total_bytes = total_items = total_errors = 0

    active = [key for key, _ in CLEANUP_CATEGORIES if enabled.get(key)]
    log(f"  {'JUNK CLEANUP (preview)' if dry_run else 'JUNK CLEANUP'}"
        f"  (age > {min_age:g}h)", to_console=INTERACTIVE)
    if not active:
        log("    (no categories enabled - nothing to clean)", to_console=INTERACTIVE)
        return 0

    paths = _category_paths()
    for key in active:
        if key == "recycle_bin":
            rb = empty_recycle_bin(dry_run)
            total_bytes += rb
            log(f"    {label_map[key]}\n      {verb} {_mb(rb):.1f} MB",
                to_console=INTERACTIVE)
            continue
        cat_removed = cat_freed = cat_err = 0
        for base in paths.get(key, []):
            removed, freed, errors = clean_location(base, dry_run, min_age)
            cat_removed += removed
            cat_freed += freed
            cat_err += errors
        total_items += cat_removed
        total_bytes += cat_freed
        total_errors += cat_err
        note = f" ({cat_err} skipped/locked)" if cat_err else ""
        log(f"    {label_map[key]}\n      {verb} {_mb(cat_freed):.1f} MB "
            f"in {cat_removed} item(s){note}", to_console=INTERACTIVE)

    log(f"  {'Would free' if dry_run else 'Freed'} a total of "
        f"{_color(f'{_mb(total_bytes):.1f} MB', GREEN)} "
        f"across {total_items} item(s), {total_errors} skipped.",
        to_console=INTERACTIVE)
    return total_bytes


# --------------------------------------------------------------------------- #
# Memory trim (purge the standby list — frees cached RAM). Needs admin.
# --------------------------------------------------------------------------- #

_SYSTEM_MEMORY_LIST_INFORMATION = 0x50
_MEMORY_EMPTY_WORKING_SETS = 2
_MEMORY_PURGE_STANDBY_LIST = 4
_STATUS_PRIVILEGE_NOT_HELD = 0xC0000061


def _enable_privilege(priv_name: str) -> bool:
    """Enable a named privilege on the current process token."""
    try:
        import ctypes
        from ctypes import wintypes

        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        TOKEN_ADJUST_PRIVILEGES, TOKEN_QUERY = 0x0020, 0x0008
        SE_PRIVILEGE_ENABLED = 0x00000002

        class LUID(ctypes.Structure):
            _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

        class LUID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

        class TOKEN_PRIVILEGES(ctypes.Structure):
            _fields_ = [("PrivilegeCount", wintypes.DWORD),
                        ("Privileges", LUID_AND_ATTRIBUTES * 1)]

        # Declare prototypes so 64-bit HANDLEs are not truncated to 32 bits.
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        advapi32.OpenProcessToken.restype = wintypes.BOOL
        advapi32.OpenProcessToken.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        advapi32.LookupPrivilegeValueW.restype = wintypes.BOOL
        advapi32.LookupPrivilegeValueW.argtypes = [
            wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(LUID)]
        advapi32.AdjustTokenPrivileges.restype = wintypes.BOOL
        advapi32.AdjustTokenPrivileges.argtypes = [
            wintypes.HANDLE, wintypes.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES),
            wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p]

        h = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                         TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                         ctypes.byref(h)):
            return False
        luid = LUID()
        if not advapi32.LookupPrivilegeValueW(None, priv_name, ctypes.byref(luid)):
            kernel32.CloseHandle(h)
            return False
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
        ok = advapi32.AdjustTokenPrivileges(h, False, ctypes.byref(tp), 0, None, None)
        err = ctypes.get_last_error()
        kernel32.CloseHandle(h)
        return bool(ok) and err == 0  # err 1300 = ERROR_NOT_ALL_ASSIGNED
    except Exception:  # noqa: BLE001
        return False


def _set_memory_list(command: int) -> int:
    """Call NtSetSystemInformation(SystemMemoryListInformation). Returns NTSTATUS."""
    import ctypes
    ntdll = ctypes.windll.ntdll
    ntdll.NtSetSystemInformation.restype = ctypes.c_ulong
    ntdll.NtSetSystemInformation.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                             ctypes.c_ulong]
    cmd = ctypes.c_int(command)
    return ntdll.NtSetSystemInformation(_SYSTEM_MEMORY_LIST_INFORMATION,
                                        ctypes.byref(cmd), ctypes.sizeof(cmd))


def memory_trim(purge_standby: bool = True, empty_working_sets: bool = False) -> dict:
    """
    Free cached RAM. Returns dict with before/after available bytes, freed,
    and flags ok / denied (needs admin).
    """
    res = {"before": 0, "after": 0, "freed": 0, "ok": False, "denied": False,
           "actions": []}
    try:
        import ctypes  # noqa: F401
    except Exception:  # noqa: BLE001
        return res

    res["before"] = psutil.virtual_memory().available
    _enable_privilege("SeProfileSingleProcessPrivilege")
    _enable_privilege("SeIncreaseQuotaPrivilege")

    def _do(cmd, label):
        try:
            status = _set_memory_list(cmd)
        except Exception:  # noqa: BLE001
            return
        if status == 0:
            res["ok"] = True
            res["actions"].append(label)
        elif status == _STATUS_PRIVILEGE_NOT_HELD:
            res["denied"] = True

    if empty_working_sets:
        _do(_MEMORY_EMPTY_WORKING_SETS, "working sets")
    if purge_standby:
        _do(_MEMORY_PURGE_STANDBY_LIST, "standby list")

    res["after"] = psutil.virtual_memory().available
    res["freed"] = max(0, res["after"] - res["before"])
    return res


# --------------------------------------------------------------------------- #
# Startup programs (Run keys + Startup folders). Reversible enable/disable via
# the StartupApproved keys — exactly how Task Manager does it.
# --------------------------------------------------------------------------- #

_RUN_SUB = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APPROVED_RUN = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
_APPROVED_RUN32 = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32"
_APPROVED_FOLDER = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder"


def _is_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def _exe_from_command(command: str) -> str:
    """Extract the executable path from a Run command line."""
    cmd = (command or "").strip()
    if not cmd:
        return ""
    if cmd[0] == '"':
        end = cmd.find('"', 1)
        path = cmd[1:end] if end != -1 else cmd[1:]
    else:
        path = cmd.split(" ")[0]
    return os.path.expandvars(path)


def _file_description(path: str) -> str:
    """Return an exe's FileDescription/ProductName from its version resource."""
    try:
        import ctypes
        from ctypes import wintypes
        if not path or not os.path.isfile(path):
            return ""
        ver = ctypes.windll.version
        ver.GetFileVersionInfoSizeW.restype = wintypes.DWORD
        ver.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR,
                                                ctypes.POINTER(wintypes.DWORD)]
        ver.GetFileVersionInfoW.restype = wintypes.BOOL
        ver.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                                            wintypes.DWORD, ctypes.c_void_p]
        ver.VerQueryValueW.restype = wintypes.BOOL
        ver.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR,
                                       ctypes.POINTER(ctypes.c_void_p),
                                       ctypes.POINTER(wintypes.UINT)]

        size = ver.GetFileVersionInfoSizeW(path, None)
        if not size:
            return ""
        buf = ctypes.create_string_buffer(size)
        if not ver.GetFileVersionInfoW(path, 0, size, buf):
            return ""

        ptr = ctypes.c_void_p()
        ulen = wintypes.UINT()
        if not ver.VerQueryValueW(buf, r"\VarFileInfo\Translation",
                                  ctypes.byref(ptr), ctypes.byref(ulen)) or not ulen.value:
            return ""
        lang, codepage = ctypes.cast(
            ptr, ctypes.POINTER(wintypes.WORD * 2)).contents[:]
        for field in ("FileDescription", "ProductName"):
            sub = "\\StringFileInfo\\%04x%04x\\%s" % (lang, codepage, field)
            vptr = ctypes.c_void_p()
            vlen = wintypes.UINT()
            if ver.VerQueryValueW(buf, sub, ctypes.byref(vptr),
                                  ctypes.byref(vlen)) and vlen.value:
                s = ctypes.wstring_at(vptr, vlen.value).strip("\x00").strip()
                if s:
                    return s
        return ""
    except Exception:  # noqa: BLE001
        return ""


def _friendly_name(command: str, fallback: str) -> str:
    """Human-readable app name for a Run command; fallback if unavailable."""
    exe = _exe_from_command(command)
    base = os.path.basename(exe).lower()
    # These launchers say nothing useful about the real app -> keep raw name.
    if base in ("rundll32.exe", "regsvr32.exe", "cmd.exe", "mshta.exe",
                "powershell.exe", "conhost.exe", "wscript.exe", "cscript.exe"):
        return fallback
    desc = _file_description(exe)
    return desc if desc else fallback


def _approved_enabled(hive, subkey: str, value_name: str, wow: int) -> bool:
    """Read StartupApproved state. Absent value => enabled. Byte0==3 => disabled."""
    import winreg
    try:
        k = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ | wow)
        try:
            data, _ = winreg.QueryValueEx(k, value_name)
        finally:
            winreg.CloseKey(k)
        if isinstance(data, (bytes, bytearray)) and len(data) >= 1 and data[0] == 3:
            return False
    except OSError:
        pass
    return True


def _read_run(hive, source: str, approved_subkey: str, wow: int) -> list:
    import winreg
    out = []
    try:
        k = winreg.OpenKey(hive, _RUN_SUB, 0, winreg.KEY_READ | wow)
    except OSError:
        return out
    idx = 0
    while True:
        try:
            name, val, _ = winreg.EnumValue(k, idx)
        except OSError:
            break
        idx += 1
        out.append({
            "name": name, "display": _friendly_name(str(val), name),
            "command": str(val), "source": source,
            "hive": hive, "approved_subkey": approved_subkey, "approved_wow": 0,
            "enabled": _approved_enabled(hive, approved_subkey, name, 0),
        })
    winreg.CloseKey(k)
    return out


def _read_startup_folder(path: str, hive, source: str) -> list:
    out = []
    if not path or not os.path.isdir(path):
        return out
    for fn in os.listdir(path):
        if fn.lower() in ("desktop.ini",) or fn.lower().endswith(".ini"):
            continue
        full = os.path.join(path, fn)
        if not os.path.isfile(full):
            continue
        out.append({
            "name": fn, "display": os.path.splitext(fn)[0], "command": full,
            "source": source, "hive": hive, "approved_subkey": _APPROVED_FOLDER,
            "approved_wow": 0,
            "enabled": _approved_enabled(hive, _APPROVED_FOLDER, fn, 0),
        })
    return out


def enumerate_startup() -> list:
    """List startup programs across Run keys and Startup folders."""
    import winreg
    env = os.environ
    items = []
    items += _read_run(winreg.HKEY_CURRENT_USER, "HKCU-Run", _APPROVED_RUN, 0)
    items += _read_run(winreg.HKEY_LOCAL_MACHINE, "HKLM-Run", _APPROVED_RUN, 0)
    items += _read_run(winreg.HKEY_LOCAL_MACHINE, "HKLM-Run32", _APPROVED_RUN32,
                       winreg.KEY_WOW64_32KEY)
    user_startup = os.path.join(env.get("APPDATA", ""),
                                r"Microsoft\Windows\Start Menu\Programs\Startup")
    common_startup = os.path.join(env.get("PROGRAMDATA", ""),
                                  r"Microsoft\Windows\Start Menu\Programs\Startup")
    items += _read_startup_folder(user_startup, winreg.HKEY_CURRENT_USER, "Startup-User")
    items += _read_startup_folder(common_startup, winreg.HKEY_LOCAL_MACHINE, "Startup-Common")
    return items


def set_startup_enabled(item: dict, enabled: bool) -> bool:
    """Enable/disable a startup item via StartupApproved. Returns success."""
    import winreg
    try:
        k = winreg.CreateKeyEx(item["hive"], item["approved_subkey"], 0,
                               winreg.KEY_SET_VALUE | item["approved_wow"])
        data = bytes([2 if enabled else 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        try:
            winreg.SetValueEx(k, item["name"], 0, winreg.REG_BINARY, data)
        finally:
            winreg.CloseKey(k)
        return True
    except (PermissionError, OSError):
        return False


def run_startup_manager() -> None:
    """Interactive enable/disable of startup programs."""
    admin = _is_admin()
    items = enumerate_startup()
    if not items:
        print("  No startup programs found in Run keys or Startup folders.")
        return
    desired = [it["enabled"] for it in items]

    while True:
        print()
        _title("STARTUP PROGRAMS")
        print("  Programs that launch when Windows starts. Turning some off = faster boot.")
        print(f"  Type a number to toggle, {_color('S', GREEN)} to save, "
              f"{_color('Q', YELLOW)} to go back.")
        if not admin:
            print(f"  {_color('Note', YELLOW)}: not elevated - HKLM/system items "
                  f"can't be changed. Launch as administrator for those.")
        _hr()
        for idx, it in enumerate(items, start=1):
            box = _color("[x]", GREEN) if desired[idx - 1] else _color("[ ]", YELLOW)
            changed = "*" if desired[idx - 1] != it["enabled"] else " "
            cmd = it["command"]
            if len(cmd) > 26:
                cmd = cmd[:23] + "..."
            print(f"  {box}{changed}{idx:>2}. {it['display'][:30]:<30} "
                  f"{it['source']:<13} {cmd}")
        _hr()
        print("  [x]=starts at boot   * = pending change")
        try:
            choice = input("  [number]=toggle  [S]ave  [Q]uit: ").strip().lower()
        except EOFError:
            return
        if choice in ("q", ""):
            print("  No changes applied.")
            return
        if choice == "s":
            applied = failed = 0
            for i, it in enumerate(items):
                if desired[i] == it["enabled"]:
                    continue
                if set_startup_enabled(it, desired[i]):
                    it["enabled"] = desired[i]
                    applied += 1
                    log(f"STARTUP: {'enabled' if desired[i] else 'disabled'} "
                        f"{it['display']} ({it['source']})", to_console=False)
                else:
                    failed += 1
            msg = f"  {_color('[SAVED]', GREEN)} {applied} change(s) applied."
            if failed:
                msg += (f" {_color(str(failed) + ' failed', YELLOW)} "
                        f"(need admin for system items).")
            print(msg)
            print("  Changes take effect at the next sign-in "
                  "(already-running apps stay open).")
            return
        if choice.isdigit():
            i = int(choice)
            if 1 <= i <= len(items):
                desired[i - 1] = not desired[i - 1]
            continue
        print("  Unrecognized input.")


# --------------------------------------------------------------------------- #
# Pro tune-ups: Windows Defender exclusions (dev-speed). Reversible; needs admin.
# --------------------------------------------------------------------------- #

def _ps(cmd: str, timeout: int = 60) -> tuple:
    """Run a PowerShell command hidden. Returns (returncode, stdout, stderr)."""
    import subprocess
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout,
            creationflags=0x08000000)  # CREATE_NO_WINDOW
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


def defender_status() -> dict:
    """Detect whether Microsoft Defender is present and active."""
    rc, out, _ = _ps("try{$s=Get-MpComputerStatus;"
                     "\"$($s.AntivirusEnabled)|$($s.RealTimeProtectionEnabled)\"}"
                     "catch{'ERR'}")
    if rc != 0 or out in ("", "ERR"):
        return {"available": False, "realtime": False}
    parts = out.split("|")
    return {"available": True,
            "av_enabled": parts[0] == "True",
            "realtime": len(parts) > 1 and parts[1] == "True"}


def _clean_excl(text: str) -> list:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("N/A") or "Must be an administrator" in s:
            continue
        out.append(s)
    return out


def defender_get_exclusions() -> tuple:
    """Return (paths, processes) currently excluded (empty if not readable)."""
    rc, out, _ = _ps("(Get-MpPreference).ExclusionPath")
    paths = _clean_excl(out) if rc == 0 else []
    rc2, out2, _ = _ps("(Get-MpPreference).ExclusionProcess")
    procs = _clean_excl(out2) if rc2 == 0 else []
    return paths, procs


def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def defender_add(kind: str, value: str) -> tuple:
    opt = "ExclusionPath" if kind == "path" else "ExclusionProcess"
    rc, _, err = _ps(f"Add-MpPreference -{opt} {_ps_quote(value)}")
    return rc == 0, err


def defender_remove(kind: str, value: str) -> tuple:
    opt = "ExclusionPath" if kind == "path" else "ExclusionProcess"
    rc, _, err = _ps(f"Remove-MpPreference -{opt} {_ps_quote(value)}")
    return rc == 0, err


def _suggested_dev_paths() -> list:
    env = os.environ
    cands = [
        r"C:\laragon",
        os.path.join(env.get("LOCALAPPDATA", ""), "npm-cache"),
        os.path.join(env.get("APPDATA", ""), "npm"),
        os.path.join(env.get("USERPROFILE", ""), "go"),
        os.path.join(env.get("USERPROFILE", ""), ".cargo"),
        os.path.join(env.get("USERPROFILE", ""), ".gradle"),
        os.path.join(env.get("USERPROFILE", ""), ".nuget"),
    ]
    return [p for p in cands if p and os.path.isdir(p)]


_SUGGESTED_DEV_PROCS = ["php.exe", "mysqld.exe", "httpd.exe", "node.exe",
                        "python.exe", "code.exe", "Code.exe"]


def run_defender_manager() -> None:
    """Manage Microsoft Defender folder/process exclusions (reversible)."""
    st = defender_status()
    if not st["available"]:
        print("  Microsoft Defender is not the active antivirus on this PC")
        print("  (a third-party AV may be installed), so exclusions can't be")
        print("  managed here. Nothing changed.")
        return
    admin = _is_admin()

    while True:
        paths, procs = defender_get_exclusions()
        print()
        _title("ANTIVIRUS EXCLUSIONS (Defender)")
        rt = _color("ON", GREEN) if st["realtime"] else _color("OFF", YELLOW)
        print(f"  Real-time protection: {rt}")
        print("  Excluding a folder/process makes builds & dev tools faster, but")
        print(f"  {_color('Defender will not scan it', YELLOW)} - only exclude paths you trust.")
        if not admin:
            print(f"  {_color('Note', YELLOW)}: not elevated - adding/removing needs admin.")
        _hr()
        if not admin:
            print(f"  {_color('Run as administrator', YELLOW)} to view and change "
                  f"exclusions.")
            print("  (The desktop shortcut already launches elevated.)")
            _hr()
            print("  Q. Back")
            _hr()
            try:
                if input("  Choose: ").strip().lower() in ("q", ""):
                    return
            except EOFError:
                return
            continue
        _section("Excluded folders")
        if paths:
            for i, p in enumerate(paths, start=1):
                print(f"     {i}. {p}")
        else:
            print("     (none)")
        _section("Excluded processes")
        base = len(paths)
        if procs:
            for j, p in enumerate(procs, start=base + 1):
                print(f"     {j}. {p}")
        else:
            print("     (none)")
        _hr()
        print("  F. Add a folder to exclude        R. Remove an exclusion")
        print("  P. Add a process to exclude       S. Suggest common dev items")
        print("  Q. Back")
        _hr()
        try:
            choice = input("  Choose: ").strip().lower()
        except EOFError:
            return

        if choice in ("q", ""):
            return
        if choice == "f":
            try:
                p = input("    Full folder path to exclude: ").strip().strip('"')
            except EOFError:
                continue
            if not p:
                continue
            if not os.path.isdir(p):
                print("    That folder doesn't exist. Not added.")
                continue
            ok, err = defender_add("path", p)
            print(f"    {_color('[ADDED]', GREEN)} {p}" if ok
                  else f"    {_color('[FAIL]', RED)} {err or 'need admin'}")
            if ok:
                log(f"DEFENDER: added folder exclusion {p}", to_console=False)
            continue
        if choice == "p":
            try:
                p = input("    Process name to exclude (e.g. php.exe): ").strip()
            except EOFError:
                continue
            if not p:
                continue
            ok, err = defender_add("process", p)
            print(f"    {_color('[ADDED]', GREEN)} {p}" if ok
                  else f"    {_color('[FAIL]', RED)} {err or 'need admin'}")
            if ok:
                log(f"DEFENDER: added process exclusion {p}", to_console=False)
            continue
        if choice == "s":
            sp = _suggested_dev_paths()
            print("    Suggested dev folders found on this PC:")
            for p in sp:
                print(f"      - {p}")
            print(f"    Suggested dev processes: {', '.join(_SUGGESTED_DEV_PROCS[:5])}")
            if _confirm("    Add ALL suggested folders + processes? [y/n]: "):
                added = 0
                for p in sp:
                    if defender_add("path", p)[0]:
                        added += 1
                        log(f"DEFENDER: added folder exclusion {p}", to_console=False)
                for pr in ("php.exe", "mysqld.exe", "httpd.exe", "node.exe"):
                    if defender_add("process", pr)[0]:
                        added += 1
                        log(f"DEFENDER: added process exclusion {pr}", to_console=False)
                print(f"    {_color('[DONE]', GREEN)} Added {added} exclusion(s)."
                      if added else
                      f"    {_color('[FAIL]', RED)} Nothing added (need admin?).")
            continue
        if choice == "r":
            allx = [("path", p) for p in paths] + [("process", p) for p in procs]
            if not allx:
                print("    Nothing to remove.")
                continue
            try:
                n = int(input("    Number to remove: ").strip())
            except (ValueError, EOFError):
                continue
            if 1 <= n <= len(allx):
                kind, value = allx[n - 1]
                ok, err = defender_remove(kind, value)
                print(f"    {_color('[REMOVED]', GREEN)} {value}" if ok
                      else f"    {_color('[FAIL]', RED)} {err or 'need admin'}")
                if ok:
                    log(f"DEFENDER: removed {kind} exclusion {value}", to_console=False)
            continue
        print("  Unrecognized choice.")


# --------------------------------------------------------------------------- #
# Pro tune-ups: curated Windows service tuning. Reversible; needs admin.
# --------------------------------------------------------------------------- #

_MODE_TOKEN = {"Auto": "auto", "Manual": "manual", "Disabled": "disabled"}
_TOKEN_PS = {"auto": "Automatic", "manual": "Manual", "disabled": "Disabled"}


def svc_query(names: list) -> dict:
    """Return {name: {'mode': token, 'state': 'Running'/'Stopped'}} for existing."""
    import json
    if not names:
        return {}
    filt = " or ".join(f"Name='{n}'" for n in names)
    rc, out, _ = _ps(f'Get-CimInstance Win32_Service -Filter "{filt}" | '
                     f'Select-Object Name,StartMode,State | ConvertTo-Json -Compress')
    if rc != 0 or not out:
        return {}
    try:
        data = json.loads(out)
    except ValueError:
        return {}
    if isinstance(data, dict):
        data = [data]
    result = {}
    for d in data:
        result[d["Name"]] = {"mode": _MODE_TOKEN.get(d.get("StartMode"), "manual"),
                             "state": d.get("State", "")}
    return result


def svc_set(name: str, token: str) -> tuple:
    """Set a service's startup type. Returns (ok, error)."""
    st = _TOKEN_PS.get(token)
    if not st:
        return False, "bad target"
    rc, _, err = _ps(f"Set-Service -Name '{name}' -StartupType {st} -ErrorAction Stop")
    return rc == 0, err


def run_service_manager() -> None:
    """Tune curated background services to Manual/Disabled (reversible)."""
    labels = {s[0]: (s[1], s[2], s[3]) for s in SERVICE_TUNING}
    present = svc_query([s[0] for s in SERVICE_TUNING])
    if not present:
        print("  Could not read services (or none of the curated ones exist here).")
        return
    order = [s[0] for s in SERVICE_TUNING if s[0] in present]
    admin = _is_admin()
    cfg = load_config()
    desired = {n: present[n]["mode"] for n in order}  # start = current

    while True:
        print()
        _title("SERVICE TUNING")
        print("  Sets noisy background services to Manual/Disabled to cut load.")
        print("  Curated & safe. Changes apply at next boot. Fully restorable.")
        if not admin:
            print(f"  {_color('Note', YELLOW)}: not elevated - applying needs admin.")
        _hr()
        for i, n in enumerate(order, start=1):
            friendly, why, rec = labels[n]
            cur = present[n]
            now = f"{cur['mode']}/{'run' if cur['state'] == 'Running' else 'stop'}"
            tgt = desired[n]
            star = _color("*", YELLOW) if tgt != cur["mode"] else " "
            tgt_col = GREEN if tgt != cur["mode"] else ""
            print(f"  {i:>2}.{star}{friendly[:34]:<35}{now:<14} -> "
                  f"{_color(tgt, tgt_col) if tgt_col else tgt}")
        _hr()
        print("  number = toggle to recommended   A = all recommended")
        print("  R = restore originals            S = apply    Q = back")
        _hr()
        try:
            choice = input("  Choose: ").strip().lower()
        except EOFError:
            return
        if choice in ("q", ""):
            return
        if choice == "a":
            for n in order:
                desired[n] = labels[n][2]
            continue
        if choice == "r":
            saved = cfg.get("services", {})
            if not saved:
                print("  No saved originals to restore (nothing was changed yet).")
                continue
            done = fail = 0
            for n, orig in list(saved.items()):
                ok, _ = svc_set(n, orig)
                if ok:
                    done += 1
                    log(f"SERVICE: restored {n} -> {orig}", to_console=False)
                else:
                    fail += 1
            cfg["services"] = {} if fail == 0 else cfg["services"]
            if fail == 0:
                save_config(cfg)
            print(f"  {_color('[RESTORED]', GREEN)} {done} service(s)"
                  + (f", {fail} failed" if fail else "") + ".")
            present = svc_query(order)
            desired = {n: present[n]["mode"] for n in order}
            continue
        if choice == "s":
            changes = [(n, desired[n]) for n in order if desired[n] != present[n]["mode"]]
            if not changes:
                print("  No changes to apply.")
                continue
            if not admin:
                print(f"  {_color('[FAIL]', RED)} Run as administrator to apply.")
                continue
            applied = fail = 0
            for n, tgt in changes:
                cfg.setdefault("services", {})
                if n not in cfg["services"]:
                    cfg["services"][n] = present[n]["mode"]  # capture original once
                ok, err = svc_set(n, tgt)
                if ok:
                    applied += 1
                    log(f"SERVICE: set {n} -> {tgt}", to_console=False)
                else:
                    fail += 1
                    cfg["services"].pop(n, None)  # nothing changed; drop capture
                    print(f"    {_color('[SKIP]', YELLOW)} {n}: {err or 'access denied'}")
            save_config(cfg)
            print(f"  {_color('[APPLIED]', GREEN)} {applied} change(s)"
                  + (f", {fail} could not be changed" if fail else "")
                  + ". Restart to take full effect.")
            present = svc_query(order)
            desired = {n: present[n]["mode"] for n in order}
            continue
        if choice.isdigit():
            i = int(choice)
            if 1 <= i <= len(order):
                n = order[i - 1]
                rec = labels[n][2]
                desired[n] = rec if desired[n] == present[n]["mode"] else present[n]["mode"]
            continue
        print("  Unrecognized choice.")


# --------------------------------------------------------------------------- #
# Hung-window detection (Win32)
# --------------------------------------------------------------------------- #

def get_window_hang_map() -> dict:
    result = {}
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.IsHungAppWindow.restype = wintypes.BOOL
        user32.IsHungAppWindow.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def _cb(hwnd, _lp):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                entry = result.setdefault(pid.value, {"hung": False, "titles": []})
                entry["titles"].append(buf.value)
                if bool(user32.IsHungAppWindow(hwnd)):
                    entry["hung"] = True
            except Exception:  # noqa: BLE001
                pass
            return True

        user32.EnumWindows(WNDENUMPROC(_cb), 0)
    except Exception:  # noqa: BLE001
        pass
    return result


def scan_processes():
    hang_map = get_window_hang_map()
    ncpu = psutil.cpu_count(logical=True) or 1
    psutil.cpu_percent(None)
    live = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            p.cpu_percent(None)
            live.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    time.sleep(CPU_SAMPLE_SECONDS)
    sys_cpu = psutil.cpu_percent(None)

    procs = []
    for p in live:
        try:
            with p.oneshot():
                name = (p.name() or "?").lower()
                rss = p.memory_info().rss
                cpu = p.cpu_percent(None) / ncpu
            info = hang_map.get(p.pid, {})
            procs.append({
                "pid": p.pid, "name": name, "mem_mb": rss / (1024 * 1024),
                "cpu": cpu, "hung": info.get("hung", False),
                "titles": info.get("titles", []), "proc": p,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return procs, sys_cpu, ncpu


def problems_for(pd: dict) -> list:
    tags = []
    if pd["hung"]:
        tags.append("NOT RESPONDING")
    if pd["cpu"] >= CPU_BUSY_PCT:
        tags.append(f"HIGH CPU ({pd['cpu']:.0f}%)")
    if pd["mem_mb"] >= HEAVY_MEM_MB:
        tags.append(f"HIGH MEM ({pd['mem_mb']:.0f} MB)")
    return tags


def is_eligible(pd: dict) -> tuple:
    if pd["name"] in BLOCKLIST:
        return False, "protected (critical system process)"
    if pd["hung"] and KILL_HUNG:
        return True, "not responding"
    if pd["name"] in ALLOWLIST and pd["mem_mb"] >= HEAVY_MEM_MB:
        return True, f"allowlisted & using {pd['mem_mb']:.0f} MB"
    return False, "not on allowlist"


def close_hung_background(cfg: dict) -> tuple:
    """
    Unattended close of Not-Responding apps (used by --auto). Only acts if
    opted in. Confirms the app is STILL hung after a grace delay before killing.
    Never touches BLOCKLIST processes. Returns (count, [(name, pid, title), ...]).
    """
    pcfg = cfg.get("process", {})
    if not pcfg.get("auto_close_hung"):
        return 0, []

    first = get_window_hang_map()
    hung_pids = {pid for pid, info in first.items() if info.get("hung")}
    if not hung_pids:
        return 0, []

    time.sleep(max(0, pcfg.get("hung_grace_seconds", 20)))

    second = get_window_hang_map()
    closed = []
    for pid in hung_pids:
        if not second.get(pid, {}).get("hung"):
            continue  # recovered during grace period -> leave it
        try:
            p = psutil.Process(pid)
            name = (p.name() or "").lower()
            if name in BLOCKLIST:
                continue
            title = (second.get(pid, {}).get("titles") or [""])[0]
            p.terminate()
            try:
                p.wait(timeout=5)
            except psutil.TimeoutExpired:
                p.kill()
            closed.append((name, pid, title))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return len(closed), closed


def terminate(pd: dict) -> bool:
    if pd["name"] in BLOCKLIST:
        print(f"  [SKIP] {pd['name']} (PID {pd['pid']}) is protected.")
        return False
    proc = pd["proc"]
    label = f"{pd['name']} (PID {pd['pid']})"
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        print(f"  {_color('[CLOSED]', GREEN)} {label}")
        return True
    except psutil.NoSuchProcess:
        print(f"  [GONE]  {label} already exited.")
        return False
    except psutil.AccessDenied:
        print(f"  {_color('[DENIED]', YELLOW)} {label} - run as Administrator.")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] {label} - {exc}")
        return False


# --------------------------------------------------------------------------- #
# Display
# --------------------------------------------------------------------------- #

def _hr() -> None:
    print("-" * 66)


def _title(text: str) -> None:
    """Print a bold, boxed section title for a professional look."""
    bar = "=" * 66
    print(_color(bar, CYAN))
    print(_color(f"  {text}", BOLD + CYAN))
    print(_color(bar, CYAN))


def _clear() -> None:
    """Clear the console for a fresh, app-like redraw (cls is reliable on Windows)."""
    try:
        import os as _os
        _os.system("cls")
    except Exception:  # noqa: BLE001
        pass


def _header_lines(bolt_color: str = None) -> list:
    """Return the header as a list of ready-to-print lines."""
    bc = bolt_color if bolt_color is not None else (BOLD + CYAN)
    bar = "=" * 66
    ew = max((len(x) for x in EMBLEM), default=0)
    n = max(len(EMBLEM), len(BANNER))
    lines = [_color(bar, CYAN)]
    for i in range(n):
        el = EMBLEM[i] if i < len(EMBLEM) else ""
        bl = BANNER[i] if i < len(BANNER) else ""
        lines.append(_color(" " + el.ljust(ew), bc) + _color("  " + bl, BOLD + CYAN))
    lines.append("")  # gap so the tagline isn't cramped against the logo
    tag = f"  {APP_TAGLINE}"
    ver = f"v{APP_VERSION}"
    gap = max(2, 66 - len(tag) - len(ver))
    lines.append(_color(tag + " " * gap + ver, CYAN))
    lines.append(_color(bar, CYAN))
    return lines


def _brand_header(bolt_color: str = None) -> None:
    """Print the branded product header: bolt emblem + PersonalCleaner logo."""
    for line in _header_lines(bolt_color):
        print(line)


def _animate_intro() -> None:
    """
    Lightning-flash the bolt a couple of times, IN PLACE, then settle.
    Colours only. Reprints over the same lines (cursor-up) so frames never
    stack, even on consoles that don't honour full-screen clears.
    """
    if not RESET:  # no ANSI -> no animation
        return
    white = "\033[1m\033[97m"
    dim = "\033[90m"
    frames = [(dim, 0.05), (white, 0.08), (dim, 0.05), (white, 0.08),
              (BOLD + CYAN, 0.06)]
    _clear()
    for idx, (col, delay) in enumerate(frames):
        buf = _header_lines(col)
        if idx > 0:
            sys.stdout.write(f"\033[{len(buf)}A")  # cursor up to redraw in place
        sys.stdout.write("".join(line + "\033[K\n" for line in buf))  # \033[K clears tail
        sys.stdout.flush()
        time.sleep(delay)


def _ram_bar(pct: float) -> str:
    """A small coloured ASCII usage bar, e.g. [#########-] 96%."""
    seg = 10
    filled = max(0, min(seg, int(round(pct / 10.0))))
    bar = "[" + "#" * filled + "-" * (seg - filled) + "]"
    if pct >= PRESSURE_PERCENT:
        col = RED
    elif pct >= PRESSURE_PERCENT - 5:
        col = YELLOW
    else:
        col = GREEN
    return _color(f"{bar} {pct:.0f}%", col)


def _section(label: str) -> None:
    """Print a bold sub-section label."""
    print(_color(f"  {label}", BOLD))


def _confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def print_context(sys_cpu: float, ncpu: int) -> None:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    if mem.percent >= PRESSURE_PERCENT:
        col, note = RED, "UNDER PRESSURE"
    elif mem.percent >= PRESSURE_PERCENT - 5:
        col, note = YELLOW, "getting high"
    else:
        col, note = GREEN, "healthy"
    print("  SYSTEM CONTEXT (informational)")
    print(f"    RAM  : {_color(f'{_gb(mem.used):.2f} GB used ({mem.percent:.1f} %)', col)}"
          f"  of {_gb(mem.total):.2f} GB   [{note}]")
    if swap.total > 0:
        print(f"    Swap : {_gb(swap.used):.2f} GB used ({swap.percent:.1f} %)"
              f" of {_gb(swap.total):.2f} GB")
    print(f"    CPU  : {sys_cpu:.1f} %   ({ncpu} logical cores)")
    print(f"    Procs: {len(psutil.pids())} running")


def health_and_close(procs, sys_cpu, ncpu) -> None:
    print_context(sys_cpu, ncpu)
    _hr()
    problem_list = []
    for pd in procs:
        if pd["pid"] in IGNORE_PIDS or pd["name"] in IGNORE_NAMES:
            continue
        tags = problems_for(pd)
        if tags:
            problem_list.append((pd, tags))
    problem_list.sort(key=lambda t: (not t[0]["hung"], -t[0]["mem_mb"]))

    if not problem_list:
        print(_color("  No misbehaving applications detected.", GREEN))
        _hr()
        return

    print(f"  PROBLEMS DETECTED ({len(problem_list)}):")
    for pd, tags in problem_list:
        eligible, reason = is_eligible(pd)
        title = pd["titles"][0] if pd["titles"] else ""
        col = RED if pd["hung"] else YELLOW
        print(_color(f"    - {pd['name']} (PID {pd['pid']}) : {', '.join(tags)}", col))
        if title:
            print(f"        window : \"{title}\"")
        print(f"        action : {'CAN CLOSE' if eligible else 'left alone'} ({reason})")
    _hr()

    eligible_pds = [pd for pd, _ in problem_list if is_eligible(pd)[0]]
    if not eligible_pds:
        print("  Nothing eligible to close. Nothing done.")
        _hr()
        return
    closed = skipped = 0
    for pd in eligible_pds:
        why = "NOT RESPONDING" if pd["hung"] else f"{pd['mem_mb']:.0f} MB"
        label = f"{pd['name']} (PID {pd['pid']}, {why})"
        if CONFIRM_BEFORE_KILL and not _confirm(f"  Close {label}? [y/n]: "):
            print(f"  [SKIP] {label} - left running.")
            skipped += 1
            continue
        if terminate(pd):
            closed += 1
    _hr()
    print(f"  Done. Closed {closed}, skipped {skipped}, of {len(eligible_pds)} eligible.")
    _hr()


# --------------------------------------------------------------------------- #
# Scheduler (Task Scheduler via schtasks)
# --------------------------------------------------------------------------- #

def _hide_console() -> None:
    """Hide this process's console window (used in --auto so it runs silent)."""
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:  # noqa: BLE001
        pass


def _agent_exe() -> str:
    """The single executable itself runs the scheduled background job (--auto)."""
    return sys.executable if getattr(sys, "frozen", False) else sys.executable


def _task_names() -> list:
    return [f"{TASK_PREFIX}-Idle", f"{TASK_PREFIX}-Daily"]


def scheduler_state() -> str:
    """Return 'enabled', 'disabled', or 'absent'."""
    import subprocess
    try:
        res = subprocess.run(["schtasks", "/Query", "/TN", f"{TASK_PREFIX}-Idle",
                              "/FO", "LIST"], capture_output=True, text=True)
    except Exception:  # noqa: BLE001
        return "absent"
    if res.returncode != 0:
        return "absent"
    return "disabled" if "disabled" in res.stdout.lower() else "enabled"


def enable_scheduler() -> None:
    import subprocess
    if scheduler_state() == "absent":
        install_scheduler(DEFAULT_IDLE_MINUTES, DEFAULT_DAILY_TIME)
    for name in _task_names():
        subprocess.run(["schtasks", "/Change", "/TN", name, "/ENABLE"],
                       capture_output=True, text=True)
    print(f"  {_color('[ON]', GREEN)} Background schedule enabled "
          f"(idle {DEFAULT_IDLE_MINUTES} min + daily {DEFAULT_DAILY_TIME}).")
    cfg = load_config()
    active = (any(cfg["cleanup"].values())
              or cfg["memory"].get("trim_on_pressure")
              or cfg["process"].get("auto_close_hung"))
    if not active:
        print(f"  {_color('Tip', YELLOW)}: no automatic actions are enabled yet - "
              f"open Settings (3) to choose what the background run should do.")


def disable_scheduler() -> None:
    import subprocess
    for name in _task_names():
        subprocess.run(["schtasks", "/Change", "/TN", name, "/DISABLE"],
                       capture_output=True, text=True)
    print(f"  {_color('[OFF]', YELLOW)} Background schedule paused.")


# --------------------------------------------------------------------------- #
# Weekly idle restart
# --------------------------------------------------------------------------- #

RESTART_TASK = f"{TASK_PREFIX}-Restart"


def _idle_seconds() -> float:
    """Seconds since the last keyboard/mouse input (how long the user is away)."""
    try:
        import ctypes
        from ctypes import wintypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(lii)
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        kernel32.GetTickCount.restype = wintypes.DWORD
        if not user32.GetLastInputInfo(ctypes.byref(lii)):
            return 0.0
        # 32-bit tick math with wrap-around handling.
        diff = (kernel32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF
        return diff / 1000.0
    except Exception:  # noqa: BLE001
        return 0.0


def restart_task_state() -> str:
    """Return 'present' or 'absent' for the weekly restart task."""
    import subprocess
    try:
        res = subprocess.run(["schtasks", "/Query", "/TN", RESTART_TASK],
                             capture_output=True, text=True)
        return "present" if res.returncode == 0 else "absent"
    except Exception:  # noqa: BLE001
        return "absent"


def enable_restart(day: str, time_str: str) -> bool:
    import subprocess
    exe = _agent_exe()
    cmd = ["schtasks", "/Create", "/TN", RESTART_TASK,
           "/TR", f'"{exe}" --scheduled-restart',
           "/SC", "WEEKLY", "/D", day, "/ST", time_str, "/F"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def disable_restart() -> None:
    import subprocess
    subprocess.run(["schtasks", "/Delete", "/TN", RESTART_TASK, "/F"],
                   capture_output=True, text=True)


def run_scheduled_restart() -> None:
    """Task action: restart ONLY if enabled and the user has been idle enough."""
    _hide_console()
    import subprocess
    cfg = load_config()
    r = cfg.get("restart", {})
    if not r.get("enabled"):
        log("RESTART: fired but feature disabled; skipping.", to_console=False)
        return
    idle = _idle_seconds()
    need = r.get("idle_minutes", 15) * 60
    if idle < need:
        log(f"RESTART: user active (idle {idle:.0f}s < {need}s); skipped.",
            to_console=False)
        return
    warn = r.get("warn_seconds", 120)
    msg = (f"Personal Cleaner maintenance restart in {warn // 60} minute(s). "
           f"Save your work. To cancel, open Run and type:  shutdown /a")
    subprocess.run(["shutdown", "/r", "/t", str(warn), "/c", msg])
    log(f"RESTART: idle {idle:.0f}s >= {need}s; restart scheduled in {warn}s.",
        to_console=False)


def _ask(prompt: str, default: str) -> str:
    try:
        val = input(f"  {prompt} [{default}]: ").strip()
        return val or default
    except EOFError:
        return default


def run_restart_settings(cfg: dict) -> None:
    """Configure the weekly idle restart: set day/time/idle and turn ON or OFF.

    You can change the schedule and leave it OFF; the task is only created when
    you save with status ON.
    """
    r = cfg["restart"]
    days = {"SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"}
    pending_on = restart_task_state() == "present"
    day = r.get("day", "SUN")
    time_str = r.get("time", "04:00")
    idle_min = r.get("idle_minutes", 60)
    warn_min = r.get("warn_seconds", 120) // 60

    while True:
        print()
        _title("WEEKLY IDLE RESTART")
        print("  Restarts the PC on a schedule - but only while you're away,")
        print("  and always after a warning you can cancel. Set it up, or leave OFF.")
        _hr()
        status = _color("ON", GREEN) if pending_on else _color("OFF", YELLOW)
        print(f"    Status : {status}")
        print(f"    When   : {day} at {time_str}")
        print(f"    Only if idle >= {idle_min} min")
        print(f"    Always shows a {warn_min}-min warning; cancel with 'shutdown /a'")
        _hr()
        print(f"    1. Turn {'OFF' if pending_on else 'ON'}")
        print("    2. Set day")
        print("    3. Set time")
        print("    4. Set idle threshold (minutes)")
        print("    S. Save & apply")
        print("    Q. Back (discard changes)")
        _hr()
        try:
            choice = input("  Choose: ").strip().lower()
        except EOFError:
            return

        if choice == "1":
            pending_on = not pending_on
        elif choice == "2":
            day = _ask("Day (SUN-SAT)", day).upper()
            if day not in days:
                print("    Invalid day; keeping previous.")
                day = r.get("day", "SUN")
        elif choice == "3":
            time_str = _ask("Time (HH:MM 24h)", time_str)
        elif choice == "4":
            val = _ask("Idle minutes before restart", str(idle_min))
            try:
                idle_min = max(1, int(val))
            except ValueError:
                print("    Unchanged.")
        elif choice == "s":
            r.update({"day": day, "time": time_str, "idle_minutes": idle_min,
                      "enabled": pending_on})
            ok = True
            if pending_on:
                ok = enable_restart(day, time_str)
            else:
                disable_restart()
            save_config(cfg)
            if not ok:
                print(f"  {_color('[FAIL]', RED)} Could not create the task "
                      f"(try running as Administrator).")
            elif pending_on:
                print(f"  {_color('[SAVED]', GREEN)} Restart ON - {day} {time_str}, "
                      f"only if idle >= {idle_min} min.")
            else:
                print(f"  {_color('[SAVED]', GREEN)} Restart OFF. "
                      f"Schedule saved ({day} {time_str}) for when you turn it on.")
            return
        elif choice in ("q", ""):
            print("  No changes applied.")
            return
        else:
            print("  Unrecognized choice.")


def install_scheduler(idle_min: int, daily_time: str) -> None:
    import subprocess
    exe = _agent_exe()
    run = f'"{exe}" --auto'
    idle_task = f"{TASK_PREFIX}-Idle"
    daily_task = f"{TASK_PREFIX}-Daily"

    jobs = [
        (["schtasks", "/Create", "/TN", idle_task, "/TR", run,
          "/SC", "ONIDLE", "/I", str(idle_min), "/F"],
         f"on-idle ({idle_min} min)"),
        (["schtasks", "/Create", "/TN", daily_task, "/TR", run,
          "/SC", "DAILY", "/ST", daily_time, "/F"],
         f"daily ({daily_time})"),
    ]
    print(f"  Installing scheduled background cleanup using:\n    {run}")
    _hr()
    for cmd, desc in jobs:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                print(f"  {_color('[OK]', GREEN)} {desc} task created.")
            else:
                msg = (res.stderr or res.stdout).strip()
                print(f"  {_color('[FAIL]', RED)} {desc}: {msg}")
                if "Access is denied" in msg:
                    print("        -> Re-run this as Administrator.")
        except Exception as exc:  # noqa: BLE001
            print(f"  [ERROR] {desc}: {exc}")
    _hr()
    print(f"  Log file: {LOG_FILE}")


def uninstall_scheduler() -> None:
    import subprocess
    for suffix in ("Idle", "Daily"):
        name = f"{TASK_PREFIX}-{suffix}"
        try:
            res = subprocess.run(["schtasks", "/Delete", "/TN", name, "/F"],
                                 capture_output=True, text=True)
            ok = res.returncode == 0
            tag = _color('[OK]', GREEN) if ok else _color('[--]', YELLOW)
            print(f"  {tag} {name}: "
                  f"{'removed' if ok else (res.stderr or res.stdout).strip()}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [ERROR] {name}: {exc}")


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #

def run_auto() -> None:
    """Silent background run: cleanup + health snapshot to the log. No prompts."""
    _hide_console()
    log("=== AUTO run started ===", to_console=False)
    try:
        cfg = load_config()
        freed = run_cleanup(dry_run=False, cfg=cfg)

        # Memory trim (opt-in) when RAM is under pressure.
        mcfg = cfg.get("memory", {})
        ram_freed = 0
        mem = psutil.virtual_memory()
        if mcfg.get("trim_on_pressure") and mem.percent >= mcfg.get("pressure_percent", 85):
            res = memory_trim(mcfg.get("purge_standby", True),
                              mcfg.get("empty_working_sets", False))
            ram_freed = res["freed"]
            if res["denied"]:
                log("AUTO: memory trim skipped - needs Administrator.", to_console=False)
            else:
                log(f"AUTO: memory trim freed {_mb(ram_freed):.0f} MB RAM "
                    f"({', '.join(res['actions']) or 'no-op'})", to_console=False)

        # Auto-close hung apps (opt-in).
        hung_closed, hung_list = close_hung_background(cfg)
        for name, pid, title in hung_list:
            log(f"AUTO: closed hung app {name} (PID {pid}) \"{title}\"", to_console=False)

        procs, sys_cpu, _ = scan_processes()
        problems = sum(1 for pd in procs
                       if pd["pid"] not in IGNORE_PIDS
                       and pd["name"] not in IGNORE_NAMES
                       and problems_for(pd))
        mem = psutil.virtual_memory()
        note = ("closed" if cfg.get("process", {}).get("auto_close_hung")
                else "not touched in auto mode")
        log(f"AUTO: freed {_mb(freed):.1f} MB disk, {_mb(ram_freed):.0f} MB RAM, "
            f"{hung_closed} hung app(s) closed | RAM {mem.percent:.0f}% | "
            f"CPU {sys_cpu:.0f}% | {problems} app problem(s) ({note})", to_console=False)

        # Toast summary (opt-out) when something actually happened.
        if cfg.get("notifications", True) and (freed > 0 or ram_freed > 0 or hung_closed):
            parts = []
            if freed > 0:
                parts.append(f"{_mb(freed):.0f} MB disk")
            if ram_freed > 0:
                parts.append(f"{_mb(ram_freed):.0f} MB RAM")
            if hung_closed:
                parts.append(f"{hung_closed} hung app(s) closed")
            show_toast("Personal Cleaner", "Freed " + ", ".join(parts))
    except Exception as exc:  # noqa: BLE001
        log(f"AUTO ERROR: {exc}", to_console=False)
    log("=== AUTO run finished ===", to_console=False)


def free_ram_now(cfg: dict) -> None:
    """Interactive on-demand RAM trim with before/after report."""
    mcfg = cfg.get("memory", {})
    print("  Freeing cached RAM (purging standby list)...")
    res = memory_trim(mcfg.get("purge_standby", True),
                      mcfg.get("empty_working_sets", False))
    if res["denied"]:
        print(f"  {_color('[DENIED]', YELLOW)} Needs Administrator. "
              f"Right-click the app -> Run as administrator.")
        return
    if not res["ok"]:
        print("  [ERROR] Could not trim memory on this system.")
        return
    mem = psutil.virtual_memory()
    freed_txt = f"{_mb(res['freed']):.0f} MB"
    print(f"  {_color('[DONE]', GREEN)} Freed {_color(freed_txt, GREEN)} "
          f"({', '.join(res['actions'])}). "
          f"RAM now {mem.percent:.1f} % ({_gb(mem.available):.2f} GB free).")


def run_settings() -> None:
    """Interactive checkbox menu for cleanup categories + memory options."""
    cfg = load_config()
    min_age = cfg.get("min_age_hours", MIN_AGE_HOURS)
    print("  Measuring cleanable space per category...")
    est = {key: estimate_category(key, min_age) for key, _ in CLEANUP_CATEGORIES}
    # Map each item code (lowercase) to the config it toggles.
    toggle_map = {}
    for i, (key, _label) in enumerate(CLEANUP_CATEGORIES, start=1):
        toggle_map[f"c{i}"] = ("cleanup", key)
    toggle_map["m1"] = ("memory", None)
    toggle_map["p1"] = ("process", None)
    toggle_map["n1"] = ("notifications", None)

    while True:
        print()
        _title("SETTINGS")
        print(_color("  HOW TO USE", BOLD))
        print("    - Type an item CODE (e.g. C1, M1, P1) and Enter to tick/untick it.")
        print("    - Only TICKED [x] items run during automatic background maintenance.")
        print("    - Values:  A = file age,  R = RAM %,  G = grace seconds.")
        print(f"    - Press {_color('S', GREEN)} to SAVE, or {_color('Q', YELLOW)} to quit WITHOUT saving.")
        _hr()
        _section("CLEANUP  (delete junk files)")
        for idx, (key, label) in enumerate(CLEANUP_CATEGORIES, start=1):
            box = _color("[x]", GREEN) if cfg["cleanup"].get(key) else "[ ]"
            size = f"{_mb(est[key]):.0f} MB" if est[key] else "-"
            print(f"     {box}  {_color(f'C{idx}', BOLD)}  {label:<40} ~{size:>8}")
        _section("MEMORY  (free up RAM)")
        mbox = _color("[x]", GREEN) if cfg["memory"].get("trim_on_pressure") else "[ ]"
        print(f"     {mbox}  {_color('M1', BOLD)}  Auto-free RAM when usage >= "
              f"{cfg['memory'].get('pressure_percent', 85)}% (purge standby list)")
        _section("PROCESSES  (close frozen apps)")
        pbox = _color("[x]", GREEN) if cfg["process"].get("auto_close_hung") else "[ ]"
        print(f"     {pbox}  {_color('P1', BOLD)}  Auto-close Not-Responding apps "
              f"(grace {cfg['process'].get('hung_grace_seconds', 20)}s)")
        print(f"          {_color('WARNING', YELLOW)}: closing a frozen app can lose its unsaved work.")
        _section("NOTIFICATIONS")
        nbox = _color("[x]", GREEN) if cfg.get("notifications", True) else "[ ]"
        print(f"     {nbox}  {_color('N1', BOLD)}  Show a toast after each background run")
        _hr()
        age_txt = f"{cfg['min_age_hours']:g}h"
        print(f"  Current: junk older than {_color(age_txt, BOLD)} "
              f"is eligible for cleanup.")
        _hr()
        try:
            choice = input("  Code to toggle (C1/M1/P1/N1) | A/R/G value | S save | Q quit: ").strip().lower()
        except EOFError:
            print("  (no interactive input; leaving settings unchanged)")
            return

        if choice in ("q", ""):
            print("  Discarded changes.")
            return
        if choice == "s":
            print(f"  {_color('[SAVED]', GREEN)} {CONFIG_FILE}" if save_config(cfg)
                  else "  [ERROR] Could not write config.")
            return
        if choice == "a":
            try:
                val = float(input("    New minimum file age in hours: ").strip())
                if val >= 0:
                    cfg["min_age_hours"] = val
            except (ValueError, EOFError):
                print("    Unchanged.")
            continue
        if choice == "r":
            try:
                val = int(input("    Trigger RAM trim at what usage % (50-99): ").strip())
                if 50 <= val <= 99:
                    cfg["memory"]["pressure_percent"] = val
            except (ValueError, EOFError):
                print("    Unchanged.")
            continue
        if choice == "g":
            try:
                val = int(input("    Grace seconds before closing a hung app (5-300): ").strip())
                if 5 <= val <= 300:
                    cfg["process"]["hung_grace_seconds"] = val
            except (ValueError, EOFError):
                print("    Unchanged.")
            continue
        if choice in toggle_map:
            kind, key = toggle_map[choice]
            if kind == "cleanup":
                cfg["cleanup"][key] = not cfg["cleanup"].get(key, False)
            elif kind == "memory":
                cfg["memory"]["trim_on_pressure"] = not cfg["memory"].get("trim_on_pressure", False)
            elif kind == "process":
                cfg["process"]["auto_close_hung"] = not cfg["process"].get("auto_close_hung", False)
            elif kind == "notifications":
                new_val = not cfg.get("notifications", True)
                cfg["notifications"] = new_val
                if new_val:
                    show_toast("Personal Cleaner", "Notifications enabled.")
            continue
        print("  Unrecognized input.")


def run_scan_and_fix(dry_run_clean: bool) -> None:
    _hr()
    print("  Scanning application health (sampling CPU ~1s)...")
    _hr()
    procs, sys_cpu, ncpu = scan_processes()
    health_and_close(procs, sys_cpu, ncpu)

    cfg = load_config()

    # Offer a RAM trim when memory is under pressure.
    mem = psutil.virtual_memory()
    if mem.percent >= PRESSURE_PERCENT:
        print()
        print(f"  RAM is high ({mem.percent:.1f} %). A standby-list purge can free "
              f"cached memory.")
        if _confirm("  Free up cached RAM now? [y/n]: "):
            free_ram_now(cfg)
        _hr()

    # Cleanup is gated by the checkbox settings.
    active = [k for k, _ in CLEANUP_CATEGORIES if cfg["cleanup"].get(k)]
    print()
    if not active:
        print("  No cleanup categories are enabled yet.")
        if _confirm("  Open settings to choose what to clean? [y/n]: "):
            run_settings()
            cfg = load_config()
            active = [k for k, _ in CLEANUP_CATEGORIES if cfg["cleanup"].get(k)]
        if not active:
            print("  Nothing enabled - skipping cleanup.")
            _hr()
            return
        print()

    run_cleanup(dry_run=True, cfg=cfg)
    _hr()
    if dry_run_clean:
        print("  (--dry-run: no files were deleted.)")
        _hr()
        return
    if _confirm("  Delete the junk shown above now? [y/n]: "):
        print()
        run_cleanup(dry_run=False, cfg=cfg)
    else:
        print("  Skipped cleanup. Nothing deleted.")
    _hr()


def view_log(lines: int = 20) -> None:
    """Print the last few log lines."""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as fh:
            tail = fh.readlines()[-lines:]
    except OSError:
        print("  No log yet.")
        return
    print(f"  Last {len(tail)} log line(s)  ({LOG_FILE}):")
    _hr()
    for line in tail:
        print("  " + line.rstrip())


def view_history(limit: int = 15) -> None:
    """Summarized table of past background (--auto) runs, parsed from the log."""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        print("  No history yet.")
        return
    pat = re.compile(
        r"\[(.*?)\] AUTO: freed ([\d.]+) MB disk, ([\d.]+) MB RAM, "
        r"(\d+) hung app\(s\) closed")
    rows = [m.groups() for ln in lines for m in [pat.search(ln)] if m]
    if not rows:
        print("  No completed background runs recorded yet.")
        print("  (History fills in once the background schedule runs.)")
        return
    rows = rows[-limit:]
    _title("BACKGROUND RUN HISTORY")
    print(f"  Last {len(rows)} automatic run(s):")
    _hr()
    print(_color(f"    {'When':<20}{'Disk':>10}{'RAM':>10}{'Hung':>7}", BOLD))
    for when, disk, ram, hung in rows:
        print(f"    {when:<20}{disk + ' MB':>10}{ram + ' MB':>10}{hung:>7}")


def _reclaimable_mb() -> float:
    """Total junk (MB) that could be cleaned right now, across all categories."""
    cfg = load_config()
    min_age = cfg.get("min_age_hours", MIN_AGE_HOURS)
    total = 0
    for key, _label in CLEANUP_CATEGORIES:
        try:
            total += estimate_category(key, min_age)
        except Exception:  # noqa: BLE001
            pass
    return total / (1024 * 1024)


def _menu_hints(mem, state: str, reclaimable: float, cfg: dict) -> list:
    """Up to two contextual suggestions for the menu."""
    hints = []
    if mem.percent >= PRESSURE_PERCENT:
        hints.append("RAM is high - M2 frees cached memory.")
    if reclaimable >= 200:
        hints.append(f"~{reclaimable:.0f} MB of junk can be cleaned - run M1.")
    any_auto = (any(cfg["cleanup"].values())
                or cfg["memory"].get("trim_on_pressure")
                or cfg["process"].get("auto_close_hung"))
    if state != "enabled":
        if any_auto:
            hints.append("You picked actions but Auto is OFF - turn on A2.")
        else:
            hints.append("Tip: choose actions in A1, then A2 to automate.")
    if not _is_admin():
        hints.append("Some features need admin - launch via the desktop shortcut.")
    return hints[:2]


def _show_welcome() -> None:
    """One-time friendly intro shown on first launch (no config yet)."""
    _clear()
    _brand_header()
    print()
    print("  Welcome! PersonalCleaner keeps your PC fast and clean -")
    print("  and it only ever does what YOU switch on.")
    print()
    print(f"  {_color('-', GREEN)} Nothing is deleted or closed unless you enable it.")
    print(f"  {_color('-', GREEN)} Every action is reversible and written to a log.")
    print(f"  {_color('-', GREEN)} Run as administrator for full features "
          f"(the desktop shortcut does this).")
    _hr()
    if _confirm("  Open Settings now to choose what to clean? [y/n]: "):
        run_settings()


def run_menu() -> None:
    """Single entry point: interactive menu that houses every feature."""
    global _FINAL_WAIT
    _FINAL_WAIT = False  # the menu manages its own pauses

    if not os.path.exists(CONFIG_FILE):
        _show_welcome()
        save_config(load_config())  # persist defaults so welcome shows once
    else:
        _animate_intro()            # lightning flash on launch
    reclaimable = _reclaimable_mb()

    while True:
        mem = psutil.virtual_memory()
        state = scheduler_state()
        state_lbl = {"enabled": _color("ON", GREEN),
                     "disabled": _color("OFF", YELLOW),
                     "absent": _color("OFF", YELLOW)}[state]
        who = (_color("Administrator", GREEN) if _is_admin()
               else _color("Standard user", YELLOW))
        _clear()
        _brand_header()
        print(f"  {who}   |   RAM {_ram_bar(mem.percent)}   |   "
              f"{len(psutil.pids())} procs   |   Auto: {state_lbl}")
        rc_txt = _color(f"~{reclaimable:.0f} MB", GREEN if reclaimable >= 1 else "")
        print(f"  Reclaimable junk: {rc_txt}")
        _hr()
        hints = _menu_hints(mem, state, reclaimable, load_config())
        if hints:
            print(_color("  Suggested:", BOLD))
            for h in hints:
                print(f"    - {h}")
            _hr()
        restart_on = restart_task_state() == "present"
        print(_color("  MAINTENANCE", BOLD))
        print(f"    {_color('M1', BOLD)}  Scan & fix now     (health + free RAM + cleanup)")
        print(f"    {_color('M2', BOLD)}  Free RAM now")
        print(f"    {_color('M3', BOLD)}  Startup programs   (speed up boot)")
        print(_color("  AUTOMATION", BOLD))
        print(f"    {_color('A1', BOLD)}  Settings           (choose what to clean)")
        print(f"    {_color('A2', BOLD)}  Background schedule    ->  turn {'OFF' if state == 'enabled' else 'ON'}")
        print(f"    {_color('A3', BOLD)}  Weekly idle restart   ->  turn {'OFF' if restart_on else 'ON'}")
        print(_color("  PRO TUNE-UPS", BOLD))
        print(f"    {_color('P1', BOLD)}  Antivirus exclusions   (faster dev/builds)")
        print(f"    {_color('P2', BOLD)}  Service tuning         (cut background load)")
        print(_color("  INFO", BOLD))
        print(f"    {_color('I1', BOLD)}  View recent activity log")
        print(f"    {_color('I2', BOLD)}  Background run history")
        print()
        print(f"    {_color('Q', BOLD)}   Quit")
        _hr()
        try:
            choice = input("  Choose a code (e.g. M1) or Q: ").strip().lower()
        except EOFError:
            return

        print()
        if choice == "m1":
            run_scan_and_fix(dry_run_clean=False)
            reclaimable = _reclaimable_mb()  # refresh after a possible cleanup
        elif choice == "m2":
            free_ram_now(load_config())
        elif choice == "m3":
            run_startup_manager()
        elif choice == "a1":
            run_settings()
        elif choice == "a2":
            if state == "enabled":
                disable_scheduler()
            else:
                enable_scheduler()
        elif choice == "a3":
            run_restart_settings(load_config())
        elif choice == "p1":
            run_defender_manager()
        elif choice == "p2":
            run_service_manager()
        elif choice == "i1":
            view_log()
        elif choice == "i2":
            view_history()
        elif choice in ("q", ""):
            print("  Goodbye.")
            return
        else:
            print("  Unrecognized choice.")

        try:
            input("\n  Press Enter to return to the menu... ")
        except EOFError:
            return


def main() -> None:
    global INTERACTIVE
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--settings", action="store_true")
    parser.add_argument("--free-ram", action="store_true")
    parser.add_argument("--startup", action="store_true")
    parser.add_argument("--defender", action="store_true")
    parser.add_argument("--services", action="store_true")
    parser.add_argument("--scheduled-restart", action="store_true")
    parser.add_argument("--install-scheduler", action="store_true")
    parser.add_argument("--uninstall-scheduler", action="store_true")
    parser.add_argument("--idle", type=int, default=DEFAULT_IDLE_MINUTES)
    parser.add_argument("--time", default=DEFAULT_DAILY_TIME)
    args = parser.parse_args()
    _rotate_log()  # keep the log file from growing without bound

    if args.auto:
        run_auto()
        return
    if args.scheduled_restart:
        run_scheduled_restart()
        return

    _init_colors()
    if args.install_scheduler:
        install_scheduler(args.idle, args.time)
        return
    if args.uninstall_scheduler:
        uninstall_scheduler()
        return
    if args.settings:
        INTERACTIVE = True
        run_settings()
        return
    if args.free_ram:
        INTERACTIVE = True
        free_ram_now(load_config())
        return
    if args.startup:
        INTERACTIVE = True
        run_startup_manager()
        return
    if args.defender:
        INTERACTIVE = True
        run_defender_manager()
        return
    if args.services:
        INTERACTIVE = True
        run_service_manager()
        return
    if args.dry_run:
        INTERACTIVE = True
        run_scan_and_fix(dry_run_clean=True)
        return

    # Default (double-click): the single, menu-driven entry point.
    INTERACTIVE = True
    run_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Interrupted by user.")
    except Exception as exc:  # noqa: BLE001
        print(f"\n  [FATAL] Unexpected error: {exc}")
    finally:
        if INTERACTIVE and _FINAL_WAIT:
            print()
            _hr()
            try:
                input("  Press Enter to close this window... ")
            except EOFError:
                time.sleep(FINAL_PAUSE_SECONDS)
