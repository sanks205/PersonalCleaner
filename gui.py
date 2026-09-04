"""PersonalCleaner — Windows 11 / WinUI 3 style UI (PyQt6).

This is a full rewrite of the interface using PyQt6 with a Fluent / WinUI 3
look (solid neutrals, single blue accent, rounded controls, navigation view
with collapse). The engine (quick_fix.py) is unchanged.
"""
import sys
import os
import base64
import winreg
from datetime import datetime

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import psutil
import quick_fix as qf

COMMERCIAL = qf.COMMERCIAL
licensing = qf.licensing
MB = 1024 * 1024

# --------------------------------------------------------------------------- #
# Theme tokens (Fluent / Windows 11)
# --------------------------------------------------------------------------- #
LIGHT = {
    "app_bg": "#F3F3F3", "surface": "#FFFFFF", "surface_alt": "#FAFAFA",
    "nav_bg": "#F7F7F7", "text": "#1B1B1B", "text_secondary": "#5C5C5C",
    "border": "#E0E0E0", "border_strong": "#C8C8C8",
    "accent": "#0F6CBD", "accent_hover": "#115EA3", "accent_pressed": "#0C3B5E",
    "on_accent": "#FFFFFF", "selected_bg": "#D6E9FB", "hover_bg": "#EDEDED",
    "disabled_bg": "#F0F0F0", "disabled_text": "#A0A0A0",
    "success": "#107C10", "warning": "#9D5D00", "error": "#C42B1C",
}
DARK = {
    "app_bg": "#1F1F1F", "surface": "#2B2B2B", "surface_alt": "#252525",
    "nav_bg": "#232323", "text": "#FFFFFF", "text_secondary": "#B0B0B0",
    "border": "#3B3B3B", "border_strong": "#4A4A4A",
    "accent": "#378CF0", "accent_hover": "#4CC2FF", "accent_pressed": "#2A8DEB",
    "on_accent": "#FFFFFF", "selected_bg": "#26405C", "hover_bg": "#383838",
    "disabled_bg": "#2A2A2A", "disabled_text": "#6A6A6A",
    "success": "#92C353", "warning": "#FDE300", "error": "#F1707B",
}
TOK = dict(LIGHT)
CUR_THEME = "light"


def set_theme(name):
    global TOK, CUR_THEME
    CUR_THEME = name
    TOK = dict(DARK if name == "dark" else LIGHT)


def _system_theme():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as k:
            return "light" if winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 1 else "dark"
    except Exception:
        return "light"


def _res(name):
    if getattr(sys, "_MEIPASS", None):
        p = os.path.join(sys._MEIPASS, name)
        if os.path.exists(p):
            return p
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


# Checkmark glyph used inside the checked checkbox indicator.
_CHECK_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' "
    "viewBox='0 0 12 12'><path d='M1.5 6.2 L4.6 9.3 L10.5 2.5' "
    "fill='none' stroke='white' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round'/></svg>"
)
CHECK_URI = "url(data:image/svg+xml;base64," + base64.b64encode(_CHECK_SVG.encode()).decode() + ")"

QSS = """
QWidget { color: @TEXT@; background: transparent; }
QMainWindow, #Central { background: @APP_BG@; }
QScrollArea { background: transparent; border: none; }

#NavPane { background: @NAV_BG@; border-right: 1px solid @BORDER@; }

#Brand { font-size: 16px; font-weight: 700; color: @TEXT@; }
#NavGroup { font-size: 11px; font-weight: 700; color: @TEXT_SECONDARY@; padding: 10px 14px 4px 14px; }

NavItem { background: transparent; border: none; border-radius: 6px; }
NavItem[selected="true"] { background: @SELECTED_BG@; }
NavItem:hover { background: @HOVER_BG@; }
#NavIcon { font-family: 'Segoe MDL2 Assets'; font-size: 16px; color: @TEXT_SECONDARY@; }
#NavText { font-size: 13px; color: @TEXT@; }
NavItem[selected="true"] #NavIcon { color: @ACCENT@; }
NavItem[selected="true"] #NavText { color: @ACCENT@; font-weight: 600; }
#NavBar { background: @ACCENT@; border-radius: 1px; }

QPushButton { font-family: 'Segoe UI'; font-size: 13px; border-radius: 6px; padding: 9px 18px; border: 1px solid transparent; }
QPushButton[kind="accent"] { background: @ACCENT@; color: @ON_ACCENT@; border: none; }
QPushButton[kind="accent"]:hover { background: @ACCENT_HOVER@; }
QPushButton[kind="accent"]:pressed { background: @ACCENT_PRESSED@; }
QPushButton[kind="accent"]:disabled { background: @DISABLED_BG@; color: @DISABLED_TEXT@; }
QPushButton[kind="default"] { background: @SURFACE@; color: @TEXT@; border: 1px solid @BORDER_STRONG@; }
QPushButton[kind="default"]:hover { background: @HOVER_BG@; }
QPushButton[kind="default"]:pressed { background: @BORDER@; }
QPushButton[kind="default"]:disabled { color: @DISABLED_TEXT@; border-color: @BORDER@; }
QPushButton[kind="subtle"] { background: transparent; color: @TEXT@; border: none; }
QPushButton[kind="subtle"]:hover { background: @HOVER_BG@; }
QPushButton[kind="subtle"]:pressed { background: @BORDER@; }
QPushButton[kind="subtle"]:disabled { color: @DISABLED_TEXT@; }
QPushButton[kind="icon"] { background: transparent; border: none; border-radius: 6px; padding: 0; }
QPushButton[kind="icon"]:hover { background: @HOVER_BG@; }
QPushButton[kind="icon"]:pressed { background: @BORDER@; }
QPushButton:focus { outline: none; }

#PageTitle { font-size: 26px; font-weight: 700; color: @TEXT@; }
#PageSub { font-size: 13px; color: @TEXT_SECONDARY@; }
#SectionLabel { font-size: 13px; font-weight: 600; color: @TEXT@; }
#Card { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 10px; }
#CardTitle { font-size: 15px; font-weight: 700; color: @TEXT@; }
#StatIcon { font-family: 'Segoe MDL2 Assets'; font-size: 20px; color: @ACCENT@; }
#StatValue { font-size: 22px; font-weight: 700; color: @TEXT@; }
#StatLabel { font-size: 12px; color: @TEXT_SECONDARY@; }

QPlainTextEdit, QTextEdit { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 8px; color: @TEXT@; padding: 10px; font-family: 'Segoe UI'; font-size: 12px; }
QPlainTextEdit:focus, QTextEdit:focus { border: 1px solid @ACCENT@; }

QLineEdit, QSpinBox, QTimeEdit { background: @SURFACE@; border: 1px solid @BORDER_STRONG@; border-radius: 6px; padding: 7px 10px; color: @TEXT@; font-size: 13px; }
QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus { border: 1px solid @ACCENT@; }
QLineEdit:read-only { background: @SURFACE_ALT@; color: @TEXT_SECONDARY@; }

QCheckBox { spacing: 10px; color: @TEXT@; font-size: 13px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid @BORDER_STRONG@; border-radius: 3px; background: @SURFACE@; }
QCheckBox::indicator:hover { border: 1px solid @ACCENT@; }
QCheckBox::indicator:checked { background: @ACCENT@; border: 1px solid @ACCENT@; image: @CHECK@; }
QCheckBox::indicator:disabled { background: @DISABLED_BG@; border: 1px solid @BORDER@; }

QTableWidget { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 8px; gridline-color: @BORDER@; font-size: 13px; }
QHeaderView::section { background: @SURFACE_ALT@; color: @TEXT_SECONDARY@; border: none; border-bottom: 1px solid @BORDER@; border-right: 1px solid @BORDER@; padding: 9px 10px; font-weight: 600; }
QTableWidget::item { padding: 7px 10px; border: none; border-right: 1px solid @BORDER@; border-bottom: 1px solid @BORDER@; }
QTableWidget::item:selected { background: @SELECTED_BG@; color: @TEXT@; }
QTableWidget::item:focus { border: none; }

QMenu { background: @SURFACE@; color: @TEXT@; border: 1px solid @BORDER@; border-radius: 8px; padding: 6px; }
QMenu::item { padding: 8px 22px 8px 14px; border-radius: 4px; background: transparent; color: @TEXT@; }
QMenu::item:selected { background: @SELECTED_BG@; color: @TEXT@; }
QMenu::item:disabled { color: @DISABLED_TEXT@; }
QMenu::separator { height: 1px; background: @BORDER@; margin: 4px 8px; }

QTabWidget::pane { border: none; background: transparent; top: 1px; }
QTabBar::tab { background: transparent; color: @TEXT_SECONDARY@; padding: 12px 18px; border: none; border-bottom: 2px solid transparent; font-size: 13px; }
QTabBar::tab:selected { color: @ACCENT@; border-bottom: 2px solid @ACCENT@; font-weight: 600; }
QTabBar::tab:hover { color: @TEXT@; }

QComboBox { background: @SURFACE@; border: 1px solid @BORDER_STRONG@; border-radius: 6px; padding: 7px 10px; color: @TEXT@; font-size: 13px; }
QComboBox:hover { border: 1px solid @ACCENT@; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 6px; selection-background-color: @SELECTED_BG@; color: @TEXT@; }

#ToggleLabel { font-size: 13px; color: @TEXT@; }

#OptResult { font-size: 14px; color: @TEXT@; }
#OptResultGood { font-size: 14px; color: @SUCCESS@; font-weight: 600; }
#ProStatus { font-size: 14px; color: @TEXT@; }
#ProStatusGood { font-size: 14px; color: @SUCCESS@; font-weight: 700; }

QScrollBar:vertical { background: transparent; width: 11px; }
QScrollBar::handle:vertical { background: @BORDER_STRONG@; border-radius: 6px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: @TEXT_SECONDARY@; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 11px; }
QScrollBar::handle:horizontal { background: @BORDER_STRONG@; border-radius: 6px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


def _check_png_uri():
    """Draw a white checkmark as a PNG data URI (no SVG plugin needed)."""
    try:
        from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
        from PyQt6.QtCore import Qt, QBuffer, QIODevice
        pm = QPixmap(16, 16)
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("white"))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawLine(3, 9, 7, 13)
        p.drawLine(7, 13, 13, 4)
        p.end()
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pm.save(buf, "PNG")
        data = bytes(buf.data())
        return "url(data:image/png;base64," + base64.b64encode(data).decode() + ")"
    except Exception:
        return "none"


def build_qss():
    q = QSS
    for k, v in TOK.items():
        q = q.replace("@" + k.upper() + "@", v)
    q = q.replace("@CHECK@", _check_png_uri())
    return q


def apply_theme(app=None):
    if app is None:
        app = QApplication.instance()
    app.setStyleSheet(build_qss())


# --------------------------------------------------------------------------- #
# Custom widgets
# --------------------------------------------------------------------------- #
class StartupTable(QTableWidget):
    """QTableWidget that keeps its column widths at fixed ratios on resize."""

    def __init__(self, rows, cols, parent=None):
        super().__init__(rows, cols, parent)
        self._ratio_cb = None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._ratio_cb:
            self._ratio_cb()


class FluentButton(QPushButton):
    def __init__(self, text="", kind="accent", parent=None):
        super().__init__(text, parent)
        self.setProperty("kind", kind)
        self.setMinimumHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


def IconButton(char, tooltip=None, size=36):
    b = QPushButton()
    b.setFixedSize(size, size)
    b.setProperty("kind", "icon")
    b.setFont(QFont("Segoe MDL2 Assets", 16))
    b.setText(char)
    if tooltip:
        b.setToolTip(tooltip)
    return b


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")


class NavItem(QWidget):
    clicked = pyqtSignal()

    def __init__(self, icon, text, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._compact = False
        self._selected = False
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(12)
        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setObjectName("NavIcon")
        self.icon_lbl.setFont(QFont("Segoe MDL2 Assets", 16))
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.icon_lbl)
        self.text_lbl = QLabel(text)
        self.text_lbl.setObjectName("NavText")
        lay.addWidget(self.text_lbl)
        lay.addStretch(1)
        self.bar = QFrame(self)
        self.bar.setObjectName("NavBar")
        self.bar.setFixedWidth(3)
        self.bar.setFixedHeight(24)
        self.bar.move(0, 8)
        self.bar.hide()

    def set_selected(self, on):
        self._selected = on
        self.setProperty("selected", "true" if on else "false")
        self.bar.setVisible(on)
        acc = TOK["accent"]
        tcol = acc if on else TOK["text"]
        icol = acc if on else TOK["text_secondary"]
        self.text_lbl.setStyleSheet(
            f"color: {tcol}; font-weight: {'600' if on else '400'};"
        )
        self.icon_lbl.setStyleSheet(f"color: {icol};")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_compact(self, on):
        self._compact = on
        if on:
            self.text_lbl.hide()
            self.layout().setContentsMargins(24, 0, 24, 0)
        else:
            self.text_lbl.show()
            self.layout().setContentsMargins(12, 0, 12, 0)

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)


class ToggleTrack(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self._checked = False
        self._hover = False

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._checked:
            col = TOK["accent"]
        elif self._hover:
            col = TOK["hover_bg"]
        else:
            col = TOK["border_strong"]
        p.setBrush(QColor(col))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 44, 24, 12, 12)
        kx = 23 if self._checked else 4
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(kx, 3, 18, 18)

    def mousePressEvent(self, e):
        self.setChecked(not self._checked)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def setChecked(self, v):
        if self._checked != v:
            self._checked = v
            self.update()
            self.toggled.emit(v)

    def isChecked(self):
        return self._checked


class ToggleSwitch(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.track = ToggleTrack()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(self.track)
        if text:
            self.label = QLabel(text)
            self.label.setObjectName("ToggleLabel")
            lay.addWidget(self.label)
        self.toggled = self.track.toggled

    def setChecked(self, v):
        self.track.setChecked(v)

    def isChecked(self):
        return self.track.isChecked()


class FluentCheckBox(QCheckBox):
    """Checkbox that draws its own indicator so the selected state is always clear."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        box = QRect(1, (r.height() - 18) // 2, 18, 18)
        checked = self.isChecked()
        enabled = self.isEnabled()
        if not enabled:
            p.setBrush(QColor(TOK["disabled_bg"]))
            p.setPen(QPen(QColor(TOK["border"])))
        elif checked:
            p.setBrush(QColor(TOK["accent"]))
            p.setPen(QPen(QColor(TOK["accent"])))
        else:
            p.setBrush(QColor(TOK["surface"]))
            p.setPen(QPen(QColor(TOK["border_strong"])))
        p.drawRoundedRect(box, 4, 4)
        if checked:
            pen = QPen(QColor("white"), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawLine(box.left() + 5, box.top() + 9, box.left() + 8, box.top() + 12)
            p.drawLine(box.left() + 8, box.top() + 12, box.left() + 13, box.top() + 5)
        tr = QRect(box.right() + 10, 0, r.width() - box.right() - 12, r.height())
        p.setPen(QColor(TOK["text"] if enabled else TOK["disabled_text"]))
        p.setFont(self.font())
        p.drawText(
            tr,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.text(),
        )


class Toast(QWidget):
    _ICONS = {"success": "\uE73E", "info": "\uE946", "warning": "\uE7BA", "error": "\uE783"}
    _COLORS = {"success": "success", "info": "accent", "warning": "warning", "error": "error"}

    def __init__(self, parent, text, kind):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 11, 14, 11)
        lay.setSpacing(10)
        icon = QLabel(self._ICONS.get(kind, "\uE946"))
        icon.setFont(QFont("Segoe MDL2 Assets", 14))
        c = TOK[self._COLORS.get(kind, "accent")]
        icon.setStyleSheet(f"color: {c}")
        msg = QLabel(text)
        msg.setStyleSheet(f"color: {TOK['text']}")
        msg.setWordWrap(True)
        lay.addWidget(icon)
        lay.addWidget(msg)
        self.setStyleSheet(
            f"background: {TOK['surface']}; border: 1px solid {TOK['border']}; "
            f"border-left: 3px solid {c}; border-radius: 8px;"
        )
        self.adjustSize()

    @classmethod
    def notify(cls, parent, text, kind="info", timeout=3200):
        t = cls(parent, text, kind)
        pr = parent.rect()
        t.move(pr.width() - t.width() - 24, pr.height() - t.height() - 24)
        t.show()
        QTimer.singleShot(timeout, t.deleteLater)


class Splash(QSplashScreen):
    def __init__(self, on_done):
        self._pix = QPixmap(460, 300)
        self._prog = 0
        self._on_done = on_done
        super().__init__(self._pix, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        screen = QApplication.primaryScreen()
        if screen:
            self.move(screen.availableGeometry().center() - self.rect().center())
        self._draw()
        self.show()
        self.raise_()
        QApplication.processEvents()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(28)

    def _draw(self):
        p = QPainter(self._pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(0, 0, 460, 300, QColor(TOK["app_bg"]))
        p.setBrush(QColor(TOK["surface"]))
        p.setPen(QPen(QColor(TOK["border"]), 1))
        p.drawRoundedRect(30, 30, 400, 240, 14, 14)
        ic = QIcon(_res("icon.ico")).pixmap(56, 56)
        p.drawPixmap(56, 70, ic)
        p.setPen(QColor(TOK["text"]))
        p.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        p.drawText(124, 96, "Personal Cleaner")
        p.setFont(QFont("Segoe UI", 11))
        p.setPen(QColor(TOK["text_secondary"]))
        p.drawText(124, 120, "Loading...")
        # circular loading spinner
        cx, cy, rad = 230, 220, 16
        p.setPen(QPen(QColor(TOK["border_strong"]), 3))
        p.drawEllipse(cx - rad, cy - rad, rad * 2, rad * 2)
        pen = QPen(QColor(TOK["accent"]), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        ang = (self._prog * 13) % 360
        p.drawArc(cx - rad, cy - rad, rad * 2, rad * 2, ang * 16, 280 * 16)
        self.setPixmap(self._pix)

    def _tick(self):
        self._prog += 5
        if self._prog >= 100:
            self._timer.stop()
            self._on_done()
            self.close()
            return
        self._draw()


class Worker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn = fn
        self.args = args

    def run(self):
        try:
            self.finished.emit(self.fn(*self.args))
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))


# --------------------------------------------------------------------------- #
# Main application
# --------------------------------------------------------------------------- #
class PCApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = qf.load_config()
        self._tray = None  # init early so closeEvent never sees missing attr
        self.setWindowTitle("Personal Cleaner")
        self.setWindowIcon(QIcon(_res("icon.ico")))
        self.resize(960, 620)
        self.setMinimumSize(920, 560)
        # Center the window on screen (so it doesn't feel huge on small laptops)
        try:
            scr = QApplication.primaryScreen()
            if scr:
                geo = scr.availableGeometry()
                x = (geo.width() - self.width()) // 2
                y = (geo.height() - self.height()) // 2
                self.move(geo.x() + x, geo.y() + y)
        except Exception:
            pass
        self.theme_choice = self.cfg.get("theme", "system")
        eff = _system_theme() if self.theme_choice == "system" else self.theme_choice
        set_theme(eff)
        apply_theme()

        self._splash = Splash(self._on_splash_done)
        try:
            self._splash.show()
            self._splash.raise_()
            self._splash.activateWindow()
            QApplication.processEvents()
        except Exception:
            pass

        self._current = "Dashboard"
        self._collapsed = False
        self.pages = {}
        self.nav_items = {}
        self._recolorables = []
        self.start_items = []
        self._workers = []
        self._nav_anim = None
        self._ready = False

        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self._build_nav()
        QApplication.instance().processEvents()
        h.addWidget(self.nav, 0)
        self.content = QStackedWidget()
        h.addWidget(self.content, 1)

        self._build_dashboard()
        self._build_clean()
        self._build_optimize()
        self._build_startup()
        self._build_settings()
        self._build_pro()
        QApplication.instance().processEvents()
        self._recolorables.append(self.notif_toggle.track)

        # ---- tray icon (hidden-app mode, like Laragon) -------------------- #
        # Created after config load; _ensure_tray is the single creator
        if self.cfg.get("tray_on_close", False):
            try:
                self._ensure_tray()
            except Exception:
                self._tray = None

        self.show_page("Dashboard")
        QApplication.instance().processEvents()
        self._refresh_stats()
        QApplication.instance().processEvents()

        for i, name in enumerate(
            ["Dashboard", "Clean", "Optimize", "Startup", "Settings", "Pro"], start=1
        ):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self).activated.connect(
                lambda n=name: self.show_page(n)
            )
        QApplication.instance().processEvents()
        self._ready = True

    # ---- navigation ------------------------------------------------------ #
    def _build_nav(self):
        self.nav = QFrame()
        self.nav.setObjectName("NavPane")
        self.nav.setFixedWidth(260)
        lay = QVBoxLayout(self.nav)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(12, 14, 12, 10)
        hdr.setSpacing(10)
        self.btn_collapse = IconButton("\uE700", "Collapse / expand", 36)
        self.btn_collapse.clicked.connect(self._toggle_nav)
        self.lbl_brand = QLabel("Personal Cleaner")
        self.lbl_brand.setObjectName("Brand")
        hdr.addWidget(self.btn_collapse)
        hdr.addWidget(self.lbl_brand)
        hdr.addStretch(1)
        lay.addLayout(hdr)

        self.lbl_group_main = QLabel("MAIN")
        self.lbl_group_main.setObjectName("NavGroup")
        lay.addWidget(self.lbl_group_main)
        self._add_nav("Dashboard", "\uE80F", "Dashboard")
        self._add_nav("Clean", "\uE74D", "Clean")
        self._add_nav("Optimize", "\uE964", "Optimize")
        self._add_nav("Startup", "\uE7E8", "Startup")

        lay.addStretch(1)

        self.lbl_group_app = QLabel("APP")
        self.lbl_group_app.setObjectName("NavGroup")
        lay.addWidget(self.lbl_group_app)
        self._add_nav("Settings", "\uE713", "Settings")
        self._add_nav("Pro", "\uE735", "Pro")
        lay.addSpacing(10)

    def _add_nav(self, name, icon, label):
        item = NavItem(icon, label)
        item.clicked.connect(lambda n=name: self.show_page(n))
        self.nav.layout().addWidget(item)
        self.nav_items[name] = item

    def show_page(self, name):
        page = self.pages.get(name)
        if not page:
            return
        self.content.setCurrentWidget(page)
        for n, it in self.nav_items.items():
            it.set_selected(n == name)
        self._current = name

    def _toggle_nav(self):
        self._collapsed = not self._collapsed
        anim = QVariantAnimation(self)
        anim.setDuration(220)
        anim.setStartValue(self.nav.width())
        anim.setEndValue(64 if self._collapsed else 260)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(self._on_nav_anim)
        anim.start()
        self._nav_anim = anim

    def _on_nav_anim(self, v):
        self.nav.setFixedWidth(int(v))
        show = int(v) > 150
        self.lbl_brand.setVisible(show)
        self.lbl_group_main.setVisible(show)
        self.lbl_group_app.setVisible(show)
        for it in self.nav_items.values():
            if getattr(it, "_compact", False) != self._collapsed:
                it.set_compact(self._collapsed)

    # ---- page scaffolding ------------------------------------------------ #
    def _page(self, title, sub=None):
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(18)
        t = QLabel(title)
        t.setObjectName("PageTitle")
        v.addWidget(t)
        if sub:
            s = QLabel(sub)
            s.setObjectName("PageSub")
            v.addWidget(s)
        sc.setWidget(root)
        return sc, root, v

    def _add_page(self, name, widget):
        self.content.addWidget(widget)
        self.pages[name] = widget

    def _stat_card(self, icon, value, label):
        card = Card()
        card.setMinimumHeight(96)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)
        ic = QLabel(icon)
        ic.setObjectName("StatIcon")
        ic.setFont(QFont("Segoe MDL2 Assets", 20))
        val = QLabel(value)
        val.setObjectName("StatValue")
        lab = QLabel(label)
        lab.setObjectName("StatLabel")
        lay.addWidget(ic)
        lay.addWidget(val)
        lay.addWidget(lab)
        card.value_label = val
        return card

    # ---- Dashboard ------------------------------------------------------- #
    def _build_dashboard(self):
        sc, root, v = self._page(
            "Dashboard", "Overview of your system cleanliness and quick actions."
        )
        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.stat_junk = self._stat_card("\uE74D", "—", "Junk to clean")
        self.stat_ram = self._stat_card("\uE945", "—", "Free RAM")
        self.stat_start = self._stat_card("\uE7E8", "—", "Startup items")
        cards.addWidget(self.stat_junk)
        cards.addWidget(self.stat_ram)
        cards.addWidget(self.stat_start)
        v.addLayout(cards)

        btns = QHBoxLayout()
        btns.setSpacing(12)
        self.btn_scan = FluentButton("Scan", "accent")
        self.btn_scan.clicked.connect(self._scan)
        self.btn_clean = FluentButton("Clean now", "default")
        self.btn_clean.clicked.connect(self._clean)
        self.btn_clean.setEnabled(False)
        btns.addWidget(self.btn_scan)
        btns.addWidget(self.btn_clean)
        btns.addStretch(1)
        v.addLayout(btns)

        lab = QLabel("Activity")
        lab.setObjectName("SectionLabel")
        v.addWidget(lab)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(160)
        v.addWidget(self.log, 1)
        clear = FluentButton("Clear log", "default")
        clear.setMinimumHeight(32)
        clear.clicked.connect(lambda: self.log.clear())
        hclear = QHBoxLayout()
        hclear.addWidget(clear)
        hclear.addStretch(1)
        v.addLayout(hclear)
        self._add_page("Dashboard", sc)

    # ---- Clean ----------------------------------------------------------- #
    def _build_clean(self):
        sc, root, v = self._page(
            "Clean", "Choose what to clean, then preview or run a cleanup."
        )
        lab = QLabel("Categories")
        lab.setObjectName("SectionLabel")
        v.addWidget(lab)
        grid = QVBoxLayout()
        grid.setSpacing(10)
        self.clean_boxes = {}
        for key, desc in qf.CLEANUP_CATEGORIES:
            cb = FluentCheckBox(desc.strip())
            cb.setChecked(bool(self.cfg["cleanup"].get(key)))
            cb.stateChanged.connect(lambda st, k=key, cb=cb: self._set_cat(k, cb, st))
            grid.addWidget(cb)
            self.clean_boxes[key] = cb
            self._recolorables.append(cb)
        v.addLayout(grid)

        row = QHBoxLayout()
        row.setSpacing(10)
        ml = QLabel("Minimum file age (hours):")
        ml.setObjectName("SectionLabel")
        self.min_age = QSpinBox()
        self.min_age.setRange(0, 8760)
        self.min_age.setValue(int(self.cfg.get("min_age_hours", qf.MIN_AGE_HOURS)))
        self.min_age.setFixedWidth(90)
        save_age = FluentButton("Save", "default")
        save_age.clicked.connect(self._save_min_age)
        row.addWidget(ml)
        row.addWidget(self.min_age)
        row.addSpacing(8)
        row.addWidget(save_age)
        row.addStretch(1)
        v.addLayout(row)

        btns = QHBoxLayout()
        btns.setSpacing(12)
        self.btn_preview = FluentButton("Preview", "default")
        self.btn_preview.clicked.connect(self._preview)
        self.btn_cleannow = FluentButton("Clean now", "accent")
        self.btn_cleannow.clicked.connect(self._clean)
        btns.addWidget(self.btn_preview)
        btns.addWidget(self.btn_cleannow)
        btns.addStretch(1)
        v.addLayout(btns)

        lab2 = QLabel("Output")
        lab2.setObjectName("SectionLabel")
        v.addWidget(lab2)
        self.clean_log = QPlainTextEdit()
        self.clean_log.setReadOnly(True)
        self.clean_log.setMinimumHeight(140)
        v.addWidget(self.clean_log, 1)
        clear_c = FluentButton("Clear log", "default")
        clear_c.setMinimumHeight(32)
        clear_c.clicked.connect(lambda: self.clean_log.clear())
        hclear = QHBoxLayout()
        hclear.addWidget(clear_c)
        hclear.addStretch(1)
        v.addLayout(hclear)
        self._add_page("Clean", sc)

    def _set_cat(self, key, cb, state):
        self.cfg["cleanup"][key] = (state == Qt.CheckState.Checked.value)

    def _save_min_age(self):
        self.cfg["min_age_hours"] = self.min_age.value()
        self._persist()
        Toast.notify(self, "Minimum age saved.", "success")

    def _estimate_total(self):
        total = 0
        for key, _ in qf.CLEANUP_CATEGORIES:
            if self.cfg["cleanup"].get(key):
                try:
                    total += qf.estimate_category(key, self.cfg["min_age_hours"])
                except Exception:
                    pass
        return total

    def _preview(self):
        self._set_busy(self.btn_preview, "Scanning...")
        self._log_clean("Previewing...")
        self._run_async(
            self._estimate_total,
            lambda total: (
                self._set_busy(self.btn_preview, "Preview", False),
                self._log_clean(f"Preview: would free {self._fmt(total)}."),
                self._notify(f"Preview: {self._fmt(total)}.", "info"),
            ),
        )

    # ---- Optimize -------------------------------------------------------- #
    def _build_optimize(self):
        sc, root, v = self._page(
            "Optimize", "Free up cached RAM to improve responsiveness."
        )
        self.btn_free = FluentButton("Free RAM now", "accent")
        self.btn_free.setToolTip(
            "Purges the standby memory list (cached file data). Safe; may need "
            "admin rights for the full effect."
        )
        self.btn_free.clicked.connect(self._free_ram)
        v.addWidget(self.btn_free)

        self.opt_card = Card()
        self.opt_card.setMinimumHeight(90)
        ol = QVBoxLayout(self.opt_card)
        ol.setContentsMargins(18, 16, 18, 16)
        ol.setSpacing(6)
        self.opt_result = QLabel(
            'Click "Free RAM now" to trim standby memory and reclaim cached RAM.'
        )
        self.opt_result.setObjectName("OptResult")
        self.opt_result.setWordWrap(True)
        ol.addWidget(self.opt_result)
        v.addWidget(self.opt_card)
        v.addStretch(1)
        self._add_page("Optimize", sc)

    def _free_ram(self):
        self._set_busy(self.btn_free, "Working...")
        before = psutil.virtual_memory().available

        def work():
            return qf.memory_trim(purge_standby=True, empty_working_sets=False)

        def done(res):
            self._set_busy(self.btn_free, "Free RAM now", False)
            freed = res.get("freed", 0)
            after = res.get("after", 0)
            if res.get("denied"):
                self.opt_result.setText(
                    "Couldn't trim — admin rights needed for the full effect.\n"
                    f"Available RAM: {self._fmt(after)}"
                )
                self.opt_result.setObjectName("OptResult")
            else:
                self.opt_result.setText(
                    f"Freed {self._fmt(freed)} of RAM.\nAvailable now: {self._fmt(after)}"
                )
                self.opt_result.setObjectName("OptResultGood")
            self.opt_result.style().unpolish(self.opt_result)
            self.opt_result.style().polish(self.opt_result)
            self._refresh_stats()
            self._notify(f"Freed {self._fmt(freed)} RAM.", "success")

        self._run_async(work, done)

    # ---- Startup --------------------------------------------------------- #
    def _build_startup(self):
        sc, root, v = self._page(
            "Startup",
            "Programs that launch at sign-in. Turn off unneeded ones for a faster boot.",
        )
        self.start_tree = StartupTable(0, 4)
        self.start_tree.setHorizontalHeaderLabels(
            ["Name", "Publisher", "Status", "Impact"]
        )
        self.start_tree.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.start_tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.start_tree.horizontalHeader().setMinimumSectionSize(90)
        self.start_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.start_tree.customContextMenuRequested.connect(self._startup_menu)
        self.start_tree.doubleClicked.connect(self._startup_toggle_sel)
        self.start_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.start_tree.setShowGrid(False)
        self.start_tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.start_tree.verticalHeader().setVisible(False)
        self.start_tree.setAlternatingRowColors(False)
        self.start_tree._ratio_cb = self._apply_startup_ratios
        v.addWidget(self.start_tree, 1)
        QTimer.singleShot(0, self._apply_startup_ratios)

        btns = QHBoxLayout()
        btns.setSpacing(12)
        self.btn_refresh = FluentButton("Refresh", "default")
        self.btn_refresh.clicked.connect(self._refresh_startup)
        self.btn_enable = FluentButton("Enable", "default")
        self.btn_enable.clicked.connect(lambda: self._toggle_startup(True))
        self.btn_disable = FluentButton("Disable", "default")
        self.btn_disable.clicked.connect(lambda: self._toggle_startup(False))
        btns.addWidget(self.btn_refresh)
        btns.addWidget(self.btn_enable)
        btns.addWidget(self.btn_disable)
        btns.addStretch(1)
        v.addLayout(btns)

        hint = QLabel("Double-click a row to toggle it. Right-click for options.")
        hint.setObjectName("PageSub")
        v.addWidget(hint)
        self._add_page("Startup", sc)

    def _apply_startup_ratios(self):
        t = self.start_tree
        if not t or t.columnCount() == 0:
            return
        vis = [c for c in range(t.columnCount()) if not t.isColumnHidden(c)]
        if not vis:
            return
        total = t.viewport().width()
        if total <= 0:
            return
        if len(vis) == 4:
            ratios = {0: 0.45, 1: 0.25, 2: 0.15, 3: 0.15}
        else:
            ratios = {0: 0.6, 2: 0.2, 3: 0.2}
        for c in vis:
            t.setColumnWidth(c, max(60, int(total * ratios.get(c, 0.2))))

    def _refresh_startup(self):
        try:
            items = qf.enumerate_startup()
        except Exception as e:
            self._log(f"Startup error: {e}")
            return
        self.start_items = items
        self.start_tree.setRowCount(len(items))
        for i, it in enumerate(items):
            self.start_tree.setItem(
                i, 0, QTableWidgetItem(it.get("display", it.get("name", "")))
            )
            self.start_tree.setItem(
                i, 1, QTableWidgetItem(it.get("publisher", "") or "\u2014")
            )
            status = "Enabled" if it.get("enabled") else "Disabled"
            self.start_tree.setItem(i, 2, QTableWidgetItem(status))
            impact = it.get("impact", "Not measured")
            self.start_tree.setItem(i, 3, QTableWidgetItem(impact))
            s_item = self.start_tree.item(i, 2)
            s_item.setForeground(
                QColor(TOK["success"] if it.get("enabled") else TOK["text_secondary"])
            )
            i_color = {
                "High": TOK["warning"],
                "Medium": TOK["text_secondary"],
                "Low": TOK["success"],
            }.get(impact, TOK["text_secondary"])
            self.start_tree.item(i, 3).setForeground(QColor(i_color))
        has_pub = any((it.get("publisher") or "").strip() for it in items)
        self.start_tree.setColumnHidden(1, not has_pub)
        self._apply_startup_ratios()

    def _toggle_startup(self, enable):
        sel = self.start_tree.selectedItems()
        if not sel:
            Toast.notify(self, "Select a startup item first.", "warning")
            return
        row = sel[0].row()
        it = self.start_items[row]
        if qf.set_startup_enabled(it, enable):
            self._refresh_startup()
            Toast.notify(
                self, f"{'Enabled' if enable else 'Disabled'} {it.get('display', '')}.", "success"
            )
        else:
            Toast.notify(self, "Failed — admin rights needed for system items.", "error")

    def _startup_toggle_sel(self, index):
        row = index.row()
        it = self.start_items[row]
        self._toggle_startup(not it.get("enabled"))

    def _startup_menu(self, pos):
        menu = QMenu(self)
        enable = menu.addAction("Enable")
        disable = menu.addAction("Disable")
        refresh = menu.addAction("Refresh")
        act = menu.exec(self.start_tree.viewport().mapToGlobal(pos))
        if act == enable:
            self._toggle_startup(True)
        elif act == disable:
            self._toggle_startup(False)
        elif act == refresh:
            self._refresh_startup()

    # ---- Settings -------------------------------------------------------- #
    def _build_settings(self):
        sc, root, v = self._page("Settings", "Personalize the app and manage behavior.")
        tabs = QTabWidget()

        ap = QWidget()
        al = QVBoxLayout(ap)
        al.setContentsMargins(8, 16, 8, 8)
        al.setSpacing(16)
        al.addWidget(QLabel("Theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        self.theme_combo.setCurrentText(self.theme_choice.capitalize())
        self.theme_combo.currentTextChanged.connect(self._on_theme_change)
        al.addWidget(self.theme_combo)
        al.addWidget(QLabel("System follows your Windows theme automatically."))
        al.addStretch(1)
        tabs.addTab(ap, "Appearance")

        gn = QWidget()
        gl = QVBoxLayout(gn)
        gl.setContentsMargins(8, 16, 8, 8)
        gl.setSpacing(16)
        self.notif_toggle = ToggleSwitch("Show a notification after each cleanup")
        self.notif_toggle.setChecked(bool(self.cfg.get("notifications", True)))
        self.tray_toggle = ToggleSwitch("Hide to tray when closed (runs in background)")
        self.tray_toggle.setChecked(bool(self.cfg.get("tray_on_close", False)))
        gl.addWidget(self.notif_toggle)
        gl.addWidget(self.tray_toggle)
        # Tray-hide: apply immediately when toggled (so Close hides without needing Save)
        self.tray_toggle.toggled.connect(lambda state: self._set_tray_mode(state))
        saveg = FluentButton("Save", "default")
        saveg.clicked.connect(self._save_general)
        gl.addWidget(saveg)
        # Small hint so user knows tray setting is live
        self._tray_hint = QLabel("Tip: after enabling, Close goes to the tray (^) — click the tray icon to open again.")
        self._tray_hint.setStyleSheet(f"color: {TOK['text_secondary']}; font-size: 11px;")
        self._tray_hint.setWordWrap(True)
        gl.addWidget(self._tray_hint)
        gl.addStretch(1)
        tabs.addTab(gn, "General")

        ab = QWidget()
        bl = QVBoxLayout(ab)
        bl.setContentsMargins(8, 16, 8, 8)
        bl.setSpacing(14)
        title = QLabel("Personal Cleaner")
        title.setObjectName("CardTitle")
        bl.addWidget(title)
        bl.addWidget(QLabel("A free, open-source Windows PC cleaner.\nVersion 1.0"))
        lic = FluentButton("View license", "default")
        lic.clicked.connect(self._show_license)
        bl.addWidget(lic)
        bl.addStretch(1)
        tabs.addTab(ab, "About")

        v.addWidget(tabs)
        self._add_page("Settings", sc)

    def _on_theme_change(self, text):
        self.theme_choice = text.lower()
        self.cfg["theme"] = self.theme_choice
        self._persist()
        eff = _system_theme() if self.theme_choice == "system" else self.theme_choice
        set_theme(eff)
        apply_theme()
        self._recolor_all()
        Toast.notify(self, f"Theme: {text}.", "info")

    def _save_general(self):
        self.cfg["notifications"] = self.notif_toggle.isChecked()
        self.cfg["tray_on_close"] = self.tray_toggle.isChecked()
        self._persist()
        if self.cfg["tray_on_close"]:
            self._ensure_tray()
        else:
            if self._tray:
                self._tray.hide()
                self._tray.deleteLater()
                self._tray = None
        Toast.notify(self, "Settings saved.", "success")

    def _show_license(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("License")
        dlg.setMinimumSize(560, 460)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(12, 12, 12, 12)
        txt = QPlainTextEdit()
        txt.setReadOnly(True)
        try:
            with open(_res("LICENSE"), "r", encoding="utf-8") as f:
                txt.setPlainText(f.read())
        except Exception:
            txt.setPlainText("License file not found.")
        lay.addWidget(txt)
        close = FluentButton("Close", "subtle")
        close.clicked.connect(dlg.accept)
        lay.addWidget(close)
        dlg.exec()

    # ---- Pro ------------------------------------------------------------- #
    def _build_pro(self):
        sc, root, v = self._page("Pro", "Unlock the Commercial edition features.")
        self.pro_card = Card()
        self.pro_card.setMinimumHeight(80)
        pl = QVBoxLayout(self.pro_card)
        pl.setContentsMargins(18, 16, 18, 16)
        pl.setSpacing(6)
        self.pro_status = QLabel()
        self.pro_status.setObjectName("ProStatus")
        pl.addWidget(self.pro_status)
        v.addWidget(self.pro_card)

        mid_row = QHBoxLayout()
        mid_row.setSpacing(10)
        self.btn_mid = FluentButton("Get Machine ID", "default")
        self.btn_mid.clicked.connect(self._get_mid)
        self.mid_edit = QLineEdit()
        self.mid_edit.setReadOnly(True)
        mid_row.addWidget(self.btn_mid)
        mid_row.addWidget(self.mid_edit, 1)
        v.addLayout(mid_row)

        act_row = QHBoxLayout()
        act_row.setSpacing(10)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Enter license key")
        self.btn_activate = FluentButton("Activate", "accent")
        self.btn_activate.clicked.connect(self._activate)
        act_row.addWidget(self.key_edit, 1)
        act_row.addWidget(self.btn_activate)
        v.addLayout(act_row)

        sch_card = Card()
        sl = QVBoxLayout(sch_card)
        sl.setContentsMargins(18, 16, 18, 16)
        sl.setSpacing(10)
        sl.addWidget(QLabel("Background schedule"))
        self.sched_status = QLabel("Status: unknown")
        self.sched_status.setObjectName("ProStatus")
        sl.addWidget(self.sched_status)
        sched_row = QHBoxLayout()
        sched_row.setSpacing(10)
        sched_row.addWidget(QLabel("Idle (min):"))
        self.idle_spin = QSpinBox()
        self.idle_spin.setRange(1, 1440)
        self.idle_spin.setToolTip("Minutes of idle time before the background cleanup runs.")
        self.idle_spin.setValue(qf.DEFAULT_IDLE_MINUTES)
        self.idle_spin.setFixedWidth(80)
        sched_row.addWidget(self.idle_spin)
        sched_row.addWidget(QLabel("Daily time:"))
        self.daily_edit = QLineEdit(qf.DEFAULT_DAILY_TIME)
        self.daily_edit.setFixedWidth(90)
        sched_row.addWidget(self.daily_edit)
        sched_row.addStretch(1)
        sl.addLayout(sched_row)
        bts = QHBoxLayout()
        bts.setSpacing(10)
        self.btn_sched_install = FluentButton("Install", "default")
        self.btn_sched_install.clicked.connect(self._install_sched)
        self.btn_sched_uninstall = FluentButton("Uninstall", "default")
        self.btn_sched_uninstall.clicked.connect(self._uninstall_sched)
        self.btn_sched_refresh = FluentButton("Refresh", "default")
        self.btn_sched_refresh.clicked.connect(self._refresh_sched)
        bts.addWidget(self.btn_sched_install)
        bts.addWidget(self.btn_sched_uninstall)
        bts.addWidget(self.btn_sched_refresh)
        bts.addStretch(1)
        sl.addLayout(bts)
        v.addWidget(sch_card)
        v.addStretch(1)

        if not (COMMERCIAL and licensing):
            self.pro_status.setText("Commercial features are not available in this build.")
            self.btn_activate.setEnabled(False)
            self.btn_mid.setEnabled(False)
            self.btn_sched_install.setEnabled(False)
        self._add_page("Pro", sc)

    def _refresh_pro_status(self):
        if not (COMMERCIAL and licensing):
            self.pro_status.setText("Commercial features are not available in this build.")
            self.pro_status.setObjectName("ProStatus")
            return
        try:
            if licensing.is_licensed():
                self.pro_status.setText("Licensed — all Pro features unlocked.")
                self.pro_status.setObjectName("ProStatusGood")
            else:
                self.pro_status.setText("Free / locked — enter a license key to unlock Pro.")
                self.pro_status.setObjectName("ProStatus")
        except Exception:
            self.pro_status.setText("License status unknown.")
            self.pro_status.setObjectName("ProStatus")
        self.pro_status.style().unpolish(self.pro_status)
        self.pro_status.style().polish(self.pro_status)

    def _get_mid(self):
        if not (COMMERCIAL and licensing):
            return
        try:
            self.mid_edit.setText(licensing.machine_id())
            self.mid_edit.selectAll()
        except Exception as e:
            Toast.notify(self, f"Error: {e}", "error")

    def _activate(self):
        if not (COMMERCIAL and licensing):
            return
        key = self.key_edit.text().strip()
        if not key:
            Toast.notify(self, "Enter a license key first.", "warning")
            return
        try:
            st = licensing.install_key(key)
            if st.get("ok"):
                Toast.notify(self, "License activated.", "success")
            else:
                Toast.notify(self, st.get("error", "Activation failed."), "error")
        except Exception as e:
            Toast.notify(self, f"Error: {e}", "error")
        self._refresh_pro_status()

    def _refresh_sched(self):
        try:
            state = qf.scheduler_state()
        except Exception:
            state = "absent"
        labels = {
            "enabled": "Enabled",
            "disabled": "Disabled (installed)",
            "absent": "Not installed",
        }
        self.sched_status.setText(f"Status: {labels.get(state, state)}")

    def _install_sched(self):
        try:
            qf.install_scheduler(
                self.idle_spin.value(),
                self.daily_edit.text().strip() or qf.DEFAULT_DAILY_TIME,
            )
            Toast.notify(self, "Scheduler installed.", "success")
        except Exception as e:
            Toast.notify(self, f"Error: {e}", "error")
        self._refresh_sched()

    def _uninstall_sched(self):
        try:
            qf.uninstall_scheduler()
            Toast.notify(self, "Scheduler removed.", "success")
        except Exception as e:
            Toast.notify(self, f"Error: {e}", "error")
        self._refresh_sched()

    # ---- shared actions -------------------------------------------------- #
    def _scan(self):
        self._set_busy(self.btn_scan, "Scanning...")
        self._log("Scanning for junk...")

        def done(total):
            self.stat_junk.value_label.setText(self._fmt(total))
            self._set_busy(self.btn_scan, "Scan", False)
            self.btn_clean.setEnabled(True)
            self._log(f"Scan complete: {self._fmt(total)} found.")
            self._notify(f"Scan complete: {self._fmt(total)} found.", "success")

        self._run_async(self._estimate_total, done)

    def _clean(self):
        if not any(self.cfg["cleanup"].values()):
            Toast.notify(self, "Select categories to clean first (Clean tab).", "warning")
            return
        self._set_busy(self.btn_clean, "Cleaning...", True)
        self._set_busy(self.btn_cleannow, "Cleaning...", True)
        self._log("Cleaning...")
        self._log_clean("Cleaning...")

        def done(freed):
            self._set_busy(self.btn_clean, "Clean now", False)
            self._set_busy(self.btn_cleannow, "Clean now", False)
            self._log(f"Cleanup done. Freed {self._fmt(freed)}.")
            self._log_clean(f"Cleanup done. Freed {self._fmt(freed)}.")
            self._refresh_stats()
            self._refresh_startup()
            self._notify(f"Freed {self._fmt(freed)}.", "success")

        self._run_async(lambda: qf.run_cleanup(False, self.cfg), done)

    def _run_async(self, fn, done=None, err=None):
        w = Worker(fn)
        w.finished.connect(lambda v, w=w, done=done: self._on_worker_done(w, done, v))
        w.error.connect(lambda m, w=w, err=err: self._on_worker_err(w, err, m))
        self._workers.append(w)
        w.start()
        return w

    def _on_worker_done(self, w, done, v):
        try:
            if done:
                done(v)
        finally:
            self._cleanup_worker(w)

    def _on_worker_err(self, w, err, m):
        try:
            if err:
                err(m)
            else:
                self._on_error(m)
        finally:
            self._cleanup_worker(w)

    def _cleanup_worker(self, w):
        try:
            self._workers.remove(w)
        except ValueError:
            pass
        w.deleteLater()

    def _on_error(self, msg):
        self._log(f"Error: {msg}")
        Toast.notify(self, f"Error: {msg[:120]}", "error")

    def _set_busy(self, btn, text, busy=True):
        btn.setEnabled(not busy)
        btn.setText(text)

    def _persist(self):
        qf.save_config(self.cfg)

    def _refresh_stats(self, junk=None, ram=None, start=None):
        if ram is None:
            ram = psutil.virtual_memory().available
        if start is None:
            try:
                start = len(qf.enumerate_startup())
            except Exception:
                start = 0
        self.stat_ram.value_label.setText(self._fmt(ram))
        self.stat_start.value_label.setText(str(start))
        if junk is not None:
            self.stat_junk.value_label.setText(self._fmt(junk))

    def _recolor_all(self):
        for w in self._recolorables:
            w.update()
        for it in getattr(self, "nav_items", {}).values():
            it.set_selected(it._selected)
        if getattr(self, "start_tree", None):
            self._refresh_startup()

    def _log(self, msg):
        self.log.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _log_clean(self, msg):
        self.clean_log.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _notify(self, text, kind="info"):
        if kind in ("success", "info") and not self.cfg.get("notifications", True):
            return
        Toast.notify(self, text, kind)

    @staticmethod
    def _fmt(b):
        b = float(b)
        for u in ["B", "KB", "MB", "GB", "TB", "PB"]:
            if abs(b) < 1024 or u == "PB":
                if u == "B":
                    return f"{int(b)} B"
                return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} PB"

    # ---- close / tray behavior (Laragon-like: X always hides to tray) ---- #
    def closeEvent(self, event):
        # Re-read live config so toggle without restart also works
        try:
            self.cfg = qf.load_config()
        except Exception:
            pass
        cfg = getattr(self, "cfg", {})
        if cfg.get("tray_on_close", False):
            event.ignore()
            self.hide()
            # Ensure tray exists — create it here if Settings was toggled just now
            if not self._tray:
                self._ensure_tray()
            if self._tray:
                self._tray.show()
                try:
                    self._tray.showMessage(
                        "Personal Cleaner",
                        "Running in background — cleans are still active.",
                    )
                except Exception:
                    pass
        else:
            # tray mode off → quit, but keep tray visible for a moment if it existed
            if self._tray:
                self._tray.hide()
                self._tray.deleteLater()
                self._tray = None
            event.accept()

    def _show_from_tray(self):
        self.show()
        self.activateWindow()
        self.raise_()
        # Keep tray alive so next Close can hide to it again (do NOT delete)
        if self._tray:
            # ensure tray stays visible after restoring
            self._tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                       QSystemTrayIcon.ActivationReason.DoubleClick):
            self._show_from_tray()

    def _ensure_tray(self):
        """Create tray if not already present; return True if tray is ready."""
        if self._tray is not None:
            return True
        try:
            self._tray = QSystemTrayIcon(self)
            self._tray.setIcon(QIcon(_res("icon.ico")))
            _m = QMenu()
            _a = _m.addAction("Show Personal Cleaner")
            _a.triggered.connect(self._show_from_tray)
            _q = _m.addAction("Quit")
            _q.triggered.connect(QApplication.instance().quit)
            self._tray.setContextMenu(_m)
            self._tray.activated.connect(self._on_tray_activated)
            self._tray.show()
            return True
        except Exception:
            self._tray = None
            return False

    def _set_tray_mode(self, state):
        """Enable or disable hide-to-tray mode. Called when the Settings toggle changes."""
        self.cfg["tray_on_close"] = state
        self._persist()
        if state:
            self._ensure_tray()
        else:
            if self._tray:
                self._tray.hide()
                self._tray.deleteLater()
                self._tray = None

    def _on_splash_done(self):
        if not getattr(self, "_ready", False):
            QTimer.singleShot(150, self._on_splash_done)
            return
        self._refresh_stats()
        self._refresh_startup()
        self._refresh_pro_status()
        self._refresh_sched()
        # If single-instance helper exists and tray mode is ON, ensure tray is visible
        if self.cfg.get("tray_on_close", False):
            self._ensure_tray()
        self.show()
        self.activateWindow()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def _excepthook(exc_type, exc, tb):
    import traceback

    msg = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        with open(_res("crash.log"), "w", encoding="utf-8") as f:
            f.write(msg)
    except Exception:
        pass
    try:
        QMessageBox.critical(None, "Personal Cleaner - Error", msg[:3000])
    except Exception:
        pass


def main():
    # --- Headless / scheduler delegation ---
    # The Task Scheduler runs `PersonalCleaner.exe --auto` (and --scheduled-restart).
    # This build is --windowed, so that invocation MUST NOT create a window.
    # Delegate all headless flags to the engine (quick_fix.main) and exit silently.
    # This is the fix for "every 10 min a new window pops up": the scheduler must
    # run silently in the background, clean junk/RAM, and never open the GUI.
    headless_flags = {
        "--auto", "--scheduled-restart",
        "--install-scheduler", "--uninstall-scheduler",
        "--settings", "--free-ram", "--startup", "--tasks",
        "--restart-explorer", "--defender", "--services", "--dry-run",
        "--help", "-h",
    }
    # Also treat --idle / --time as headless (they accompany --install-scheduler)
    # so `PersonalCleaner.exe --install-scheduler --idle 10 --time 03:00` never pops GUI.
    for _a in sys.argv[1:]:
        key = _a.split("=")[0].lower()
        if key in headless_flags or key in ("--idle", "--time"):
            qf.main()
            return
    # Extra guard: single-instance for the GUI — if a GUI is already running
    # in the same session, don't spawn a duplicate (scheduler runs use --auto
    # and already returned above, so they never reach here).
    # NOTE: when Run as Administrator vs normal user, they are different
    # Windows sessions and don't see each other — no dedup in that case.
    try:
        from PyQt6.QtNetwork import QLocalServer, QLocalSocket  # type: ignore
        import ctypes

        def _is_admin() -> bool:
            try:
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                return False

        _sock_name = f"PersonalCleaner-GUI-singleton-{'admin' if _is_admin() else 'user'}"
        _socket = QLocalSocket()
        _socket.connectToServer(_sock_name)
        if _socket.waitForConnected(300):
            # Another GUI in same session is already running — just exit
            return
        # No existing instance — claim the slot
        global _singleton_server
        _singleton_server = QLocalServer()
        try:
            QLocalServer.removeServer(_sock_name)
        except Exception:
            pass
        _singleton_server.listen(_sock_name)
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    sys.excepthook = _excepthook
    pc = PCApp()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
