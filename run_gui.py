"""This file is for strictly launching the GUI."""
from gui_backend.main_backend import MainWindowBackend

if __name__ == "__main__":
    # Launch the main GUI
    window = MainWindowBackend()
    
    window.app.exec()