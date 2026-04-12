import asyncio
import io
from PyQt6.QtCore import QThread, pyqtSignal
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager, GlobalSystemMediaTransportControlsSessionPlaybackStatus
from winsdk.windows.storage.streams import DataReader, Buffer
from PIL import Image

class MediaMonitor(QThread):
    media_updated = pyqtSignal(str, str, str, str) # state, title, artist, accent_color

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self.loop = None
        self.manager = None
        self.current_session = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.monitor_media())
        except Exception as e:
            print("MediaMonitor error:", e)

    async def monitor_media(self):
        self.manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        
        await self.update_media_info()
        
        self.manager.add_sessions_changed(self.on_sessions_changed)
        
        self.subscribe_to_current_session()

        while self._is_running:
            await asyncio.sleep(0.5)

    def subscribe_to_current_session(self):
        try:
            self.current_session = self.manager.get_current_session()
            if self.current_session:
                self.current_session.add_media_properties_changed(self.on_properties_changed)
                self.current_session.add_playback_info_changed(self.on_playback_changed)
        except Exception as e:
            print(f"Error subscribing to media session: {e}")
            self.current_session = None

    def on_sessions_changed(self, sender, args):
        if self.loop and self._is_running:
            self.subscribe_to_current_session()
            asyncio.run_coroutine_threadsafe(self.update_media_info(), self.loop)

    def on_properties_changed(self, sender, args):
        if self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(self.update_media_info(), self.loop)

    def on_playback_changed(self, sender, args):
        if self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(self.update_media_info(), self.loop)

    async def update_media_info(self):
        try:
            if not self.current_session:
                # Try re-subscribing in case session just became available
                self.subscribe_to_current_session()
                if not self.current_session:
                    self.media_updated.emit("Idle", "", "", "#000000")
                    return

            try:
                info = self.current_session.get_playback_info()
            except Exception as e:
                if "remote procedure call failed" in str(e).lower() or "0x800706be" in str(e).lower():
                    self.current_session = None # Reset session on RPC failure
                self.media_updated.emit("Idle", "", "", "#000000")
                return

            if not info:
                self.media_updated.emit("Idle", "", "", "#000000")
                return

            status = info.playback_status
            
            state_str = "Idle"
            if status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                state_str = "Playing"
            elif status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED:
                state_str = "Paused"

            if state_str in ("Playing", "Paused"):
                try:
                    props = await self.current_session.try_get_media_properties_async()
                    if not props:
                        self.media_updated.emit(state_str, "Unknown Title", "", "#000000")
                        return
                    
                    title = props.title if props.title else "Unknown Title"
                    artist = props.artist if props.artist else ""
                    
                    accent_color = "#000000"
                    if props.thumbnail:
                        try:
                            thumb_stream = await props.thumbnail.open_read_async()
                            reader = DataReader(thumb_stream.get_input_stream_at(0))
                            await reader.load_async(thumb_stream.size)
                            buffer = reader.read_buffer(thumb_stream.size)
                            
                            image_data = bytes(buffer)
                            image = Image.open(io.BytesIO(image_data))
                            image = image.resize((32, 32)) # Downsample to speed up
                            
                            # Get dominant color excluding too dark/bright colors
                            colors = image.getcolors(32 * 32)
                            # Filter out blacks and whites
                            filtered = [c for c in colors if sum(c[1][:3]) > 50 and sum(c[1][:3]) < 700]
                            if filtered:
                                dominant = max(filtered, key=lambda x: x[0])[1]
                                accent_color = '#{:02x}{:02x}{:02x}'.format(dominant[0], dominant[1], dominant[2])
                            else:
                                # Fallback to average
                                avg = image.resize((1, 1)).getpixel((0, 0))
                                accent_color = '#{:02x}{:02x}{:02x}'.format(avg[0], avg[1], avg[2])
                        except Exception as thumb_e:
                            print(f"Thumbnail error: {thumb_e}")
                except Exception as props_e:
                    print(f"Properties error: {props_e}")
                    title, artist, accent_color = "Unknown Title", "", "#000000"

                self.media_updated.emit(state_str, title, artist, accent_color)
            else:
                self.media_updated.emit("Idle", "", "", "#000000")
        except Exception as e:
            if "remote procedure call failed" in str(e).lower() or "0x800706be" in str(e).lower():
                self.current_session = None
            print(f"Update media info error handled: {e}")

    # Control Methods
    def toggle_play_pause(self):
        if self.current_session and self.loop:
            asyncio.run_coroutine_threadsafe(self._do_toggle(), self.loop)

    async def _do_toggle(self):
        await self.current_session.try_toggle_play_pause_async()

    def next_track(self):
        if self.current_session and self.loop:
            asyncio.run_coroutine_threadsafe(self._do_next(), self.loop)

    async def _do_next(self):
        await self.current_session.try_skip_next_async()

    def prev_track(self):
        if self.current_session and self.loop:
            asyncio.run_coroutine_threadsafe(self._do_prev(), self.loop)

    async def _do_prev(self):
        await self.current_session.try_skip_previous_async()

    def stop(self):
        self._is_running = False
        self.wait()
