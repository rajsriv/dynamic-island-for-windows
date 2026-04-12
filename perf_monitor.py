import psutil
from PyQt6.QtCore import QThread, pyqtSignal
import time

class PerfMonitor(QThread):
    metrics_updated = pyqtSignal(dict) 

    def __init__(self, interval_sec=1.0, parent=None):
        super().__init__(parent)
        self.interval_sec = interval_sec
        self._is_running = True
        psutil.cpu_percent(interval=None)

    def run(self):
        last_net = psutil.net_io_counters()
        last_time = time.time()
        
        while self._is_running:
            cpu = psutil.cpu_percent(interval=None) 
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            cur_net = psutil.net_io_counters()
            cur_time = time.time()
            dt = cur_time - last_time
            
            # Bytes per second
            down = (cur_net.bytes_recv - last_net.bytes_recv) / dt if dt > 0 else 0
            up = (cur_net.bytes_sent - last_net.bytes_sent) / dt if dt > 0 else 0
            
            data = {
                "cpu": cpu,
                "ram": ram,
                "disk": disk,
                "down": down,
                "up": up
            }
            
            self.metrics_updated.emit(data)
            
            last_net = cur_net
            last_time = cur_time
            
            for _ in range(int(self.interval_sec * 10)):
                if not self._is_running:
                    break
                time.sleep(0.1)

    def stop(self):
        self._is_running = False
        self.wait()
