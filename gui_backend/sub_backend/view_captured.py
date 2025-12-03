
from gui.sub_widgets.view_captured import ViewCaptured
from gui_backend.sub_backend.view_transforms import ViewTransformsBackend, _GRAB_SPEED
from gui.main_window import MainWindow
from gui.helpers import _NO_DATA_EDIT, _SEPERATE_FIRST_DIM, LoadType, TertiaryData, PerSubPlot, Label
from PyQt6.QtWidgets import QFileDialog
from PyQt6 import QtCore, QtWidgets
import os
import numpy as np
from numpy.typing import NDArray
from functools import partial
from gui_backend.helpers import TimeStampData, _CHIRP_INFO, CreateLine, _DATETIME_FORMAT, _CHIRP_DICT_START
from dataclasses import dataclass
from datetime import datetime
from typing import List, Callable, Optional, Dict
import json
import time
from pathlib import Path

class TimeStampedSession:    
    def __init__(
        self,
        session_name: str,
        session_chirp_list: List[CreateLine],
        time_stamp_session: float,
        time_stamp_data: List[TimeStampData],
    ):
        self.session_name = session_name
        self.session_chirp_list = session_chirp_list
        self.time_stamp_session = time_stamp_session
        self.time_stamp_data = time_stamp_data
    
        self._temporary_data: Dict[str, List[TimeStampData]] = {}

    def add_data(self, new_data: List[TimeStampData], index: int):
        self._temporary_data[index] = new_data
    
    def create_concatination(self, append_type: str):
        if append_type == LoadType.NO_APPEND.value:
            return
        
        # this can be optimized a lot
        sorted_keys = sorted(self._temporary_data.keys())
        ordered_dict = {key: self._temporary_data[key] for key in sorted_keys}
        for new_timestamp in ordered_dict.values():
            current_data_index = len(self.time_stamp_data) - 1
                    
            current_data = self.time_stamp_data[current_data_index]
            while len(new_timestamp) > len(self.time_stamp_data):
                self.time_stamp_data.append(TimeStampData(
                    name=current_data.name, 
                    time_stamp=current_data.time_stamp, 
                    data=self.time_stamp_data[current_data_index].data.copy(), 
                    transform=current_data.transform
                ))
        
        for time_stamp_index, time_stamp_data in enumerate(self.time_stamp_data):
            chirp_size = 0
            for chirp_index, chirp_data in enumerate(new_timestamp[time_stamp_index].data):
                chirp_size += chirp_data.shape[-1]*(len(ordered_dict) + 1)
                                   
            new_array = np.empty(chirp_data.shape[:-1] + (chirp_size, ))
            
            start_index = 0

            for chirp_index, chirp_data in enumerate(time_stamp_data.data):
                end_index = start_index + time_stamp_data.data[chirp_index].shape[-1]
                new_array[..., start_index:end_index] = time_stamp_data.data[chirp_index] 
                start_index = end_index 

            for new_index, new_timestamp in enumerate(ordered_dict.values()):
                for chirp_index, chirp_data in enumerate(time_stamp_data.data):
                    end_index = start_index + chirp_data.shape[-1]
                    last_timestamp = min(len(new_timestamp)-1, time_stamp_index)
                    new_array[..., start_index:end_index] = new_timestamp[last_timestamp].data[chirp_index]
                    start_index = end_index
            self.time_stamp_data[time_stamp_index].data = [new_array]
        
        del self._temporary_data

"""        for time_stamp_index, time_stamp_data in enumerate(self.time_stamp_data):
            
            for chirp_index, chirp_data in enumerate(time_stamp_data.data):
                new_array = np.empty(chirp_data.shape[:-1] + (chirp_data.shape[-1]*(len(ordered_dict) + 1), ))
                new_array[..., :chirp_data.shape[-1]] = time_stamp_data.data[chirp_index]
                for new_index, new_timestamp in enumerate(ordered_dict.values()):
                    last_timestamp = min(len(new_timestamp)-1, time_stamp_index)
                    new_array[..., (new_index+1)*chirp_data.shape[-1]:(new_index+2)*chirp_data.shape[-1]] = new_timestamp[last_timestamp].data[chirp_index]
                   
                self.time_stamp_data[time_stamp_index].data[chirp_index] = new_array
        
        del self._temporary_data"""

class PlayWorker(QtCore.QObject):
    move_to_next_frame = QtCore.pyqtSignal()
    pause_player_signal = QtCore.pyqtSignal()
    begin_player = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        playback_speed: float, 
        number_of_runs: int,
    ):
        super().__init__()
        self.paused = False
        self.pause_player_signal.connect(self.pause_player)
        self.begin_player.connect(self.start_play)
        self.current_run = 0
        self.number_of_runs = number_of_runs
        self.playback_speed = playback_speed
        self.running = True

    
    def pause_player(self):
        self.paused = True
    
    def next_frame(self):
        if self.running:
            return
        self.running = True
        
        
        self.current_run += 1
        self.start_play()
    
    def start_play(self):
        if self.current_run >= self.number_of_runs - 1 or self.paused:
            self.finished.emit()
            return

        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(int(self.playback_speed * 1000), loop.quit)
        loop.exec()

        self.move_to_next_frame.emit()
        self.running = False

class ViewCapturedBackend(QtCore.QObject):
    """Visualize the transforms provided from methods in another file."""
    callback_trigger = QtCore.pyqtSignal()
    
    def __init__(self, main_window: MainWindow, sub_window: ViewCaptured, data_handler):
        """Initialize the elements and events for the view transforms window.
        
        Args:
            main_window: The main gui window.
            sub_window: The window this backend is supporting.
        """
        super().__init__()
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
        
        self.main_window.sub_window_widgets.render_control.widgets.replay_button.clicked.connect(partial(self.replay_frames, self.pause_player))
        self.main_window.sub_window_widgets.render_control.widgets.play_button.clicked.connect(self.play_frames_from_index)
        self.main_window.sub_window_widgets.render_control.widgets.pause_button.clicked.connect(self.pause_player)
        
        self.main_window.sub_window_widgets.render_control.widgets.playback_speed.line_edit.textEdited.connect(self.set_playback_speed)
        
        self.sub_window.widgets.save_file_explorer.clicked.connect(self.find_location_to_save)
        self.sub_window.widgets.apply_transform.clicked.connect(self.apply_transform_and_save)
        
        self.session_dict = {}
        
        self.transforms_backend = ViewTransformsBackend(
            self.main_window, self.sub_window.view_transforms_window, self.stop_everything, self.handle_change_operations
        )
        self.timestamp_change_operations = []
        self.displayed_data: Optional[TimeStampData] = None
        self.current_timestamp = 0
        self.current_session = 0
        self.player_thread: Optional[QtCore.QThread] = None
        self.current_player: Optional[PlayWorker] = None
        # grab speed is in ms, convert to s * 4
        self.minimum_speed = _GRAB_SPEED * 4.0e-3
        self.playback_speed = 0
        
        self.loop_until_next_session = QtCore.QEventLoop()
        self.finished_operation = None
        self.info_signal: QtCore.pyqtSignal = None
        self.index_to_label = []
        
        self.minimum_value = float("inf")
        self.maximum_value = -float("inf")
        self.tertiary_data = TertiaryData()
        self.tertiary_data.graph_info.per_subplot_info.append(PerSubPlot())
        self.tertiary_data.graph_info.per_subplot_info.append(PerSubPlot())
        self.tertiary_data.graph_info.per_subplot_info.append(PerSubPlot())

    
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
            self.minimum_value = float("inf")
            self.maximum_value = -float("inf")
            self.current_folder = folder
            self.session_dict: Dict[str, TimeStampedSession] = {}
            self.current_session = 0
            self.current_timestamp = 0

            self.index_to_label = []
            
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

                prefix, index, label = session_name.split("-")
                
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
                
                if self.sub_window.widgets.load_operation.getInnerText() == LoadType.NO_APPEND.value:
                    label += index
                
                if label not in self.session_dict:
                    self.index_to_label.append(label)
                    self.session_dict[label] = (TimeStampedSession(
                        session_name = prefix,
                        session_chirp_list = chirp_info_list,
                        time_stamp_session = directory_time_stamp,
                        time_stamp_data=time_stamped_data,
                    ))
                else:
                    self.session_dict[label].add_data(time_stamped_data, index)
       
       
            for session in self.session_dict.values():
                session.create_concatination(self.sub_window.widgets.load_operation.getInnerText())
            self.on_time_stamp_change(0)

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
        try:
            self.timestamp_change_operations.pop(0)()
            if self.finished_operation is not None:
                self.finished_operation()
        except IndexError:
            return
 
    def data_processing(self, data: TimeStampData):
        minimum = np.min(data.data)
        maximum = np.max(data.data)
        
        if maximum > self.maximum_value:
            self.maximum_value = maximum
        if minimum < self.minimum_value:
            self.minimum_value = minimum
        self.displayed_data = data
 
    def stop_everything(self):
        self.paused = True
        self.timestamp_change_operations = []
 
    def set_time_stamp(self, time_stamp_location: int, callback: bool = True) -> None:
        current_session = self.session_dict[self.index_to_label[self.current_session]]
        self.current_timestamp = max(min(time_stamp_location, len(current_session.time_stamp_data) -1 ), 0)
        if callback:
            self.set_entry_value(self.current_timestamp)
        
    def set_session(self, session_location: int, callback: bool = True) -> None:
        self.current_session = max(min(session_location, len(self.session_dict) -1 ), 0)
        if callback:
            self.set_slider_pos(self.current_session)
    
    def set_slider_pos(self, slider_pos: int):
        self.sub_window.render_window.widgets.which_session.setValue(slider_pos)
    
    def set_entry_value(self, time_stamp: int):
        self.sub_window.render_window.widgets.which_data.setInnerText(str(time_stamp))
        
    def on_slider_change(self, index_to_move_to: int) -> None:
        self.current_timestamp = 0
        current_session = self.session_dict[self.index_to_label[self.current_session]]
        self.transforms_backend.iterate_through_each_view_tab(current_session.time_stamp_data[self.current_timestamp], self.tertiary_data)
        self.timestamp_change_operations.append(partial(self.set_session, index_to_move_to, False))

    def next_session(self):
        self.current_timestamp = 0
        if self.current_session + 1 > len(self.session_dict) - 1:
            return False
        
        next_session = self.session_dict[self.index_to_label[self.current_session+1]]
        first_timestamp = next_session.time_stamp_data[self.current_timestamp]
        self.data_processing(first_timestamp)
        self.transforms_backend.iterate_through_each_view_tab(first_timestamp, self.tertiary_data)
        self.timestamp_change_operations.append(partial(self.set_session, self.current_session+1))
        return True

    def prev_session(self):
        self.current_timestamp = 0
        if self.current_session - 1 < 0:
            return False
        
        prev_session = self.session_dict[self.index_to_label[self.current_session-1]]
        first_timestamp = prev_session.time_stamp_data[self.current_timestamp]
        self.data_processing(first_timestamp)
        self.transforms_backend.iterate_through_each_view_tab(first_timestamp, self.tertiary_data)
        self.timestamp_change_operations.append(partial(self.set_session, self.current_session-1))
        return True

    def on_time_stamp_change(self, index_to_move_to: int) -> None:
        current_session = self.session_dict[self.index_to_label[self.current_session]]
        self.transforms_backend.iterate_through_each_view_tab(current_session.time_stamp_data[index_to_move_to], self.tertiary_data)
        self.timestamp_change_operations.append(partial(self.set_time_stamp, index_to_move_to, False))

    def next_plot(self):
        current_session = self.session_dict[self.index_to_label[self.current_session]]
        if self.current_timestamp + 1 > len(current_session.time_stamp_data) - 1:
            return False
        next_viewing_data = current_session.time_stamp_data[self.current_timestamp+1]
        self.data_processing(next_viewing_data)
        self.transforms_backend.iterate_through_each_view_tab(next_viewing_data, self.tertiary_data)
        self.timestamp_change_operations.append(partial(self.set_time_stamp, self.current_timestamp+1))
        return True

    def prev_plot(self):
        current_session = self.session_dict[self.index_to_label[self.current_session]]
        if self.current_timestamp - 1 < 0:
            return False
        
        prev_viewing_data = current_session.time_stamp_data[self.current_timestamp-1]
        self.data_processing(prev_viewing_data)
        self.transforms_backend.iterate_through_each_view_tab(prev_viewing_data, self.tertiary_data)
        self.timestamp_change_operations.append(partial(self.set_time_stamp, self.current_timestamp-1))
        return True

    def set_playback_speed(self):
        playback_speed = self.sub_window.render_window.widgets.playback_speed.getInnerText()
        if playback_speed == 0:
            self.playback_speed = 0
        else:
            self.playback_speed = max(self.minimum_speed, self.sub_window.render_window.widgets.playback_speed.getInnerText())
        self.sub_window.render_window.widgets.playback_speed.setInnerText(self.playback_speed)

    def replay_frames(self, finished_playback: Optional[Callable] = None):
        self.current_timestamp = 0
        self.play_frames(finished_playback)
        
    def play_frames_from_index(self):
        self.play_frames(self.pause_player)

    def pause_player(self):
        if self.current_player is not None:
            self.finished_operation = None
            self.current_player.pause_player_signal.emit()
            self.current_player = None
            self.player_thread.quit()
            self.player_thread.wait()
            self.player_thread = None

    def play_frames(self, finished_playback: Callable):
        self.player_thread = QtCore.QThread()
        current_session = self.session_dict[self.index_to_label[self.current_session]]        
        if self.playback_speed == 0:

            second_timestamp = current_session.time_stamp_data[1].time_stamp
            first_timestamp = current_session.time_stamp_data[0].time_stamp
            playback_speed = max(second_timestamp - first_timestamp, self.minimum_speed)
        else:
            playback_speed = self.playback_speed
        
        number_of_runs = len(current_session.time_stamp_data) - self.current_timestamp
        
        self.current_player = PlayWorker(playback_speed, number_of_runs)
        self.current_player.moveToThread(self.player_thread)
        self.current_player.move_to_next_frame.connect(self.next_plot)
        
        self.player_thread.started.connect(
            lambda: self.current_player.begin_player.emit()
        )
        self.callback_trigger.connect(self.current_player.next_frame)
        self.finished_operation = lambda: self.callback_trigger.emit()
        self.current_player.finished.connect(finished_playback)  
        
        self.info_signal.emit(f"Started {current_session.session_name}")
        self.player_thread.start()

      
    def post_transform_manipulation(self, transform_data: NDArray[np.float64]):
        if _NO_DATA_EDIT == self.sub_window.widgets.post_transform.getInnerText():
            yield transform_data
        elif _SEPERATE_FIRST_DIM == self.sub_window.widgets.post_transform.getInnerText():
            for section in np.reshape(transform_data, (-1, transform_data.shape[-1])):
                yield section

    def post_transform_data_handling(self, transform_data: TimeStampData):
        location = Path(f"{self.sub_window.widgets.save_location.getInnerText()}/{transform_data.transform}")
        location.mkdir(exist_ok=True)
        Path(f"{location}/{transform_data.name}").mkdir(exist_ok=True)
        
        for sampling_number, sampling_data in enumerate(transform_data.data):
            for section, save_data in enumerate(self.post_transform_manipulation(sampling_data)):
                print(f"saving {section}")
                np.save(f"{location}/{transform_data.name}/{datetime.fromtimestamp(transform_data.time_stamp).strftime(_DATETIME_FORMAT)}_{section}_{sampling_number}", save_data)

    def apply_transform_and_save(self):
        self.transforms_backend.callback_new_transform_data = self.post_transform_data_handling
        self.playback_speed = 0.01
        self.replay_frames(self.finished_session) 
        
    def finished_session(self):
        self.pause_player()
        
        self.finished_operation = partial(self.replay_frames, self.finished_session) 

        if not self.next_session():
            self.save_database_info()
            self.transforms_backend.callback_new_transform_data = None
            self.finished_operation = None
            
    def save_database_info(self):
        location = f"{self.sub_window.widgets.save_location.getInnerText()}/{self.displayed_data.transform}"
        with open(location + "database_info.json", "w") as file_pointer:
            json.dump({"minimum":self.minimum_value, "maximum":self.maximum_value}, file_pointer, indent=4)
