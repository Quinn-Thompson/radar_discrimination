"""Pull live data from the TR13CTO"""
import multiprocessing as mp
from multiprocessing.synchronize import Event
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp, ifxStructure, FmcwSequenceDelay, FmcwSequenceLoop, FmcwSequenceElement, FmcwElementType
from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtCore import QTimer, pyqtSignal, QObject, QMutex
from queue import Empty
import time
import numpy as np
from functools import partial
from datetime import datetime
from ctypes import POINTER
from gui_backend.helpers import ElementSequence, CreateLine, EventsToHandle, TimeStampData, _CHIRP_INFO, _CHIRP_DICT_START, _DATETIME_FORMAT
import json

class_registry: Dict[str, ifxStructure] = {
    "FmcwSequenceChirp": FmcwSequenceChirp,
}

_CONFIG_DIR = Path("config")
_CONFIG_PATH = _CONFIG_DIR / "device_configs.json"
_POLL_DATA_MAX = 10

def create_sequence_from_object(first_action: ElementSequence) -> FmcwSequenceElement:
    element = FmcwSequenceElement()
    element.type = first_action.type
    if first_action.type == FmcwElementType.IFX_SEQ_CHIRP:
        element.chirp = FmcwSequenceChirp(**first_action.chirp.__dict__)
    if first_action.type == FmcwElementType.IFX_SEQ_DELAY:
        element.delay = FmcwSequenceDelay(**first_action.delay.__dict__)
    if first_action.type == FmcwElementType.IFX_SEQ_LOOP:
        loop_sequence = POINTER(FmcwSequenceElement)(create_sequence_from_object(first_action.loop.sub_sequence))
        element.loop = FmcwSequenceLoop(
            loop_sequence,
            first_action.loop.num_repetitions,
            first_action.loop.repetition_time_s
        )
    if first_action.next_element is not None:
        element.next_element = POINTER(FmcwSequenceElement)(create_sequence_from_object(first_action.next_element))

    return element

def run_device_inner_loop(data_queue: mp.Queue, event_passed: Event, event_queue: mp.Queue, fmcw_custom: mp.Queue, passback_queue: mp.Queue, current_sequence: Optional[FmcwSequenceElement]) -> None:
    acquire = False
    with DeviceFmcw() as device:
        passback_queue.put(f"Succeeded in initializing device with sequence: {current_sequence}")
        device.stop_acquisition()
        
        if current_sequence is not None:
            device.set_acquisition_sequence(current_sequence)
        while True:

            if event_passed.is_set():
                event_passed.clear()
                event = event_queue.get()
                if event == EventsToHandle.NEW_SEQUENCE:
                    device.stop_acquisition()
                    new_sequence = create_sequence_from_object(fmcw_custom.get())
                    device.set_acquisition_sequence(new_sequence)
                    passback_queue.put("Succeeded in Setting New Sequence")
                    current_sequence = new_sequence
                elif event == EventsToHandle.STOP_ACQUISITION:
                    device.stop_acquisition()
                    acquire = False
                elif event == EventsToHandle.START_ACQUISITION:
                    device.start_acquisition()
                    acquire = True
                    
            if acquire:
                frame_contents = device.get_next_frame()
                data_queue.put(TimeStampData("nan", time.time(), frame_contents))
            else:
                time.sleep(0.1)

def gather_data(data_queue: mp.Queue, event_passed: Event, event_queue: mp.Queue, fmcw_custom: mp.Queue, passback_queue: mp.Queue) -> None:
    """Gathers data to report back to the main process."""
    current_sequence = None
    while True:
        try:        
            run_device_inner_loop(data_queue, event_passed, event_queue, fmcw_custom, passback_queue, current_sequence)
        except Exception as exception:
            passback_queue.put(exception)
            time.sleep(2.0)
            

class DataHandler(QObject):
    """Manages taking data from another process."""
    update_matplotlib = pyqtSignal(object)
    updated_sequence = pyqtSignal(object)
        
    def __init__(self) -> None:
        """Initialize the process for gathering data."""
        super().__init__()
        self.data_queue = mp.Queue()
        self.event_passed = mp.Event()
        self.event_queue = mp.Queue()
        self.fmcw_custom = mp.Queue()
        self.passback_queue = mp.Queue()
        self.data_process = mp.Process(target=gather_data, args=(self.data_queue, self.event_passed, self.event_queue, self.fmcw_custom, self.passback_queue))
        self.data_process.start()

        self.info_signal: pyqtSignal = None
        self.acquiring = False
        self.no_data_acquisition = False
        
        self.current_data = None
        self.waiting_for_data = True
        self._sent_once = False
        
        self.capture = False
        self.callback_function = None
        self._start_capture_time = None
        self._capture_count = None
        self.chirp_info_list = None
        self._previous_redraw_time = 0

    def stop_acquisition(self) -> None:
        self.event_queue.put(EventsToHandle.STOP_ACQUISITION)
        self.event_passed.set()
        self.acquiring = False
        self.no_data_acquisition = False
        self.info_signal.emit("Stopped All Acquisitions")

    def start_acquisition(self) -> None:
        self.event_queue.put(EventsToHandle.START_ACQUISITION)
        self.event_passed.set()
        self.acquiring = True
        self.info_signal.emit("Started Device Acquisitions")

    def start_no_data_acquisition(self) -> None:
        self.no_data_acquisition = True
        self.info_signal.emit("Started No Data Acquisition Procs")

    def create_new_config(self, first_element: ElementSequence, chirp_info_list: List[CreateLine]):
        self.chirp_info_list = chirp_info_list
        self.updated_sequence.emit((first_element, chirp_info_list))
        self.fmcw_custom.put(first_element)
        self.event_queue.put(EventsToHandle.NEW_SEQUENCE)
        self.event_passed.set()

    def capture_for_x_time(self, capture_time: float, location: Path):
        """Inform the callback to capture data from separate process for x seconds.

        Args:
            capture_time: The amount of time to capture data.
            location: The location to save the data.
        """
        if self.acquiring:
            if capture_time == 0.0:
                capture_time = 2**16
            location.mkdir()
            with open(location / _CHIRP_INFO, "w") as file_pointer:
                json.dump({_CHIRP_DICT_START: [chirp_info.get_json_dictionary() for chirp_info in self.chirp_info_list]}, file_pointer, indent=4)
            self.capture = True
            self.callback_function = partial(self._handle_x_time_capture, capture_time=capture_time, location=location)
            self.info_signal.emit(f"Capturing for {capture_time} seconds to {location}")
        else:
            self.info_signal.emit("Cannot capture without acquiring")

    def capture_for_x_count(self, capture_count: int, location: Path):
        """Inform the callback to capture x frames from separate process.

        Args:
            capture_time: The amount of time to capture data.
            location: The location to save the data.
        """
        if self.acquiring:
            if capture_count == 0:
                capture_count = 2**16
            location.mkdir()
            with open(location / _CHIRP_INFO, "w") as file_pointer:
                json.dump({_CHIRP_DICT_START: [chirp_info.get_json_dictionary() for chirp_info in self.chirp_info_list]}, file_pointer, indent=4)
            self.capture = True
            self.callback_function = partial(self._handle_x_count_capture, capture_count=capture_count, location=location)
            self.info_signal.emit(f"Capturing for {capture_count} frames to {location}")
        else:
            self.info_signal.emit("Cannot capture without acquiring")
        
    def _handle_x_time_capture(self, data: TimeStampData, capture_time: float, location: Path):
        """Callback during the polling process to capture data for x time.

        Args:
            data: The data to save.
            capture_time: The amount of time to capture data for.
            location: The location to save the data.
        """
        if self._start_capture_time is None:
            self._start_capture_time = data.time_stamp
            
        if data.time_stamp - self._start_capture_time > capture_time or not self.acquiring:
            self._start_capture_time = None
            self.capture = False
            self.callback_function = None
            self.info_signal.emit("Finished Capture")
            return
            
        self.save_data(data, location)
    
    def _handle_x_count_capture(self, data: TimeStampData, capture_count: int, location: Path):
        """Callback during the polling process to capture data for x frames

        Args:
            data: The data to save.
            capture_time: The amount of time to capture data for.
            location: The location to save the data.
        """
        if self._capture_count is None:
            self._capture_count = 0
            
        if self._capture_count > capture_count or not self.acquiring:
            self._capture_count = None
            self.capture = False
            self.callback_function = None
            self.info_signal.emit("Finished Capture")
            return
            
        self.save_data(data, location)
        self._capture_count += 1

    def save_data(self, data: TimeStampData, location: Path):
        """Save the data at a location.

        Args:
            data: The data to save and the timestamp to use for the name.
            location: Where to save the data.
        """
        if not isinstance(data.data, list):
            data_to_save = [data.data]
        else:
            data_to_save = data.data
        
        for chirp_index, chirp_data in enumerate(data_to_save):
            np.save(f"{location}/{datetime.fromtimestamp(data.time_stamp).strftime(_DATETIME_FORMAT)}_{chirp_index}", chirp_data)
        
    def poll_passback(self):
        try:
            self.info_signal.emit(str(self.passback_queue.get_nowait()))
        except Empty:
            pass

    def poll_data_queue(self):
        """Consistently poll data when anything needs to display live data or data needs to be drawn.
        
        This class will be polled once every x period of time, and will empty the queue
        if the queue is congested, no choose and kill is done, instead it will just attempt to empty it ASAP 
        to prevent data skipping.
        """
        for _ in range(_POLL_DATA_MAX):
            try:
                if not self.no_data_acquisition:
                    data_value: TimeStampData = self.data_queue.get_nowait() 
                    self.current_data = data_value
                else:
                    self.current_data = None
            except Empty:
                break

            if self.no_data_acquisition or data_value is not None:
                self.handle_passing_data()
            
            # this may be a problem as it is a bottleneck for retreiving data
            if self.capture and data_value is not None:
                self.callback_function(data_value)
                
            if self.no_data_acquisition:
                break
        
    def handle_passing_data(self):
        # just throw the data at matplotlib whenever it's done updating
        if self.waiting_for_data and self._sent_once:
            self._sent_once = False
        
        if self.waiting_for_data and not self._sent_once:
            current_time = time.time()
            if current_time - self._previous_redraw_time > 0.10:
                self.waiting_for_data = False
                self.update_matplotlib.emit(self.current_data)
                self._sent_once = True
                self._previous_redraw_time = current_time