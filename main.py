import sys
import psutil
import winreg
import ctypes
import datetime
import math
import qtawesome as qta
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup, QPointF, pyqtProperty
from PyQt6.QtGui import (QCursor, QPainter, QColor, QBrush, QPaintEvent, 
                         QLinearGradient, QRadialGradient, QConicalGradient, QAction, QPen, QPainterPath, QRegion)
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QMenu, QPushButton, QGraphicsOpacityEffect, QGridLayout, QFrame, QProgressBar)
import webbrowser

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
        
        self.last_power_plugged = psutil.sensors_battery().power_plugged if psutil.sensors_battery() else False
        
        # Internal Animated Dimensions (The "Liquid Ink")
        self._island_w = 180
        self._island_h = 40
        self.island_w_anim = QPropertyAnimation(self, b"island_w")
        self.island_h_anim = QPropertyAnimation(self, b"island_h")
        for anim in [self.island_w_anim, self.island_h_anim]:
            anim.setDuration(850); anim.setEasingCurve(QEasingCurve.Type.OutExpo)
            
        self.shine_phase = -1.0
        self.shine_anim = QPropertyAnimation(self, b"shine_phase")
        self.shine_anim.setDuration(1800)
        self.shine_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.charging_phase = 0.0
        self.charging_anim = QPropertyAnimation(self, b"charging_phase")
        self.charging_anim.setDuration(3000)
        self.charging_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        self._weather_bg_opacity = 0.0
        self.weather_bg_anim = QPropertyAnimation(self, b"weather_bg_opacity")
        self.weather_bg_anim.setDuration(1200)
        self.weather_bg_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        self.weather_bg_phase = 0.0
        
        self._perf_bg_opacity = 0.0
        self.perf_bg_anim = QPropertyAnimation(self, b"perf_bg_opacity")
        self.perf_bg_anim.setDuration(1200)
        self.perf_bg_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        self._calendar_bg_opacity = 0.0
        self.calendar_bg_anim = QPropertyAnimation(self, b"calendar_bg_opacity")
        self.calendar_bg_anim.setDuration(1200)
        self.calendar_bg_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        self._month_bg_opacity = 0.0
        self.month_bg_anim = QPropertyAnimation(self, b"month_bg_opacity")
        self.month_bg_anim.setDuration(1200)
        self.month_bg_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        self.power_timer = QTimer(self)
        self.power_timer.timeout.connect(self.check_power_status)
        self.power_timer.start(2000)
        
        # Dimensions Constants
        self.IDLE_W, self.IDLE_H = 180, 40
        self.EXP_W, self.EXP_H = 340, 100
        self.PERF_W, self.PERF_H = 360, 180
        self.MUSIC_W, self.MUSIC_H = 420, 40
        self.NOTIFY_W, self.NOTIFY_H = 380, 40
        self.WEATHER_W, self.WEATHER_H = 360, 160
        self.CALENDAR_W, self.CALENDAR_H = 360, 165
        self.MONTH_W, self.MONTH_H = 360, 140
        self.WIDE_W = 1200 # Extra wide for absolute 'nothingness' fade
        
        self.is_charging = False
        
        self.current_state = "Idle"
        self.media_state = "Idle"
        self.media_title, self.media_artist = "", ""
        self.features = ["perf", "media", "weather", "calendar", "month"]
        self.current_feature_index = 0
        
        # Notification/Event queue
        self.event_title, self.event_text = "", ""
        self.revert_timer = QTimer(self); self.revert_timer.setSingleShot(True); self.revert_timer.timeout.connect(lambda: self.change_state("Idle"))
        
        self.setup_monitors()
        self.init_ui()
        self.setup_autostart()
        
        self.master_timer = QTimer(self); self.master_timer.timeout.connect(self.update_content); self.master_timer.start(1000)
        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self.update_animation); self.anim_timer.start(16)
        self.hit_timer = QTimer(self); self.hit_timer.timeout.connect(self.check_mouse_position); self.hit_timer.start(25)
        
        # FIXED CANVAS: Force a large fixed size to prevent layout shrinking
        self.setFixedSize(1200, 300); self.recenter_window()
        
        self.anim_group = QParallelAnimationGroup()
        self.opacity_anim = QPropertyAnimation(self.content_opacity, b"opacity"); self.opacity_anim.setDuration(850); self.opacity_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.content_pos_anim = QPropertyAnimation(self.content_container, b"pos"); self.content_pos_anim.setDuration(850); self.content_pos_anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        
        self.anim_group.addAnimation(self.island_w_anim); self.anim_group.addAnimation(self.island_h_anim)
        self.anim_group.addAnimation(self.opacity_anim); self.anim_group.addAnimation(self.content_pos_anim)

    @pyqtProperty(float)
    def weather_bg_opacity(self): return self._weather_bg_opacity
    @weather_bg_opacity.setter
    def weather_bg_opacity(self, val): self._weather_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def perf_bg_opacity(self): return self._perf_bg_opacity
    @perf_bg_opacity.setter
    def perf_bg_opacity(self, val): self._perf_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def calendar_bg_opacity(self): return self._calendar_bg_opacity
    @calendar_bg_opacity.setter
    def calendar_bg_opacity(self, val): self._calendar_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def month_bg_opacity(self): return self._month_bg_opacity
    @month_bg_opacity.setter
    def month_bg_opacity(self, val): self._month_bg_opacity = val; self.update()

    def get_current_radius(self):
        # Keeps pill shape for small heights, switches to rounded rect for taller panels
        return min(self._island_h / 2.0, 30.0)

    @pyqtProperty(int)
    def island_w(self): return self._island_w
    @island_w.setter
    def island_w(self, val): 
        self._island_w = val
        self.update_island_geometry(self.get_island_rect(), self.get_current_radius())
        self.update()

    @pyqtProperty(int)
    def island_h(self): return self._island_h
    @island_h.setter
    def island_h(self, val): 
        self._island_h = val
        self.update_island_geometry(self.get_island_rect(), self.get_current_radius())
        self.update()

    def paintEvent(self, a0: QPaintEvent):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.get_island_rect()
        p_rect = rect.adjusted(1, 1, -1, -1)
        radius = self.get_current_radius()

        # 1. Background Charging Animation ("Behind" the island)
        if self.charging_phase > 0.0:
            self.paint_charging_ears(painter, rect, radius)
        
        painter.setPen(Qt.PenStyle.NoPen)
        # 2. Drop shadow
        for i in range(5): 
            painter.setBrush(QColor(0, 0, 0, 15 - i*3))
            painter.drawRoundedRect(rect.adjusted(i, i, -i, -i), radius, radius)
        
        # 3. Base Island
        painter.setBrush(QBrush(QColor(0, 0, 0))); painter.drawRoundedRect(rect, radius, radius)

        # 4. Weather/Perf Animated Background (iOS style)
        if self._weather_bg_opacity > 0.0:
            self.paint_weather_bg(painter, rect, radius)
        if self._perf_bg_opacity > 0.0:
            self.paint_perf_bg(painter, rect, radius)
        if self._calendar_bg_opacity > 0.0:
            self.paint_calendar_bg(painter, rect, radius)
        if self._month_bg_opacity > 0.0:
            self.paint_month_bg(painter, rect, radius)
            
        # --- START STRICT CLIPPING ---
        # Everything drawn after this point will be strictly contained within the rounded rect
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(rect), radius, radius)
        painter.setClipPath(clip_path)

        can_anim = (self.current_state in ("Hover", "Notify") and self.features[self.current_feature_index] == "media") or \
                   (self.current_state == "Idle" and self.features[self.current_feature_index] == "media" and self.media_state in ("Playing", "Paused"))
        
        if can_anim:
            if self.animation_style == "Glow Sweep": self.paint_glow_sweep(painter, rect, radius)
            elif self.animation_style == "Fluid Blobs": self.paint_fluid_blobs(painter, rect, radius)
            elif self.animation_style == "Neon Border": self.paint_neon_border(painter, rect, radius)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor(255, 255, 255, 30), 1.2)); painter.drawRoundedRect(p_rect, radius, radius)

        # Content (Strictly Clipped)
        # We now use a container widget with a physical mask to ensure no labels/icons overflow.
        self.update_island_geometry(rect, radius)

        # Shine Sweep Animation (Strictly Clipped)
        if self.shine_phase > 0.0 and self.shine_phase < 1.0:
            self.paint_shine_sweep(painter, rect, radius)
        
        painter.setClipping(False) # Restore clipping
        # --- END STRICT CLIPPING ---

    def paint_shine_sweep(self, painter, rect, radius):
        import math
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        
        # shine_phase goes from 0.0 to 1.0 (Expansion progress)
        p = self.shine_phase
        if p <= 0 or p >= 1.0: return
        
        # Opacity curve: peaks early then dissipates
        opacity = math.sin(p * math.pi)
        
        start_x = 35
        max_reach = rect.width() * 1.5
        current_expansion = max_reach * p
        base_alpha = int(220 * math.sin(p * math.pi))
        for i in range(2):
            jitter_x = 0; jitter_y = 0
            W = current_expansion * (0.6 + i * 0.1)
            h = rect.height()
            target_x = start_x + (current_expansion * 0.4) + jitter_x
            target_y = (h / 2) + jitter_y
            painter.save()
            painter.translate(target_x, target_y)
            painter.scale(2.5, 0.8) 
            grad = QRadialGradient(QPointF(0, 0), W / 2)
            alpha = int(base_alpha * (1.0 - i * 0.3))
            grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
            grad.setColorAt(0.3, QColor(0, 160, 255, int(alpha * 0.6)))
            grad.setColorAt(0.6, QColor(90, 0, 255, int(alpha * 0.15)))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(grad); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(0, 0), W / 2, W / 2)
            painter.restore()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def paint_glow_sweep(self, painter, rect, radius):
        from PyQt6.QtGui import QTransform
        glow = QColor(self.album_accent_color); glow.setAlpha(120)
        gradient = QLinearGradient(0, 0, rect.width(), 0); gradient.setSpread(QLinearGradient.Spread.RepeatSpread)
        gradient.setColorAt(0.0, Qt.GlobalColor.transparent); gradient.setColorAt(0.5, glow); gradient.setColorAt(1.0, Qt.GlobalColor.transparent)
        brush = QBrush(gradient); transform = QTransform(); transform.translate(self.gradient_phase * rect.width() * 2, 0); brush.setTransform(transform)
        painter.setBrush(brush); painter.drawRoundedRect(rect, radius, radius)

    def paint_fluid_blobs(self, painter, rect, radius):
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        glow_color = QColor(self.album_accent_color); glow_color.setAlpha(100); p = self.gradient_phase * 2 * math.pi
        x1, y1 = rect.width() * (0.2 + 0.15 * math.sin(p)), rect.height() * (0.5 + 0.25 * math.cos(p))
        g1 = QRadialGradient(x1, y1, rect.width() * 0.45); g1.setColorAt(0, glow_color); g1.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(g1); painter.drawRoundedRect(rect, radius, radius)
        x2, y2 = rect.width() * (0.8 + 0.15 * math.cos(p * 0.7)), rect.height() * (0.5 + 0.25 * math.sin(p * 1.2))
        g2 = QRadialGradient(x2, y2, rect.width() * 0.35); g2.setColorAt(0, QColor(glow_color).lighter(125)); g2.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(g2); painter.drawRoundedRect(rect, radius, radius)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def paint_neon_border(self, painter, rect, radius):
        conical = QConicalGradient(QPointF(rect.center()), self.gradient_phase * 360)
        for i, c in enumerate(["#F00", "#FF0", "#0F0", "#0FF", "#00F", "#F0F", "#F00"]): conical.setColorAt(i/6.0, QColor(c))
        painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QBrush(conical), 2.2)); painter.drawRoundedRect(rect.adjusted(1,1,-1,-1), radius, radius)

    def update_animation(self):
        self.gradient_phase = (self.gradient_phase + 0.005) % 1.0
        self.weather_bg_phase = (self.weather_bg_phase + 0.003) % 1.0
        if self.current_state in ("Hover", "Notify") or self.media_state in ("Playing", "Paused") or \
           self._weather_bg_opacity > 0.0 or self._perf_bg_opacity > 0.0 or \
           self._calendar_bg_opacity > 0.0 or self._month_bg_opacity > 0.0: 
            self.update()

    def get_windows_accent_color(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM")
            v, _ = winreg.QueryValueEx(key, "ColorizationColor"); winreg.CloseKey(key); return f"#{(v & 0xFFFFFF):06x}"
        except: return "#0078D7"

    def get_shine_phase(self): return self._shine_phase
    def set_shine_phase(self, value): self._shine_phase = value; self.update()
    shine_phase = pyqtProperty(float, get_shine_phase, set_shine_phase)

    def get_charging_phase(self): return self._charging_phase
    def set_charging_phase(self, value): self._charging_phase = value; self.update()
    charging_phase = pyqtProperty(float, get_charging_phase, set_charging_phase)

    def setup_autostart(self):
        try:
            app_path = sys.executable if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{sys.argv[0]}"'
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "DynamicIsland", 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
        except Exception as e: print("Autostart error:", e)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self); self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)
        self.island_root = QWidget(self)
        self.island_root.setObjectName("IslandRoot")
        self.island_root_layout = QVBoxLayout(self.island_root); self.island_root_layout.setContentsMargins(15, 0, 15, 0); self.island_root_layout.setSpacing(0)
        self.content_container = QWidget(); self.content_layout = QVBoxLayout(self.content_container); self.content_layout.setContentsMargins(0, 0, 0, 0); self.content_layout.setSpacing(0)
        self.content_opacity = QGraphicsOpacityEffect(self.content_container); self.content_container.setGraphicsEffect(self.content_opacity)
        self.header_widget = QWidget(); self.header_layout = QHBoxLayout(self.header_widget); self.header_layout.setContentsMargins(0, 0, 0, 0); self.header_layout.setSpacing(10)
        self.status_icon = QLabel(); self.status_icon.setObjectName("IconLabel"); self.status_icon.setFixedSize(22, 22)
        self.status_icon.setPixmap(qta.icon('mdi.circle', color=self.accent_color).pixmap(20, 20))
        self.status_text = QLabel(""); self.status_text.setObjectName("TitleLabel")
        self.header_layout.addWidget(self.status_icon); self.header_layout.addWidget(self.status_text)
        self.media_controls = QWidget(); self.media_controls_layout = QHBoxLayout(self.media_controls); self.media_controls_layout.setContentsMargins(0, 0, 0, 0); self.media_controls_layout.setSpacing(2)
        self.btn_prev = QPushButton(icon=qta.icon('mdi.skip-previous', color='white')); self.btn_play = QPushButton(icon=qta.icon('mdi.play', color='white')); self.btn_next = QPushButton(icon=qta.icon('mdi.skip-next', color='white'))
        for b in [self.btn_prev, self.btn_play, self.btn_next]: b.setObjectName("MediaButton")
        self.btn_prev.clicked.connect(self.media_monitor.prev_track); self.btn_play.clicked.connect(self.media_monitor.toggle_play_pause); self.btn_next.clicked.connect(self.media_monitor.next_track)
        for b in [self.btn_prev, self.btn_play, self.btn_next]: self.media_controls_layout.addWidget(b)
        self.perf_widget = QWidget(); self.perf_layout = QHBoxLayout(self.perf_widget); self.perf_layout.setContentsMargins(0, 0, 0, 0); self.perf_layout.setSpacing(8)
        self.cpu_label = QLabel("CPU: 0%"); self.cpu_label.setObjectName("PerfLabel")
        self.ram_label = QLabel("RAM: 0%"); self.ram_label.setObjectName("PerfLabel")
        self.perf_layout.addWidget(self.cpu_label); self.perf_layout.addWidget(self.ram_label)
        self.header_layout.addStretch(); self.header_layout.addWidget(self.media_controls); self.header_layout.addWidget(self.perf_widget); self.media_controls.hide(); self.perf_widget.hide()
        
        # New Feature Panels
        self.perf_panel = self.create_perf_panel()
        self.weather_panel = self.create_weather_panel()
        self.calendar_panel = self.create_calendar_panel()
        self.month_panel = self.create_month_panel()
        
        for p in [self.perf_panel, self.weather_panel, self.calendar_panel, self.month_panel]: p.hide()
        
        self.content_layout.addWidget(self.header_widget)
        self.content_layout.addWidget(self.perf_panel)
        self.content_layout.addWidget(self.weather_panel)
        self.content_layout.addWidget(self.calendar_panel)
        self.content_layout.addWidget(self.month_panel)
        
        self.island_root_layout.addWidget(self.content_container); self.update_content()
        self.update_island_geometry(self.get_island_rect(), self.get_current_radius())

    def setup_monitors(self):
        self.perf_monitor = PerfMonitor(parent=self); self.perf_monitor.metrics_updated.connect(self.update_perf); self.perf_monitor.start()
        self.media_monitor = MediaMonitor(self); self.media_monitor.media_updated.connect(self.update_media); self.media_monitor.start()
        self.key_monitor = KeyLockMonitor(self); self.key_monitor.lock_changed.connect(self.show_key_event); self.key_monitor.start()
        self.notif_monitor = NotificationMonitor(self); self.notif_monitor.notification_received.connect(self.show_notification); self.notif_monitor.start()

    def update_island_geometry(self, rect, radius):
        if not hasattr(self, 'island_root'): return
        self.island_root.setGeometry(int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()))
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, rect.width(), rect.height()), radius, radius)
        self.island_root.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def paint_charging_ears(self, painter, rect, radius):
        p = self.charging_phase
        if p <= 0: return
        
        opacity = math.sin(p * math.pi)
        centerX = rect.center().x()
        centerY = rect.top() + rect.height() / 2
        
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)

        # 1. Main Soft Glow Aura (Behind and around)
        glow_path = QPainterPath()
        glow_path.addRoundedRect(rect.adjusted(-20*opacity, -10*opacity, 20*opacity, 10*opacity), radius+10, radius+10)
        
        # Multi-layered soft glow
        for i in range(5):
            alpha = int(70 * opacity / (i + 1))
            glow_grad = QRadialGradient(rect.center(), rect.width() / 1.5)
            # Alternate Cyan and Deep Purple for vibrancy
            color = QColor(0, 255, 255, alpha) if i % 2 == 0 else QColor(140, 0, 255, alpha)
            painter.setPen(QPen(color, 12 + i*8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(glow_path)

        # 2. Cinematic Laser Beams (Thicker and Glowing)
        beam_len = 500 * opacity
        left_edge = rect.left()
        right_edge = rect.right()
        
        # Right Beam - Tapered Glow
        for i in range(3):
            beam_w = 4 - i
            if beam_w <= 0: continue
            alpha = int(180 * opacity / (i + 1))
            r_beam_grad = QLinearGradient(right_edge, centerY, right_edge + beam_len, centerY)
            r_beam_grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
            r_beam_grad.setColorAt(0.1, QColor(0, 240, 255, alpha))
            r_beam_grad.setColorAt(0.5, QColor(160, 0, 255, alpha // 2))
            r_beam_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            
            painter.setPen(QPen(QBrush(r_beam_grad), beam_w + 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(right_edge, centerY), QPointF(right_edge + beam_len, centerY))

        # Left Beam - Tapered Glow
        for i in range(3):
            beam_w = 4 - i
            if beam_w <= 0: continue
            alpha = int(180 * opacity / (i + 1))
            l_beam_grad = QLinearGradient(left_edge, centerY, left_edge - beam_len, centerY)
            l_beam_grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
            l_beam_grad.setColorAt(0.1, QColor(0, 240, 255, alpha))
            l_beam_grad.setColorAt(0.5, QColor(160, 0, 255, alpha // 2))
            l_beam_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            
            painter.setPen(QPen(QBrush(l_beam_grad), beam_w + 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(left_edge, centerY), QPointF(left_edge - beam_len, centerY))

        # 3. Bright Core Impact points
        painter.setBrush(QColor(255, 255, 255, int(255 * opacity)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(right_edge, centerY), 4, 3)
        painter.drawEllipse(QPointF(left_edge, centerY), 4, 3)
        
        painter.restore()

    def check_power_status(self):
        try:
            battery = psutil.sensors_battery()
            if battery:
                is_plugged = battery.power_plugged
                if is_plugged and not self.last_power_plugged:
                    self.trigger_charging_anim()
                self.last_power_plugged = is_plugged
        except: pass

    def trigger_charging_anim(self):
        self.is_charging = True
        self.execute_liquid_transition()
        self.charging_anim.stop()
        self.charging_anim.setStartValue(0.0)
        self.charging_anim.setEndValue(1.0)
        self.charging_anim.start()
        QTimer.singleShot(3100, self.cleanup_charging_anim)

    def cleanup_charging_anim(self):
        self.is_charging = False
        self.charging_phase = 0.0
        self.execute_liquid_transition()

    def show_key_event(self, name, is_on):
        self.event_title = name; self.event_text = ("ENABLED" if is_on else "DISABLED")
        if self.current_state == "Notify": self.update_feature_view(); self.execute_liquid_transition()
        else: self.change_state("Notify")
        self.revert_timer.start(2500)

    def show_notification(self, app, title, text):
        self.event_title = app; self.event_text = (f"{title}: {text}" if title else text)
        if self.current_state == "Notify": self.update_feature_view(); self.execute_liquid_transition()
        else: self.change_state("Notify")
        self.revert_timer.start(3500)

    def paint_weather_bg(self, painter, rect, radius):
        painter.save()
        painter.setOpacity(self._weather_bg_opacity)
        p = self.weather_bg_phase * 2 * math.pi
        
        # Base deep blue
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(20, 40, 100))
        grad.setColorAt(1, QColor(10, 20, 60))
        painter.setBrush(grad); painter.drawRoundedRect(rect, radius, radius)
        
        # Liquid Blooms
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        for i, color in enumerate([QColor(60, 130, 250, 120), QColor(40, 80, 220, 100)]):
            x = rect.center().x() + math.sin(p + i) * (rect.width() * 0.3)
            y = rect.center().y() + math.cos(p * 0.7 + i*2) * (rect.height() * 0.2)
            bloom = QRadialGradient(QPointF(x, y), rect.width() * 0.6)
            bloom.setColorAt(0, color); bloom.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(bloom); painter.drawRoundedRect(rect, radius, radius)
        painter.restore()

    def paint_perf_bg(self, painter, rect, radius):
        painter.save()
        painter.setOpacity(self._perf_bg_opacity)
        p = self.weather_bg_phase * 2 * math.pi # Use same phase for sync
        
        # Base deep forest green
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(0, 40, 20))
        grad.setColorAt(1, QColor(0, 20, 10))
        painter.setBrush(grad); painter.drawRoundedRect(rect, radius, radius)
        
        # Liquid Lime Blooms
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        for i, color in enumerate([QColor(50, 255, 50, 80), QColor(200, 255, 0, 60)]):
            x = rect.center().x() + math.sin(p * 0.8 + i*1.5) * (rect.width() * 0.35)
            y = rect.center().y() + math.cos(p * 0.5 + i) * (rect.height() * 0.25)
            bloom = QRadialGradient(QPointF(x, y), rect.width() * 0.5)
            bloom.setColorAt(0, color); bloom.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(bloom); painter.drawRoundedRect(rect, radius, radius)
        painter.restore()

    def paint_calendar_bg(self, painter, rect, radius):
        painter.save()
        painter.setOpacity(self._calendar_bg_opacity)
        p = self.weather_bg_phase * 2 * math.pi
        
        # Base deep amber/brown
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(60, 40, 0))
        grad.setColorAt(1, QColor(30, 20, 0))
        painter.setBrush(grad); painter.drawRoundedRect(rect, radius, radius)
        
        # Liquid Amber/Yellow Blooms
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        for i, color in enumerate([QColor(255, 180, 0, 90), QColor(255, 255, 0, 60)]):
            x = rect.center().x() + math.sin(p * 0.9 + i*2) * (rect.width() * 0.3)
            y = rect.center().y() + math.cos(p * 0.6 + i) * (rect.height() * 0.2)
            bloom = QRadialGradient(QPointF(x, y), rect.width() * 0.55)
            bloom.setColorAt(0, color); bloom.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(bloom); painter.drawRoundedRect(rect, radius, radius)
        painter.restore()

    def paint_month_bg(self, painter, rect, radius):
        painter.save()
        painter.setOpacity(self._month_bg_opacity)
        p = self.weather_bg_phase * 2 * math.pi
        
        # Base deep midnight purple
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(30, 0, 50))
        grad.setColorAt(1, QColor(15, 0, 30))
        painter.setBrush(grad); painter.drawRoundedRect(rect, radius, radius)
        
        # Liquid Purple/Magenta Blooms
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        for i, color in enumerate([QColor(180, 0, 255, 80), QColor(255, 0, 180, 60)]):
            x = rect.center().x() + math.sin(p * 1.1 + i) * (rect.width() * 0.3)
            y = rect.center().y() + math.cos(p * 0.8 + i*1.2) * (rect.height() * 0.2)
            bloom = QRadialGradient(QPointF(x, y), rect.width() * 0.5)
            bloom.setColorAt(0, color); bloom.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(bloom); painter.drawRoundedRect(rect, radius, radius)
        painter.restore()

    def create_action_button(self, app_type):
        btn = QPushButton(icon=qta.icon('mdi.open-in-new', color='white'))
        btn.setObjectName("ActionButton")
        btn.setFixedSize(32, 32)
        btn.clicked.connect(lambda: self.open_app(app_type))
        return btn

    def open_app(self, app_type):
        schemes = {"weather": "bingweather:", "calendar": "outlookcal:", "month": "ms-settings:dateandtime"}
        if app_type in schemes: webbrowser.open(schemes[app_type])

    def create_weather_panel(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(10, 10, 10, 15); l.setSpacing(12)
        h1 = QHBoxLayout(); temp = QLabel("34°"); temp.setStyleSheet("font-size: 38px; font-weight: bold;")
        info = QVBoxLayout(); city = QLabel("Varanasi, India"); city.setStyleSheet("font-size: 14px; font-weight: 600;")
        cond = QLabel("Mostly Sunny"); cond.setStyleSheet("font-size: 11px; color: #AAA;")
        info.addWidget(city); info.addWidget(cond); h1.addLayout(info); h1.addStretch(); h1.addWidget(temp)
        h1.addWidget(self.create_action_button("weather"))
        l.addLayout(h1)
        h2 = QHBoxLayout(); h2.setSpacing(5)
        for t, ic, tmp in [("2PM", "mdi.weather-sunny", "35°"), ("3PM", "mdi.weather-sunny", "35°"), ("4PM", "mdi.weather-sunny", "36°"), ("5PM", "mdi.weather-cloudy", "34°"), ("6PM", "mdi.weather-cloudy", "32°")]:
            slot = QVBoxLayout(); slot.setSpacing(2); st = QLabel(t); st.setStyleSheet("font-size: 9px; color: #888;"); st.setAlignment(Qt.AlignmentFlag.AlignCenter)
            si = QLabel(); si.setPixmap(qta.icon(ic, color='white').pixmap(18, 18)); si.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stp = QLabel(tmp); stp.setStyleSheet("font-size: 10px; font-weight: 600;"); stp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slot.addWidget(st); slot.addWidget(si); slot.addWidget(stp); h2.addLayout(slot)
        l.addLayout(h2); return w

    def create_calendar_panel(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(10, 8, 10, 15); l.setSpacing(10)
        header = QHBoxLayout(); title = QLabel("Today"); title.setStyleSheet("font-weight: bold; font-size: 14px;")
        ev_count = QLabel("3 events"); ev_count.setStyleSheet("color: #888; font-size: 11px;")
        header.addWidget(title); header.addStretch(); header.addWidget(ev_count); header.addWidget(self.create_action_button("calendar"))
        l.addLayout(header)
        for name, cat, color, time in [("Project Sync", "Work", "#00A0FF", "2:00 PM"), ("Gym Session", "Health", "#00FF80", "5:30 PM"), ("Dinner with Family", "Personal", "#FF5050", "8:00 PM")]:
            row = QHBoxLayout(); bar = QFrame(); bar.setFixedWidth(3); bar.setStyleSheet(f"background-color: {color}; border-radius: 1px;")
            det = QVBoxLayout(); det.setContentsMargins(0, 0, 0, 0); det.setSpacing(1)
            n = QLabel(name); n.setStyleSheet("font-size: 13px; font-weight: 600; padding: 0px;"); c = QLabel(cat); c.setStyleSheet("font-size: 10px; color: #888; padding: 0px;")
            det.addWidget(n); det.addWidget(c); tm = QLabel(time); tm.setStyleSheet("font-size: 11px; font-weight: 500;")
            row.addWidget(bar); row.addLayout(det); row.addStretch(); row.addWidget(tm); l.addLayout(row)
        return w

    def create_perf_panel(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(15, 12, 15, 18); l.setSpacing(12)
        header = QHBoxLayout(); title = QLabel("System Status"); title.setStyleSheet("font-weight: bold; font-size: 15px;")
        header.addWidget(title); header.addStretch(); header.addWidget(self.create_action_button("month")) # Fallback
        l.addLayout(header)

        # Helper for rows
        def add_item(layout, icon, label):
            v = QVBoxLayout(); v.setSpacing(4)
            h = QHBoxLayout(); ico = QLabel(); ico.setPixmap(qta.icon(icon, color="white").pixmap(14, 14))
            txt = QLabel(label); txt.setStyleSheet("font-size: 11px; color: #888; font-weight: 600;")
            h.addWidget(ico); h.addWidget(txt); h.addStretch()
            val = QLabel("0%"); val.setStyleSheet("font-size: 13px; font-weight: 600;")
            bar = QProgressBar(); bar.setFixedHeight(4); bar.setTextVisible(False); bar.setMaximum(100)
            bar.setStyleSheet("QProgressBar { background-color: #222; border-radius: 2px; border: none; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00FF80, stop:1 #80FF00); border-radius: 2px; }")
            v.addLayout(h); v.addWidget(val); v.addWidget(bar)
            layout.addLayout(v); return bar, val

        r1 = QHBoxLayout(); r1.setSpacing(30)
        self.cpu_bar_L = add_item(r1, "mdi.cpu-64-bit", "CPU")
        self.ram_bar_L = add_item(r1, "mdi.memory", "RAM")
        l.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(30)
        self.disk_bar_L = add_item(r2, "mdi.harddisk", "STORAGE")
        
        nv = QVBoxLayout(); nv.setSpacing(4)
        nh = QHBoxLayout(); nico = QLabel(); nico.setPixmap(qta.icon("mdi.web", color="white").pixmap(14, 14))
        ntxt = QLabel("NETWORK"); ntxt.setStyleSheet("font-size: 11px; color: #888; font-weight: 600;")
        nh.addWidget(nico); nh.addWidget(ntxt); nh.addStretch(); nv.addLayout(nh)
        self.net_down_L = QLabel("↓ 0 KB/s"); self.net_up_L = QLabel("↑ 0 KB/s")
        for lb in [self.net_down_L, self.net_up_L]: lb.setStyleSheet("font-size: 12px; font-weight: 600;")
        nv.addWidget(self.net_down_L); nv.addWidget(self.net_up_L); r2.addLayout(nv)
        l.addLayout(r2); return w
        return w

    def create_month_panel(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(10, 8, 10, 18); l.setSpacing(8)
        now = datetime.datetime.now(); days = (datetime.date(now.year, now.month + 1, 1) - datetime.date(now.year, now.month, 1)).days if now.month < 12 else 31
        header = QHBoxLayout(); title = QLabel(now.strftime("%B Progress")); title.setStyleSheet("font-weight: bold; font-size: 14px;")
        perc = QLabel(f"{int(now.day/days*100)}%"); perc.setStyleSheet("color: #00A0FF; font-weight: bold; font-size: 14px;")
        header.addWidget(title); header.addStretch(); header.addWidget(perc); header.addWidget(self.create_action_button("month"))
        l.addLayout(header); grid = QGridLayout(); grid.setSpacing(8); grid.setContentsMargins(0, 5, 0, 0)
        for i in range(days):
            dot = QFrame(); dot.setFixedSize(12, 12); color = "#00A0FF" if (i+1) <= now.day else "#333"
            dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;"); grid.addWidget(dot, i//10, i%10)
        l.addLayout(grid); return w



    def update_content(self):
        if self.current_state == "Idle":
            feature = self.features[self.current_feature_index]
            if feature == "media" and self.media_state in ("Playing", "Paused"):
                dt = self.media_title; self.status_text.setText(dt[:22] + "..." if len(dt) > 25 else dt)
                self.status_icon.setPixmap(qta.icon('mdi.music', color='white').pixmap(18, 18))
            else:
                now = datetime.datetime.now(); ts = now.strftime("%I:%M %p").lstrip("0"); self.status_text.setText(f"{now.strftime('%a')}, {ts}")
                self.status_icon.setPixmap(qta.icon('mdi.circle', color=self.accent_color).pixmap(18, 18))
        self.update()

    def update_perf(self, data):
        cpu, ram, disk = data["cpu"], data["ram"], data["disk"]
        down, up = data["down"], data["up"]
        
        # Header (Small - used in Idle/Notify)
        self.cpu_label.setText(f"CPU: {int(cpu)}%"); self.ram_label.setText(f"RAM: {int(ram)}%")
        
        # Large Panel Detailed Metrics
        self.cpu_bar_L[0].setValue(int(cpu)); self.cpu_bar_L[1].setText(f"{int(cpu)}%")
        self.ram_bar_L[0].setValue(int(ram)); self.ram_bar_L[1].setText(f"{int(ram)}%")
        self.disk_bar_L[0].setValue(int(disk)); self.disk_bar_L[1].setText(f"{int(disk)}%")
        
        # Net speed formatting helper
        def fmt(b):
            if b < 1024: return f"{int(b)} B/s"
            if b < 1024*1024: return f"{int(b/1024)} KB/s"
            return f"{b/(1024*1024):.1f} MB/s"
            
        self.net_down_L.setText(f"↓ {fmt(down)}"); self.net_up_L.setText(f"↑ {fmt(up)}")

    def update_media(self, state, title, artist, accent_hex):
        self.media_state, self.media_title, self.media_artist = state, title, artist; self.album_accent_color = QColor(accent_hex)
        self.btn_play.setIcon(qta.icon('mdi.pause' if state == "Playing" else 'mdi.play', color='white')); self.update_content()
        if self.current_state == "Hover": self.update_feature_view()

    def update_feature_view(self):
        if self.current_state == "Idle":
            self.perf_panel.hide(); self.perf_widget.hide(); self.media_controls.hide(); self.weather_panel.hide(); self.calendar_panel.hide(); self.month_panel.hide()
            self.header_widget.show(); self.update_content(); return
        if self.current_state == "Notify":
            self.perf_panel.hide(); self.perf_widget.hide(); self.media_controls.hide(); self.weather_panel.hide(); self.calendar_panel.hide(); self.month_panel.hide(); self.header_widget.show()
            self.status_icon.setPixmap(qta.icon('mdi.lightning-bolt' if "Lock" in self.event_title else 'mdi.email', color='white').pixmap(18, 18))
            dt = f"{self.event_title} - {self.event_text}"; self.status_text.setText(dt[:45] + "..." if len(dt) > 48 else dt)
            return
        feature = self.features[self.current_feature_index]
        self.header_widget.show() if feature == "media" else self.header_widget.hide()
        self.perf_panel.setVisible(feature == "perf")
        self.media_controls.setVisible(feature == "media")
        self.weather_panel.setVisible(feature == "weather"); self.calendar_panel.setVisible(feature == "calendar"); self.month_panel.setVisible(feature == "month")
        if feature == "perf": self.status_text.setText("Performance Status"); self.status_icon.setPixmap(qta.icon('mdi.speedometer', color='white').pixmap(18, 18))
        elif feature == "media":
            if self.media_state in ("Playing", "Paused"):
                dt = f"{self.media_title} - {self.media_artist}"; self.status_text.setText(dt[:37] + "..." if len(dt) > 40 else dt)
            else: self.status_text.setText("Music Player")
            self.status_icon.setPixmap(qta.icon('mdi.music', color='white').pixmap(18, 18))

    def wheelEvent(self, event):
        if self.current_state == "Hover":
            delta = event.angleDelta().y()
            self.current_feature_index = (self.current_feature_index + (1 if delta < 0 else -1)) % len(self.features)
            self.execute_liquid_transition()
        super().wheelEvent(event)

    def get_centered_x(self, width):
        sr = self.screen().availableGeometry(); return sr.x() + (sr.width() // 2) - (width // 2)

    def execute_liquid_transition(self):
        if self.is_charging: w, h = 850, 40
        elif self.current_state == "Idle": w, h = self.IDLE_W, self.IDLE_H
        elif self.current_state == "Notify": w, h = self.NOTIFY_W, self.NOTIFY_H
        else:
            feature = self.features[self.current_feature_index]
            if feature == "media": w, h = self.MUSIC_W, self.MUSIC_H
            elif feature == "perf": w, h = self.PERF_W, self.PERF_H
            elif feature == "weather": w, h = self.WEATHER_W, self.WEATHER_H
            elif feature == "calendar": w, h = self.CALENDAR_W, self.CALENDAR_H
            elif feature == "month": w, h = self.MONTH_W, self.MONTH_H
            else: w, h = self.EXP_W, self.EXP_H
        if not self.is_charging:
             self.shine_anim.stop(); self.shine_anim.setStartValue(0.0); self.shine_anim.setEndValue(1.0); self.shine_anim.start()
        
        # BG Cross-fades (Multi-theme)
        def set_bg_target(anim, current_val, target_val):
            anim.stop(); anim.setStartValue(current_val); anim.setEndValue(target_val); anim.start()

        is_hover = (self.current_state != "Idle" and self.current_state != "Notify")
        feat = self.features[self.current_feature_index] if is_hover else None

        set_bg_target(self.weather_bg_anim, self._weather_bg_opacity, 1.0 if feat == "weather" else 0.0)
        set_bg_target(self.perf_bg_anim, self._perf_bg_opacity, 1.0 if feat == "perf" else 0.0)
        set_bg_target(self.calendar_bg_anim, self._calendar_bg_opacity, 1.0 if feat == "calendar" else 0.0)
        set_bg_target(self.month_bg_anim, self._month_bg_opacity, 1.0 if feat == "month" else 0.0)

        self.anim_group.stop()
        self.content_pos_anim.setStartValue(QPoint(15, 0))
        self.content_pos_anim.setEndValue(QPoint(-10, 0))
        self.opacity_anim.setStartValue(1.0); self.opacity_anim.setKeyValueAt(0.3, 0.0); self.opacity_anim.setEndValue(1.0)
        self.island_w_anim.setStartValue(self._island_w); self.island_w_anim.setEndValue(w)
        self.island_h_anim.setStartValue(self._island_h); self.island_h_anim.setEndValue(h)
        QTimer.singleShot(250, self.update_feature_view)
        QTimer.singleShot(250, lambda: self.reset_content_slide(w))
        self.anim_group.start()

    def reset_content_slide(self, target_w):
        current_y = self.content_container.y()
        self.content_pos_anim.stop()
        self.content_pos_anim.setStartValue(QPoint(target_w // 4, current_y))
        self.content_pos_anim.setEndValue(QPoint(15, current_y))
        self.content_pos_anim.start()

    def change_state(self, new):
        if self.current_state == new: return
        self.current_state = new; self.execute_liquid_transition()

    def get_island_rect(self):
        W = self._island_w
        H = self._island_h
        centerX = self.width() / 2
        return QRectF(centerX - W/2, 10, W, H)

    def recenter_window(self): self.move(self.get_centered_x(self.width()), 10)

    def check_mouse_position(self):
        if self.current_state == "Notify": return
        cursor_pos = QCursor.pos()
        rect = self.get_island_rect()
        
        # Correctly map both corners to global coordinates for a reliable hit-test
        global_top_left = self.mapToGlobal(QPoint(int(rect.x()), int(rect.y())))
        global_bottom_right = self.mapToGlobal(QPoint(int(rect.right()), int(rect.bottom())))
        global_rect = QRect(global_top_left, global_bottom_right)
        
        hit_rect = global_rect.adjusted(-15, -10, 15, 15)  # Generous hit zone
        hwnd = int(self.winId())
        ex = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        WS_EX_TRANSPARENT = 0x20
        
        if hit_rect.contains(cursor_pos):
            if ex & WS_EX_TRANSPARENT: 
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex & ~WS_EX_TRANSPARENT)
            if self.current_state != "Hover": 
                self.change_state("Hover")
            self.revert_timer.stop()
        else:
            if not (ex & WS_EX_TRANSPARENT): 
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex | WS_EX_TRANSPARENT)
            if self.current_state == "Hover":
                if not self.revert_timer.isActive():
                    self.revert_timer.start(1200) # Grace period before returning to Idle

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
