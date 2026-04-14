import ctypes
import time
from PyQt6.QtCore import QThread, pyqtSignal

class KeyLockMonitor(QThread):
                              
    lock_changed = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self.last_caps = self.get_caps_lock()
        self.last_num = self.get_num_lock()

    def get_caps_lock(self):
                           
        return (ctypes.windll.user32.GetKeyState(0x14) & 1) != 0

    def get_num_lock(self):
                           
        return (ctypes.windll.user32.GetKeyState(0x90) & 1) != 0

    def run(self):
        while self._is_running:
            caps = self.get_caps_lock()
            if caps != self.last_caps:
                self.last_caps = caps
                self.lock_changed.emit("Caps Lock", caps)

            num = self.get_num_lock()
            if num != self.last_num:
                self.last_num = num
                self.lock_changed.emit("Num Lock", num)

            time.sleep(0.02)

    def stop(self):
        self._is_running = False
        self.wait()
