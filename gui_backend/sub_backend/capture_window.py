"""Window to allow for capturing and saving data."""
from gui.sub_widgets.capture_window import CaptureWindow
from gui_backend.helpers import _RECEIVER_COUNT
from gui_backend.pull_data import DataHandler, TimeStampData
from gui_backend.sub_backend.view_transforms import ViewTransformsBackend
from gui.main_window import MainWindow
import numpy as np
from numpy.typing import NDArray
from matplotlib.axes import Axes
from typing import List
from PyQt6.QtWidgets import QFileDialog
from gui.helpers import background_color
from pathlib import Path
from datetime import datetime

class CaptureBackend:
    """The backend operations for the capturing window."""
    
    def __init__(self, main_window: MainWindow, sub_window: CaptureWindow, data_handler: DataHandler):
        """Initialize the elements and events for the capture window.
        
        Args:
            main_window: The main gui window.
            sub_window: The window this backend is supporting.
            data_handler: The logic for getting data from another thread.
        """
        self.figure_layout: List[Axes] = []
        self.main_window = main_window
        self.data_handler = data_handler
        self.sub_window = sub_window
        self.transforms_backend = ViewTransformsBackend(self.main_window, self.sub_window.view_transforms_window)
        sub_window.widgets.capture_button_frames.clicked.connect(self.capture_x_frames)
        sub_window.widgets.capture_button_time.clicked.connect(self.capture_for_x_time)
        sub_window.widgets.save_button.clicked.connect(self.find_location_to_save)
        self.data_handler.update_matplotlib.connect(lambda frame: self.update_plots(frame.data))

    def update_plots(self, frame: NDArray[np.float64]):
        self.data_handler.waiting_for_data = False
        self.transforms_backend.run_transformation(frame)
        self.data_handler.waiting_for_data = True

    def find_location_to_save(self):
        """Browse the file explorer for where to save the data."""
        folder = QFileDialog.getExistingDirectory(
            self.main_window, 
            "Select Folder", 
            "" 
        )

        if folder:
            self.sub_window.widgets.save_location.setText(folder)
        else:
            self.sub_window.widgets.save_location.setText("No file selected")

    def capture_x_frames(self):
        """The logic for what the button press should do for capturing x frames."""
        if self.sub_window.widgets.packet_prefix.text():
            packet_name = f"{self.sub_window.widgets.packet_prefix.text()}_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")}"
        else:
            packet_name = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
        
        self.data_handler.capture_for_x_count(
            int(self.sub_window.widgets.input_line.text()), Path(self.sub_window.widgets.save_location.text()) / packet_name
        )
    
    def capture_for_x_time(self):
        """The logic for what the button press should do for capturing for x time."""
        if self.sub_window.widgets.packet_prefix.text():
            packet_name = f"{self.sub_window.widgets.packet_prefix.text()}_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")}"
        else:
            packet_name = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
        
        self.data_handler.capture_for_x_time(
            float(self.sub_window.widgets.input_line.text()), Path(self.sub_window.widgets.save_location.text()) / packet_name
        )
    