
from gui.sub_widgets.view_captured import ViewCaptured
from gui_backend.sub_backend.view_transforms import ViewTransformsBackend
from gui.main_window import MainWindow
from PyQt6.QtWidgets import QFileDialog
import os
import numpy as np
from numpy.typing import NDArray
from functools import partial
from gui_backend.helpers import TimeStampData, _CHIRP_INFO, CreateLine, _DATETIME_FORMAT, _CHIRP_DICT_START
from dataclasses import dataclass
from datetime import datetime
from typing import List
import json

@dataclass
class TimeStampedSession:
    session_name: str
    session_chirp_list: List[CreateLine]
    time_stamp_session: float
    time_stamp_data: List[TimeStampData]

class ViewCapturedBackend:
    """Visualize the transforms provided from methods in another file."""
    
    def __init__(self, main_window: MainWindow, sub_window: ViewCaptured, data_handler):
        """Initialize the elements and events for the view transforms window.
        
        Args:
            main_window: The main gui window.
            sub_window: The window this backend is supporting.
        """
        self.main_window = main_window
        self.sub_window = sub_window
        self.data_handler = data_handler
        self.current_folder = None
        sub_window.widgets.load_button.clicked.connect(self.find_location_to_load)
        # self.main_window.sub_window_widgets.render_control.widgets.which_bloch.valueChanged.connect(self.on_slider_change)
        self.main_window.sub_window_widgets.render_control.widgets.next_button.clicked.connect(self.next_plot)
        self.main_window.sub_window_widgets.render_control.widgets.prev_button.clicked.connect(self.prev_plot)
        
        # self.transforms_backend = ViewTransformsBackend(self.main_window, self.sub_window.view_transforms_window, None, None)
        self.index_change_operations = []
        self.data_list = []
        self.file_names = []
    
    def stop_loading(self):
        self.allow_loading = False
        
    def find_location_to_load(self):
        """Use the file explorer to determine where to load the data from."""
        folder = QFileDialog.getExistingDirectory(
            self.main_window, 
            "Select Folder", 
            "" 
        )

        if folder:
            self.current_folder = folder
            self.session_list: List[TimeStampedSession] = []
            self.current_index = 0
            for root, directories, files in os.walk(folder):
                if not files:
                    continue
                time_stamped_data: List[TimeStampData] = []
                chirp_data: List[NDArray[np.float64]] = []
                try:
                   session_name, _, directory_date_time = os.path.basename(os.path.normpath(root)).partition("_")
                except AttributeError:
                    continue
                   
                try:
                    directory_time_stamp = datetime.strptime(directory_date_time, _DATETIME_FORMAT).timestamp()
                except:
                    continue
                previous_date_time = None
                for file in files:

                    if file == _CHIRP_INFO:
                        with open(os.path.join(root,file), "r") as file_pointer:
                            json_dictionary = json.load(file_pointer)
                        
                    else:
                        frame_data = np.load(os.path.join(root,file))
                        chirp_data.append(frame_data)
                        file_name, _ = os.path.splitext(file)
                        file_date_time, _, chirp_id = file_name.rpartition("_")
                        if previous_date_time is not None and file_date_time != previous_date_time:
                            file_timestamp = datetime.strptime(file_date_time, _DATETIME_FORMAT).timestamp()
                            time_stamped_data.append(TimeStampData(file_timestamp, chirp_data))
                            chirp_data = []
                        previous_date_time = file_date_time
                else:
                    time_stamped_data.append(TimeStampData(file_timestamp, frame_data))
                
                chirp_info_list = [CreateLine("", 0.0, 0.0, 0.0)] * len(json_dictionary[_CHIRP_DICT_START])
                for dict_chirp_info, chirp_info in zip(json_dictionary[_CHIRP_DICT_START], chirp_info_list):
                    chirp_info.set_json_dictionary(dict_chirp_info)
                    
                self.session_list.append(TimeStampedSession(
                    session_name = session_name,
                    session_chirp_list = chirp_info_list,
                    time_stamp_session = directory_time_stamp,
                    time_stamp_data=time_stamped_data,
                ))
                
                
       
            self.main_window.sub_window_widgets.render_control.widgets.which_bloch.setMaximum(len(self.file_names) - 1)
            self.transforms_backend.run_transformation(self.data_list[self.current_index])
 
    def set_index(self, index_to_move_to: int) -> None:
        self.current_index = index_to_move_to
 
    def on_slider_change(self, index_to_move_to) -> None:
        self.index_change_operations.append(partial(self.set_index, index_to_move_to))
        self.transforms_backend.iterate_through_each_view_tab(self.data_list[self.current_index])

    def next_plot(self):
        next_index = 1 if self.current_index < (len(self.data_list) - 1) else 0
        self.transforms_backend.run_transformation(self.data_list[next_index])
        self.current_index = next_index
        
    def prev_plot(self):
        self.current_index -= 1 if self.current_index > 0 else 0
        self.transforms_backend.run_transformation(self.data_list[self.current_index])
    
