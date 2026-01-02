import logging
import tkinter as tk

from src.ui import MainWindow
from src.utils import setup_logging


def main():
    setup_logging()
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logger = logging.getLogger("main")
    logger.info("Application starting...")

    root = tk.Tk()
    # Apply theme or improved aesthetics here if desired later
    try:
        app = MainWindow(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
