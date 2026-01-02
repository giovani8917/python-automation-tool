import threading
import pystray
from PIL import Image, ImageDraw

class TrayManager:
    """
    Manages the system tray integration using pystray.
    """
    def __init__(self, root, on_open, on_quit):
        self.root = root
        self.on_open = on_open
        self.on_quit = on_quit
        self.tray_icon = None

    def minimize_to_tray(self, window_title="Asistente"):
        self.root.withdraw()
        
        if not self.tray_icon:
            image = Image.new('RGB', (64, 64), color=(0, 0, 0))
            d = ImageDraw.Draw(image)
            d.rectangle((16, 16, 48, 48), fill=(200, 200, 200))
            
            menu = pystray.Menu(
                pystray.MenuItem('Abrir', self.on_open),
                pystray.MenuItem('Salir', self.on_quit)
            )
            self.tray_icon = pystray.Icon("automations", image, window_title, menu)
            
        if not self.tray_icon.visible:
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def stop(self):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
