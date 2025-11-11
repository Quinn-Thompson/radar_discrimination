"""Pull live data from the TR13CTO"""
import multiprocessing as mp
from multiprocessing.synchronize import Event
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp, ifxStructure
from pathlib import Path
from typing import Dict, Any, Union
from dataclasses import dataclass
import json
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from queue import Empty
import time
from numpy.typing import NDArray
import numpy as np
from functools import partial
from datetime import datetime

class_registry: Dict[str, ifxStructure] = {
    "FmcwSequenceChirp": FmcwSequenceChirp,
}

_CONFIG_DIR = Path("config")
_CONFIG_PATH = _CONFIG_DIR / "device_configs.json"

@dataclass
class TimeStampData():
    """Numpy data that has a time stamp."""
    time_stamp: float
    data: NDArray[np.float64]


def gather_data(data_queue: mp.Queue, run_device: Event, fmcw_config: Dict[str, Any]) -> None:
    """Gathers data to report back to the main process."""
    
    # unloads the json dicts into object types
    chirp_class = class_registry[fmcw_config["chirp"]["chirp_type"]]
    del fmcw_config["chirp"]["chirp_type"]
    chirp_class_inst = chirp_class(**fmcw_config["chirp"])
    
    fmcw_config["chirp"] = chirp_class_inst
    config = FmcwSimpleSequenceConfig(**fmcw_config)
    
    with DeviceFmcw() as device:
        
        sequence = device.create_simple_sequence(config)
        device.set_acquisition_sequence(sequence)

        while True:
            # loop that runs forever, waiting for an Event to collect data
            if run_device.is_set():
                frame_contents = device.get_next_frame()
                data_queue.put(TimeStampData(time.time(), frame_contents[0]))
            else:
                time.sleep(0.1)
        


class DataHandler(QObject):
    """Manages taking data from another process."""
    update_matplotlib = pyqtSignal(object)
        
    def __init__(self) -> None:
        """Initialize the process for gathering data."""
        super().__init__()
        with open(_CONFIG_PATH, "r") as config_pointer:
            loaded_Config = json.load(config_pointer)
        self.data_queue = mp.Queue()
        self.run_device = mp.Event()
        self.data_process = mp.Process(target=gather_data, args=(self.data_queue, self.run_device, loaded_Config))
        self.data_process.start()
        
        self.display = True
        self.run_device.set()
        self.capture = False
        self.callback_function = None
        self._start_capture_time = None
        self._capture_count = None

    def capture_for_x_time(self, capture_time: float, location: Path):
        """Inform the callback to capture data from separate process for x seconds.

        Args:
            capture_time: The amount of time to capture data.
            location: The location to save the data.
        """
        location.mkdir()
        if not self.display:
            self.run_device.set()
        self.capture = True
        self.callback_function = partial(self._handle_x_time_capture, capture_time=capture_time, location=location)

    def capture_for_x_count(self, capture_count: int, location: Path):
        """Inform the callback to capture x frames from separate process.

        Args:
            capture_time: The amount of time to capture data.
            location: The location to save the data.
        """
        location.mkdir()
        if not self.display:
            self.run_device.set()
        self.capture = True
        self.callback_function = partial(self._handle_x_count_capture, capture_count=capture_count, location=location)
        
    def _handle_x_time_capture(self, data: TimeStampData, capture_time: float, location: Path):
        """Callback during the polling process to capture data for x time.

        Args:
            data: The data to save.
            capture_time: The amount of time to capture data for.
            location: The location to save the data.
        """
        if self._start_capture_time is None:
            self._start_capture_time = data.time_stamp
            
        if data.time_stamp - self._start_capture_time > capture_time:
            self._start_capture_time = None
            self.capture = False
            self.callback_function = None
            if not self.display:
                self.run_device.clear()
            return
            
        np.save(f"{location}/{datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")}", data.data)
    
    def _handle_x_count_capture(self, data: TimeStampData, capture_count: int, location: Path):
        """Callback during the polling process to capture data for x frames

        Args:
            data: The data to save.
            capture_time: The amount of time to capture data for.
            location: The location to save the data.
        """
        if self._capture_count is None:
            self._capture_count = 0
            
        if self._capture_count > capture_count:
            self._capture_count = None
            self.capture = False
            self.callback_function = None
            if not self.display:
                self.run_device.clear()
            return
            
        np.save(f"{location}/{datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")}", data.data)
        self._capture_count += 1
                    
    def poll_data_queue(self):
        """Consistently poll data when anything needs to display live data or data needs to be drawn."""
        count = 0
        while True:
            try:
                data_value: TimeStampData = self.data_queue.get_nowait()
                if not count and self.display and data_value is not None:
                    self.update_matplotlib.emit(data_value)
                if self.capture and data_value is not None:
                    self.callback_function(data_value)
            except Empty:
                break
            
            count += 1
        