"""Window to allow for capturing and saving data."""
from gui.sub_widgets.capture_window import CaptureWindow
from gui_backend.helpers import _RECEIVER_COUNT, TimeStampData, _DATETIME_FORMAT
from gui_backend.pull_data import DataHandler, TimeStampData
from gui_backend.sub_backend.view_transforms import ViewTransformsBackend
from gui.main_window import MainWindow
import numpy as np
from numpy.typing import NDArray
from matplotlib.axes import Axes
from typing import List, Optional
from PyQt6 import QtCore, QtWidgets
from gui.helpers import background_color
from pathlib import Path
from datetime import datetime


class CaptureBackend(QtCore.QObject):
    """The backend operations for the capturing window."""
    
    def __init__(self, main_window: MainWindow, sub_window: CaptureWindow, data_handler: DataHandler):
        """Initialize the elements and events for the capture window.
        
        Args:
            main_window: The main gui window.
            sub_window: The window this backend is supporting.
            data_handler: The logic for getting data from another thread.
        """
        super().__init__()
        self.figure_layout: List[Axes] = []
        self.main_window = main_window
        self.data_handler = data_handler
        self.sub_window = sub_window
        self.transforms_backend = ViewTransformsBackend(
            self.main_window, 
            self.sub_window.view_transforms_window,
            self.data_handler.stop_acquisition,
            self.send_out_next_frame
        )
        sub_window.widgets.capture_button_frames.clicked.connect(self.capture_x_frames)
        sub_window.widgets.capture_button_time.clicked.connect(self.capture_for_x_time)
        sub_window.widgets.save_button.clicked.connect(self.find_location_to_save)

        sub_window.widgets.start_no_data_acquisitions.clicked.connect(lambda: self.data_handler.start_no_data_acquisition())        
        sub_window.widgets.start_acquisitions.clicked.connect(lambda: self.data_handler.start_acquisition())
        sub_window.widgets.stop_acquisitions.clicked.connect(lambda: self.data_handler.stop_acquisition())
        self.data_handler.update_matplotlib.connect(lambda time_stamp_data: self.update_plots(time_stamp_data))
        self.data_handler.updated_sequence.connect(lambda chirp_info: self.transforms_backend.create_new_chirp_views(*chirp_info))

    def send_out_next_frame(self):
        """Send out the next frame to the display."""
        if not self.data_handler.waiting_for_data:
            self.data_handler.waiting_for_data = True

    def update_plots(self, time_stamp_data: Optional[TimeStampData]):
        """Update the plots in the view transforms.

        Args:
            frame
        """
        if time_stamp_data is not None:
            self.transforms_backend.iterate_through_each_view_tab(time_stamp_data.data)
        else:
            self.transforms_backend.iterate_through_each_view_tab(time_stamp_data)

    def find_location_to_save(self):
        """Browse the file explorer for where to save the data."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.main_window, 
            "Select Folder", 
            "" 
        )

        if folder:
            self.sub_window.widgets.save_location.setInnerText(folder)
        else:
            self.sub_window.widgets.save_location.setInnerText("No file selected")

    def capture_x_frames(self):
        """The logic for what the button press should do for capturing x frames."""
        if self.sub_window.widgets.packet_prefix.getInnerText() != "":
            packet_name = f"{self.sub_window.widgets.packet_prefix.getInnerText()}_{datetime.now().strftime(_DATETIME_FORMAT)}"
        else:
            packet_name = datetime.now().strftime(_DATETIME_FORMAT)
        
        capture_count = self.sub_window.widgets.amount_to_capture.getInnerText()
        
        if capture_count == "":
            capture_count = 0
        
        self.data_handler.capture_for_x_count(
            int(capture_count), Path(self.sub_window.widgets.save_location.getInnerText()) / packet_name
        )
    
    def capture_for_x_time(self):
        """The logic for what the button press should do for capturing for x time."""
        if self.sub_window.widgets.packet_prefix.getInnerText() != "":
            packet_name = f"{self.sub_window.widgets.packet_prefix.getInnerText()}_{datetime.now().strftime(_DATETIME_FORMAT)}"
        else:
            packet_name = datetime.now().strftime(_DATETIME_FORMAT)
        
        capture_time = self.sub_window.widgets.amount_to_capture.getInnerText()
        
        if capture_time == "":
            capture_time = 0.0
        
        self.data_handler.capture_for_x_time(
            float(capture_time), Path(self.sub_window.widgets.save_location.getInnerText()) / packet_name
        )
    