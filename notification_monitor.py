import asyncio
from PyQt6.QtCore import QThread, pyqtSignal
from winsdk.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus

class NotificationMonitor(QThread):
                                   
    notification_received = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self.loop = None
        self.listener = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.setup_listener())
        except Exception as e:
            print("NotificationMonitor setup error:", e)

    async def setup_listener(self):
        try:
            from winsdk.windows.foundation.metadata import ApiInformation
            if not ApiInformation.is_type_present("Windows.UI.Notifications.Management.UserNotificationListener"):
                print("UserNotificationListener is not supported on this device.")
                return

            self.listener = UserNotificationListener.current
            if not self.listener:
                print("Unable to get current UserNotificationListener instance.")
                return

            access_status = await self.listener.request_access_async()
            if access_status != UserNotificationListenerAccessStatus.ALLOWED:
                print(f"Notification access status: {access_status}. Please enable it in Windows Settings.")
                return
        except Exception as e:
            print(f"Notification setup error: {e}")
            return

                                                                                       
                                                                                 
                                                 
        
        known_ids = set()
                        
        initial = await self.listener.get_notifications_async(0x1)              
        for n in initial:
            known_ids.add(n.id)

        while self._is_running:
            try:
                notifications = await self.listener.get_notifications_async(0x1)
                for n in notifications:
                    if n.id not in known_ids:
                        known_ids.add(n.id)
                        try:
                            app_name = n.app_info.display_info.display_name
                                           
                            bindings = n.notification.visual.bindings
                            title = ""
                            body = ""
                            for b in bindings:
                                text_elements = b.get_text_elements()
                                if len(text_elements) > 0: title = text_elements[0].text
                                if len(text_elements) > 1: body = text_elements[1].text
                            
                            self.notification_received.emit(app_name, title, body)
                        except: pass
            except: pass
            await asyncio.sleep(1.0)                                    

    def stop(self):
        self._is_running = False
        if self.loop:
            self.loop.stop()
        self.wait()
