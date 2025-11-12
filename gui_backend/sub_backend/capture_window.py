"""Window to allow for capturing and saving data."""
from gui.sub_widgets.capture_window import CaptureWindow
from gui_backend.helpers import _RECEIVER_COUNT
from gui_backend.pull_data import DataHandler, TimeStampData
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
        self.sub_window.widgets.figure.patch.set_facecolor(background_color)
        for receiver in range(1, _RECEIVER_COUNT+1):

            self.figure_layout.append(sub_window.widgets.figure.add_subplot(1, _RECEIVER_COUNT, receiver))
            for spine in self.figure_layout[receiver-1].spines.values():
                spine.set_edgecolor('white')   # color of border lines
                spine.set_linewidth(2) 
            self.figure_layout[receiver-1].patch.set_facecolor(background_color)
            self.figure_layout[receiver-1].set_title(f"Receiver {receiver}", fontsize=10, pad=24, color="white")
            self.figure_layout[receiver-1].tick_params(axis='x', colors='white')
            self.figure_layout[receiver-1].tick_params(axis='y', colors='white')
        sub_window.widgets.capture_button_frames.clicked.connect(self.capture_x_frames)
        sub_window.widgets.capture_button_time.clicked.connect(self.capture_for_x_time)
        sub_window.widgets.save_button.clicked.connect(self.find_location_to_save)
        self.data_handler.update_matplotlib.connect(lambda frame: self.update_graphs(frame))
        
        self.p_color_mesh = None

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
    
    def update_graphs(self, update_graphs: TimeStampData):
        """Update the matplotlib graphs with new data.

        Args:
            update_graphs: The time stamped data to update the graphs with.
        """
        num_rx_antennas, num_chirps_per_frame, num_samples_per_chirp = update_graphs.data.shape
        if self.p_color_mesh is None:
            self.p_color_mesh = []
            for receiver in range(_RECEIVER_COUNT):
                self.p_color_mesh.append(self.figure_layout[receiver].pcolormesh(
                    np.arange(num_samples_per_chirp), np.arange(num_chirps_per_frame), update_graphs.data[receiver, :, :], shading="gouraud"
                ))
            self.figure_layout[0].set_xlabel("Time in Seconds (s)", fontsize=14)
            self.figure_layout[0].set_ylabel("Frequencies (Hz)", fontsize=14)

            self.figure_layout[0].figure.colorbar(self.p_color_mesh[-1], label='Power (dB)', ax=self.figure_layout[0])
            self.figure_layout[0].figure.canvas.draw_idle()
            self.p_color_mesh[-1].autoscale()
                
        for receiver in range(_RECEIVER_COUNT):
            self.p_color_mesh[receiver].set_array(update_graphs.data[receiver, :, :])
            self.figure_layout[receiver].figure.canvas.draw_idle()
