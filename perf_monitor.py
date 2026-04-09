import psutil
from PyQt6.QtCore import QThread, pyqtSignal
import time

class PerfMonitor(QThread):
    metrics_updated = pyqtSignal(float, float) # cpu_percent, ram_percent

    def __init__(self, interval_sec=2.0, parent=None):
        super().__init__(parent)
        self.interval_sec = interval_sec
        self._is_running = True
        # Initialize psutil cpu percent
        psutil.cpu_percent(interval=None)

    def run(self):
        while self._is_running:
            cpu = psutil.cpu_percent(interval=None) 
            ram = psutil.virtual_memory().percent
            
            self.metrics_updated.emit(cpu, ram)
            
            for _ in range(int(self.interval_sec * 10)):
                if not self._is_running:
                    break
                time.sleep(0.1)

    def stop(self):
        self._is_running = False
        self.wait()
