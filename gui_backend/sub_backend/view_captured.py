
from gui.sub_widgets.view_captured import ViewCaptured
from gui_backend.sub_backend.view_transforms import ViewTransformsBackend, _GRAB_SPEED
from gui.main_window import MainWindow
from PyQt6.QtWidgets import QFileDialog
from PyQt6 import QtCore, QtWidgets
import os
import numpy as np
from numpy.typing import NDArray
from functools import partial
from gui_backend.helpers import TimeStampData, _CHIRP_INFO, CreateLine, _DATETIME_FORMAT, _CHIRP_DICT_START
from dataclasses import dataclass
from datetime import datetime
from typing import List, Callable, Optional
import json
import time


@dataclass
class TimeStampedSession:
    session_name: str
    session_chirp_list: List[CreateLine]
    time_stamp_session: float
    time_stamp_data: List[TimeStampData]

class PlayWorker(QtCore.QObject):
    move_to_next_frame = QtCore.pyqtSignal()
    pause_player_signal = QtCore.pyqtSignal()
    begin_player = QtCore.pyqtSignal(int, float, float, list)
    finished = QtCore.pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.paused = False
        self.pause_player_signal.connect(self.pause_player)
        self.begin_player.connect(self.start_play)
    
    def pause_player(self):
        self.paused = True
    
    def start_play(self, starting_time_stamp: int, minimum_speed: float, playback_speed: float, time_stamp_data: List[float]):
        previous_time = time.time()
        current_time_stamp = starting_time_stamp
        while current_time_stamp < len(time_stamp_data) - 1:
            if self.paused:
                break
            current_time = time.time()
            if playback_speed == 0:
                frame_time_stamp = time_stamp_data[current_time_stamp]
                next_frame_time_stamp = time_stamp_data[current_time_stamp+1]
                wait_time = max(next_frame_time_stamp - frame_time_stamp, minimum_speed)
            else:
                wait_time = playback_speed
            
            if current_time - previous_time > wait_time:
                self.move_to_next_frame.emit()
                previous_time = current_time
                current_time_stamp += 1
        self.finished.emit()


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
        self.main_window.sub_window_widgets.render_control.widgets.next_session.clicked.connect(self.next_session)
        self.main_window.sub_window_widgets.render_control.widgets.prev_session.clicked.connect(self.prev_session)
        
        self.main_window.sub_window_widgets.render_control.widgets.replay_button.clicked.connect(self.replay_frames)
        self.main_window.sub_window_widgets.render_control.widgets.play_button.clicked.connect(self.play_frames_from_index)
        self.main_window.sub_window_widgets.render_control.widgets.pause_button.clicked.connect(self.pause_player)
        
        self.main_window.sub_window_widgets.render_control.widgets.playback_speed.line_edit.textEdited.connect(self.set_playback_speed)
        
        self.sub_window.widgets.save_file_explorer.clicked.connect(self.find_location_to_save)
        self.sub_window.widgets.apply_transform.clicked.connect(self.apply_transform_and_save)
        
        self.session_list = []
        
        self.transforms_backend = ViewTransformsBackend(
            self.main_window, self.sub_window.view_transforms_window, self.stop_everything, self.handle_change_operations
        )
        self.timestamp_change_operations = []
        self.current_timestamp = 0
        self.current_session = 0
        self.player_thread: Optional[QtCore.QThread] = None
        self.current_player: Optional[PlayWorker] = None
        # grab speed is in ms, convert to s * 4
        self.minimum_speed = _GRAB_SPEED * 4.0e-3
        self.playback_speed = 0
    
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
            self.current_session = 0
            self.current_timestamp = 0
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
                        
                        file_name, _ = os.path.splitext(file)
                        file_date_time, _, chirp_id = file_name.rpartition("_")
                        if previous_date_time is not None and file_date_time != previous_date_time:
                            file_timestamp = datetime.strptime(file_date_time, _DATETIME_FORMAT).timestamp()
                            time_stamped_data.append(TimeStampData(session_name, file_timestamp, chirp_data.copy()))
                            chirp_data = []
                        chirp_data.append(frame_data)
                        previous_date_time = file_date_time
                else:
                    time_stamped_data.append(TimeStampData(session_name, file_timestamp, chirp_data))
                
                chirp_info_list = [CreateLine("", 0.0, 0.0, 0.0)] * len(json_dictionary[_CHIRP_DICT_START])
                for dict_chirp_info, chirp_info in zip(json_dictionary[_CHIRP_DICT_START], chirp_info_list):
                    chirp_info.set_json_dictionary(dict_chirp_info)
                    
                self.session_list.append(TimeStampedSession(
                    session_name = session_name,
                    session_chirp_list = chirp_info_list,
                    time_stamp_session = directory_time_stamp,
                    time_stamp_data=time_stamped_data,
                ))
       
            self.main_window.sub_window_widgets.render_control.widgets.which_session.setMaximum(len(self.session_list) - 1)
            self.transforms_backend.iterate_through_each_view_tab(
                self.session_list[self.current_session].time_stamp_data[self.current_timestamp]
            )

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

    def handle_change_operations(self):
        while True:
            try:
                self.timestamp_change_operations.pop(0)()
            except IndexError:
                return
 
    def stop_everything(self):
        self.paused = True
        self.timestamp_change_operations = []
 
    def set_time_stamp(self, time_stamp_location: int, callback: bool = True) -> None:
        self.current_timestamp = max(min(time_stamp_location, len(self.session_list[self.current_session].time_stamp_data) -1 ), 0)
        if callback:
            self.set_entry_value(self.current_timestamp)
        
    def set_session(self, session_location: int, callback: bool = True) -> None:
        self.current_session = max(min(session_location, len(self.session_list) -1 ), 0)
        if callback:
            self.set_slider_pos(self.current_session)
    
    def set_slider_pos(self, slider_pos: int):
        self.sub_window.render_window.widgets.which_session.setValue(slider_pos)
    
    def set_entry_value(self, time_stamp: int):
        self.sub_window.render_window.widgets.which_data.setInnerText(str(time_stamp))
        
    
    def on_slider_change(self, index_to_move_to: int) -> None:
        self.timestamp_change_operations.append(partial(self.set_session, index_to_move_to, False))
        self.transforms_backend.iterate_through_each_view_tab(self.session_list[index_to_move_to].time_stamp_data[self.current_timestamp])

    def next_session(self):
        if self.current_session + 1 > len(self.session_list) - 1:
            return
        
        self.timestamp_change_operations.append(partial(self.set_session, self.current_session+1))
        self.transforms_backend.iterate_through_each_view_tab(self.session_list[self.current_session].time_stamp_data[self.current_timestamp+1])

    def prev_session(self):
        if self.current_session - 1 < 0:
            return
        self.timestamp_change_operations.append(partial(self.set_session, self.current_session-1))
        self.transforms_backend.iterate_through_each_view_tab(self.session_list[self.current_session].time_stamp_data[self.current_timestamp+1])

    def on_time_stamp_change(self, index_to_move_to: int) -> None:
        self.timestamp_change_operations.append(partial(self.set_time_stamp, index_to_move_to, False))
        self.transforms_backend.iterate_through_each_view_tab(self.session_list[self.current_session].time_stamp_data[index_to_move_to])

    def next_plot(self):
        if self.current_timestamp + 1 > len(self.session_list[self.current_session].time_stamp_data) - 1:
            return
        
        self.timestamp_change_operations.append(partial(self.set_time_stamp, self.current_timestamp+1))
        self.transforms_backend.iterate_through_each_view_tab(self.session_list[self.current_session].time_stamp_data[self.current_timestamp+1])

    def prev_plot(self):
        if self.current_timestamp - 1 < 0:
            return
        
        self.timestamp_change_operations.append(partial(self.set_time_stamp, self.current_timestamp-1))
        self.transforms_backend.iterate_through_each_view_tab(self.session_list[self.current_session].time_stamp_data[self.current_timestamp-1])

    def set_playback_speed(self):
        playback_speed = self.sub_window.render_window.widgets.playback_speed.getInnerText()
        if playback_speed == 0:
            self.playback_speed = 0
        else:
            self.playback_speed = max(self.minimum_speed, self.sub_window.render_window.widgets.playback_speed.getInnerText())
        self.sub_window.render_window.widgets.playback_speed.setInnerText(self.playback_speed)

    def replay_frames(self, finished_playback: Optional[Callable] = None):
        self.paused = False
        self.current_timestamp = 0
        self.play_frames(self.pause_player)
        
    def play_frames_from_index(self):
        self.play_frames(self.pause_player)

    def pause_player(self):
        if self.current_player is not None:
            self.current_player.pause_player_signal.emit()
            self.current_player = None
            self.player_thread.quit()
            self.player_thread.wait()
            self.player_thread = None
            
    def play_frames(self, finished_playback: Callable):
        self.player_thread = QtCore.QThread()
        
        self.current_player = PlayWorker()
        self.current_player.moveToThread(self.player_thread)
        self.current_player.move_to_next_frame.connect(self.next_plot)
        playback_speeds = [time_stamp_data.time_stamp for time_stamp_data in self.session_list[self.current_session].time_stamp_data]
        
        self.player_thread.started.connect(
            lambda: self.current_player.begin_player.emit(self.current_timestamp, self.minimum_speed, self.playback_speed, playback_speeds)
        )
        
        self.player_thread.start()
        self.current_player.finished.connect(finished_playback)        

    def post_transform_data_handling(self, transform_data: TimeStampData):
        location = self.sub_window.widgets.save_location
        for sampling_number, sampling_data in enumerate(transform_data.data):
            np.save(f"{location}/{datetime.fromtimestamp(transform_data.time_stamp).strftime(_DATETIME_FORMAT)}_{sampling_number}", sampling_data)

    def apply_transform_and_save(self):
        self.transforms_backend.callback_new_transform_data = self.post_transform_data_handling
        for sequence in self.session_list:
            self.replay_frames()
