"""The main window wrapper that holds everything."""
from gui.main_window import start_application, MainWindow
from gui_backend.sub_backend.data_handler import VisualizationWrapper
from PyQt6 import QtCore, QtGui

_PATH_TO_ICON = "radar.png"

class MainWindowBackend(QtCore.QObject):
    """Wrapper around the window, to handle data."""
    
    def __init__(self) -> None:
        """Initialize the wrapper around the window object for pyqt."""
        # lookup table for classification colors
        super().__init__()
        self.app = start_application()
        self.runner = None
        self.window = MainWindow()
        self.window.showMaximized()
        self.window.setWindowIcon(QtGui.QIcon(_PATH_TO_ICON))
        self.circuit_initialized = False
        self.bloch_backend = VisualizationWrapper(self.window)
        self.window.save_button.clicked.connect(self.window.get_json_dictionary)
        self.window.load_button.clicked.connect(self.window.set_json_dictionary)
        