"""The wrapper around all sub window backends."""
import matplotlib

from PyQt6.QtCore import QTimer
from gui.main_window import MainWindow
from gui_backend.sub_backend.view_captured import ViewCapturedBackend
from gui_backend.sub_backend.capture_window import CaptureBackend
from gui_backend.sub_backend.signal_window import SignalWindowBackend
from gui_backend.pull_data import DataHandler
from functools import partial
matplotlib.use("TkAgg")

class VisualizationWrapper():
    """Manage data that goes between each back end."""
    
    def __init__(self, main_window: MainWindow) -> None:
        """Initialize the wrapper with info from the main window gui.

        Args:
            main_window: The main gui window.
        """
        
        self.data_handler = DataHandler()
        self.timer = QTimer()
        self.timer.timeout.connect(self.data_handler.poll_data_queue)
        self.timer.start(100)  # check every 100ms
        
        self.main_window = main_window
        self.view_captured = ViewCapturedBackend(self.main_window, self.main_window.sub_window_widgets.view_captured, self.data_handler)
        self.capture = CaptureBackend(self.main_window, self.main_window.sub_window_widgets.capture_window, self.data_handler)
        self.signals = SignalWindowBackend(self.main_window, self.main_window.sub_window_widgets.signal_window, self.data_handler)