import sys
import winreg
import ctypes
import datetime
import math
import qtawesome as qta
from PyQt6.QtCore import Qt, QTimer, QRect, QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup, QPointF
from PyQt6.QtGui import (QCursor, QPainter, QColor, QBrush, QPaintEvent, 
                         QLinearGradient, QRadialGradient, QConicalGradient, QAction, QPen)
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QProgressBar, QMenu, QPushButton, QGraphicsOpacityEffect)

from app_styles import get_stylesheet
from perf_monitor import PerfMonitor
from media_monitor import MediaMonitor
from event_monitor import KeyLockMonitor
from notification_monitor import NotificationMonitor

# DWM Constants
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMSBT_DISABLE = 1
DWMWCP_ROUND = 2

class DynamicIsland(QWidget):
    def __init__(self):
        super().__init__()
        
        # Window Flags: Frameless, stay on top, tool window (no taskbar)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.accent_color = self.get_windows_accent_color()
        self.album_accent_color = QColor(0, 0, 0)
        self.gradient_phase = 0.0
        self.animation_style = "Fluid Blobs"
        self.island_style = "Default" 
        
        self.setObjectName("IslandWidget")
        self.setStyleSheet(get_stylesheet(self.accent_color))
        
        # Dimensions Constants
        self.IDLE_W, self.IDLE_H = 180, 40
        self.EXP_W, self.EXP_H = 300, 70
        self.MUSIC_W, self.MUSIC_H = 420, 40
        self.NOTIFY_W, self.NOTIFY_H = 380, 40
        
        self.current_state = "Idle"
        self.media_state = "Idle"
        self.media_title, self.media_artist = "", ""
        self.features = ["perf", "media"]
        self.current_feature_index = 1
        
        # Notification/Event queue
        self.event_title, self.event_text = "", ""
        self.revert_timer = QTimer(self); self.revert_timer.setSingleShot(True); self.revert_timer.timeout.connect(lambda: self.change_state("Idle" if self.current_state != "Hover" else "Hover"))
        
        self.setup_monitors()
        self.init_ui()
        self.setup_autostart()
        
        self.master_timer = QTimer(self); self.master_timer.timeout.connect(self.update_content); self.master_timer.start(1000)
        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self.update_animation); self.anim_timer.start(30)
        self.hit_timer = QTimer(self); self.hit_timer.timeout.connect(self.check_mouse_position); self.hit_timer.start(50)
        
        self.resize(self.IDLE_W, self.IDLE_H); self.recenter_window()
        self.anim_group = QParallelAnimationGroup()
        self.geom_anim = QPropertyAnimation(self, b"geometry"); self.geom_anim.setDuration(400); self.geom_anim.setEasingCurve(QEasingCurve.Type.OutQuart)
        self.opacity_anim = QPropertyAnimation(self.content_opacity, b"opacity"); self.opacity_anim.setDuration(400); self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutQuart)
        self.anim_group.addAnimation(self.geom_anim); self.anim_group.addAnimation(self.opacity_anim)

    def paintEvent(self, a0: QPaintEvent):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect, p_rect = self.rect(), self.rect().adjusted(1,1,-1,-1)
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(5): painter.setBrush(QColor(0, 0, 0, 20 - i*4)); painter.drawRoundedRect(rect.adjusted(i, i, -i, -i), 24, 24)
        
        clr = QColor(10, 10, 10, 180) if self.island_style == "Liquid Glass" else QColor(15, 15, 15)
        painter.setBrush(QBrush(clr)); painter.drawRoundedRect(rect, 20, 20)
        if self.island_style == "Liquid Glass":
            glint = QLinearGradient(0, 0, 0, 15); glint.setColorAt(0, QColor(255, 255, 255, 45)); glint.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(glint); painter.drawRoundedRect(rect.adjusted(2, 2, -2, -22), 18, 18)
            
        can_anim = (self.current_state in ("Hover", "Notify") and self.features[self.current_feature_index] == "media") or \
                   (self.current_state == "Idle" and self.features[self.current_feature_index] == "media" and self.media_state in ("Playing", "Paused"))
        if can_anim:
            if self.animation_style == "Glow Sweep": self.paint_glow_sweep(painter, rect)
            elif self.animation_style == "Fluid Blobs": self.paint_fluid_blobs(painter, rect)
            elif self.animation_style == "Neon Border": self.paint_neon_border(painter, rect)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor(255, 255, 255, 20), 1.2)); painter.drawRoundedRect(p_rect, 20, 20)

    def paint_glow_sweep(self, painter, rect):
        from PyQt6.QtGui import QTransform
        glow = QColor(self.album_accent_color); glow.setAlpha(180)
        gradient = QLinearGradient(0, 0, rect.width(), 0); gradient.setSpread(QLinearGradient.Spread.RepeatSpread)
        gradient.setColorAt(0.0, Qt.GlobalColor.transparent); gradient.setColorAt(0.5, glow); gradient.setColorAt(1.0, Qt.GlobalColor.transparent)
        brush = QBrush(gradient); transform = QTransform(); transform.translate(self.gradient_phase * rect.width() * 2, 0); brush.setTransform(transform)
        painter.setBrush(brush); painter.drawRoundedRect(rect, 20, 20)

    def paint_fluid_blobs(self, painter, rect):
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        glow_color = QColor(self.album_accent_color); glow_color.setAlpha(150); p = self.gradient_phase * 2 * math.pi
        x1, y1 = rect.width() * (0.2 + 0.15 * math.sin(p)), rect.height() * (0.5 + 0.25 * math.cos(p))
        g1 = QRadialGradient(x1, y1, rect.width() * 0.45); g1.setColorAt(0, glow_color); g1.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(g1); painter.drawRoundedRect(rect, 20, 20)
        x2, y2 = rect.width() * (0.8 + 0.15 * math.cos(p * 0.7)), rect.height() * (0.5 + 0.25 * math.sin(p * 1.2))
        g2 = QRadialGradient(x2, y2, rect.width() * 0.35); g2.setColorAt(0, QColor(glow_color).lighter(125)); g2.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(g2); painter.drawRoundedRect(rect, 20, 20)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def paint_neon_border(self, painter, rect):
        conical = QConicalGradient(QPointF(rect.center()), self.gradient_phase * 360)
        for i, c in enumerate(["#F00", "#FF0", "#0F0", "#0FF", "#00F", "#F0F", "#F00"]): conical.setColorAt(i/6.0, QColor(c))
        painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QBrush(conical), 2.2)); painter.drawRoundedRect(rect.adjusted(1,1,-1,-1), 20, 20)

    def update_animation(self):
        self.gradient_phase = (self.gradient_phase + 0.005) % 1.0
        if self.current_state in ("Hover", "Notify") or self.media_state in ("Playing", "Paused"): self.update()

    def get_windows_accent_color(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM")
            v, _ = winreg.QueryValueEx(key, "ColorizationColor"); winreg.CloseKey(key); return f"#{(v & 0xFFFFFF):06x}"
        except: return "#0078D7"

    def setup_autostart(self):
        try:
            # Check if running as PyInstaller bundle
            app_path = sys.executable if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{sys.argv[0]}"'
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "DynamicIsland", 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
        except Exception as e: print("Autostart error:", e)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self); self.main_layout.setContentsMargins(15, 0, 15, 0); self.main_layout.setSpacing(0)
        self.content_container = QWidget(); self.content_layout = QVBoxLayout(self.content_container); self.content_layout.setContentsMargins(0, 0, 0, 0); self.content_layout.setSpacing(0)
        self.content_opacity = QGraphicsOpacityEffect(self.content_container); self.content_container.setGraphicsEffect(self.content_opacity)
        
        self.header_widget = QWidget(); self.header_layout = QHBoxLayout(self.header_widget); self.header_layout.setContentsMargins(0, 0, 0, 0); self.header_layout.setSpacing(10)
        self.status_icon = QLabel("●"); self.status_icon.setObjectName("IconLabel"); self.status_icon.setStyleSheet(f"color: {self.accent_color};"); self.status_icon.setFixedWidth(20)
        self.status_text = QLabel(""); self.status_text.setObjectName("TitleLabel")
        self.header_layout.addWidget(self.status_icon); self.header_layout.addWidget(self.status_text)
        
        self.media_controls = QWidget(); self.media_controls_layout = QHBoxLayout(self.media_controls); self.media_controls_layout.setContentsMargins(0, 0, 0, 0); self.media_controls_layout.setSpacing(2)
        self.btn_prev = QPushButton(icon=qta.icon('mdi.skip-previous', color='white')); self.btn_play = QPushButton(icon=qta.icon('mdi.play', color='white')); self.btn_next = QPushButton(icon=qta.icon('mdi.skip-next', color='white'))
        for b in [self.btn_prev, self.btn_play, self.btn_next]: b.setObjectName("MediaButton")
        self.btn_prev.clicked.connect(self.media_monitor.prev_track); self.btn_play.clicked.connect(self.media_monitor.toggle_play_pause); self.btn_next.clicked.connect(self.media_monitor.next_track)
        for b in [self.btn_prev, self.btn_play, self.btn_next]: self.media_controls_layout.addWidget(b)
        
        self.header_layout.addStretch(); self.header_layout.addWidget(self.media_controls); self.media_controls.hide()
        self.content_layout.addWidget(self.header_widget)
        
        self.perf_widget = QWidget(); self.perf_layout = QHBoxLayout(self.perf_widget); self.perf_layout.setContentsMargins(0, 10, 0, 10)
        self.cpu_label = QLabel("CPU"); self.cpu_bar = QProgressBar(); self.ram_label = QLabel("RAM"); self.ram_bar = QProgressBar()
        for bar in [self.cpu_bar, self.ram_bar]: bar.setTextVisible(False); bar.setMaximum(100); bar.setFixedHeight(6)
        for l in [self.cpu_label, self.ram_label]: l.setObjectName("PerfLabel")
        for w in [self.cpu_label, self.cpu_bar, self.ram_label, self.ram_bar]: self.perf_layout.addWidget(w)
        self.content_layout.addWidget(self.perf_widget); self.perf_widget.hide()
        self.main_layout.addWidget(self.content_container); self.update_content()

    def setup_monitors(self):
        self.perf_monitor = PerfMonitor(parent=self); self.perf_monitor.metrics_updated.connect(self.update_perf); self.perf_monitor.start()
        self.media_monitor = MediaMonitor(self); self.media_monitor.media_updated.connect(self.update_media); self.media_monitor.start()
        self.key_monitor = KeyLockMonitor(self); self.key_monitor.lock_changed.connect(self.show_key_event); self.key_monitor.start()
        self.notif_monitor = NotificationMonitor(self); self.notif_monitor.notification_received.connect(self.show_notification); self.notif_monitor.start()

    def show_key_event(self, name, is_on):
        self.event_title = name; self.event_text = ("ENABLED" if is_on else "DISABLED")
        # Restart state to force refresh
        if self.current_state == "Notify": self.update_feature_view(); self.execute_liquid_transition()
        else: self.change_state("Notify")
        self.revert_timer.start(2500)

    def show_notification(self, app, title, text):
        self.event_title = app; self.event_text = (f"{title}: {text}" if title else text)
        if self.current_state == "Notify": self.update_feature_view(); self.execute_liquid_transition()
        else: self.change_state("Notify")
        self.revert_timer.start(3500)

    def update_content(self):
        if self.current_state == "Idle":
            feature = self.features[self.current_feature_index]
            if feature == "media" and self.media_state in ("Playing", "Paused"):
                dt = self.media_title; self.status_text.setText(dt[:22] + "..." if len(dt) > 25 else dt); self.status_icon.setText("♫")
            else:
                now = datetime.datetime.now(); ts = now.strftime("%I:%M %p").lstrip("0"); self.status_text.setText(f"{now.strftime('%a')}, {ts}"); self.status_icon.setText("●")
        self.update()

    def update_perf(self, cpu, ram):
        self.cpu_label.setText(f"CPU: {int(cpu)}%"); self.cpu_bar.setValue(int(cpu)); self.ram_label.setText(f"RAM: {int(ram)}%"); self.ram_bar.setValue(int(ram))

    def update_media(self, state, title, artist, accent_hex):
        self.media_state, self.media_title, self.media_artist = state, title, artist; self.album_accent_color = QColor(accent_hex)
        self.btn_play.setIcon(qta.icon('mdi.pause' if state == "Playing" else 'mdi.play', color='white')); self.update_content()
        if self.current_state == "Hover": self.update_feature_view()

    def update_feature_view(self):
        if self.current_state == "Idle":
            self.perf_widget.hide(); self.media_controls.hide(); self.update_content(); return
        
        if self.current_state == "Notify":
            self.perf_widget.hide(); self.media_controls.hide()
            self.status_icon.setText("⚡" if "Lock" in self.event_title else "✉")
            dt = f"{self.event_title} - {self.event_text}"; self.status_text.setText(dt[:45] + "..." if len(dt) > 48 else dt)
            return

        feature = self.features[self.current_feature_index]
        if feature == "perf":
            self.media_controls.hide(); self.perf_widget.show(); self.status_text.setText("Performance Status"); self.status_icon.setText("●")
        elif feature == "media":
            self.perf_widget.hide(); self.media_controls.show()
            if self.media_state in ("Playing", "Paused"):
                dt = f"{self.media_title} - {self.media_artist}"; self.status_text.setText(dt[:37] + "..." if len(dt) > 40 else dt); self.status_icon.setText("♫")
            else: self.status_text.setText("Music Player"); self.status_icon.setText("♫")

    def wheelEvent(self, event):
        if self.current_state == "Hover":
            delta = event.angleDelta().y()
            self.current_feature_index = (self.current_feature_index + (1 if delta < 0 else -1)) % len(self.features)
            self.execute_liquid_transition()
        super().wheelEvent(event)

    def get_centered_x(self, width):
        sr = self.screen().availableGeometry(); return sr.x() + (sr.width() // 2) - (width // 2)

    def execute_liquid_transition(self):
        if self.current_state == "Idle": w, h = self.IDLE_W, self.IDLE_H
        elif self.current_state == "Notify": w, h = self.NOTIFY_W, self.NOTIFY_H
        else:
            feature = self.features[self.current_feature_index]
            if feature == "media": w, h = self.MUSIC_W, self.MUSIC_H
            else: w, h = self.EXP_W, self.EXP_H
        
        target_rect = QRect(self.get_centered_x(w), 10, w, h); self.anim_group.stop()
        self.opacity_anim.setKeyValueAt(0, 1.0); self.opacity_anim.setKeyValueAt(0.5, 0.4); self.opacity_anim.setKeyValueAt(1.0, 1.0)
        self.geom_anim.setStartValue(self.geometry()); self.geom_anim.setEndValue(target_rect)
        QTimer.singleShot(200, self.update_feature_view); self.anim_group.start()

    def change_state(self, new):
        if self.current_state == new: return
        self.current_state = new; self.execute_liquid_transition()

    def recenter_window(self): self.remove(self.get_centered_x(self.width()), 10) if hasattr(self, 'remove') else self.move(self.get_centered_x(self.width()), 10)

    def check_mouse_position(self):
        if self.current_state == "Notify": return # Don't interrupt notification state by mouse
        cursor_pos = QCursor.pos(); rect = self.geometry(); hit_rect = rect.adjusted(-15, -15, 15, 15)
        hwnd = int(self.winId()); ex = ctypes.windll.user32.GetWindowLongW(hwnd, -20); WS_EX_TRANSPARENT = 0x20
        if hit_rect.contains(cursor_pos):
            if ex & WS_EX_TRANSPARENT: ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex & ~WS_EX_TRANSPARENT)
            self.change_state("Hover")
        else:
            if not (ex & WS_EX_TRANSPARENT): ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex | WS_EX_TRANSPARENT)
            self.change_state("Idle")

    def contextMenuEvent(self, event):
        menu = QMenu(self); menu.setStyleSheet("QMenu { background-color: #1a1a1a; color: #fff; border: 1px solid #333; padding: 4px; border-radius: 6px; } QMenu::item:selected { background-color: " + self.accent_color + "; }")
        am = menu.addMenu("Animation Style")
        for s in ["Glow Sweep", "Fluid Blobs", "Neon Border"]:
            a = am.addAction(s); a.setCheckable(True); a.setChecked(self.animation_style == s); a.triggered.connect(lambda _, st=s: setattr(self, 'animation_style', st))
        sm = menu.addMenu("Island Style")
        for s in ["Default", "Liquid Glass"]:
            a = sm.addAction(s); a.setCheckable(True); a.setChecked(self.island_style == s); a.triggered.connect(lambda _, st=s: setattr(self, 'island_style', st))
        menu.addSeparator(); qa = menu.addAction("Quit"); qa.triggered.connect(QApplication.quit); menu.exec(self.mapToGlobal(event.pos()))

if __name__ == "__main__":
    app = QApplication(sys.argv); island = DynamicIsland(); island.show(); sys.exit(app.exec())
