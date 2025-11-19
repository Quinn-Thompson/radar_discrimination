"""Pull live data from the TR13CTO"""
import multiprocessing as mp
from multiprocessing.synchronize import Event
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp, ifxStructure, FmcwSequenceDelay, FmcwSequenceLoop, FmcwSequenceElement, FmcwElementType
from ifxradarsdk.common.exceptions import ErrorNumSamplesOutOfRange
from pathlib import Path
from typing import Dict, Any, Union, List, Optional
from dataclasses import dataclass
import json
from PyQt6.QtCore import QTimer, pyqtSignal, QObject, QMutex
from queue import Empty
import time
from numpy.typing import NDArray
import numpy as np
from functools import partial
from datetime import datetime
from ctypes import POINTER
from gui_backend.helpers import ElementSequence, CreateLine, EventsToHandle
from enum import Enum
from gui.main_window import MainWindow 

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

def run_device_inner_loop(data_queue: mp.Queue, event_passed: Event, event_queue: mp.Queue, fmcw_custom: mp.Queue) -> None:
    acquire = False
    with DeviceFmcw() as device:
        device.stop_acquisition()
        while True:

            if event_passed.is_set():
                event_passed.clear()
                event = event_queue.get()
                if event == EventsToHandle.NEW_SEQUENCE:
                    device.stop_acquisition()
                    new_sequence = create_sequence_from_object(fmcw_custom.get())
                    device.set_acquisition_sequence(new_sequence)
                elif event == EventsToHandle.STOP_ACQUISITION:
                    device.stop_acquisition()
                    acquire = False
                elif event == EventsToHandle.START_ACQUISITION:
                    device.start_acquisition()
                    acquire = True
                    
            if acquire:
                frame_contents = device.get_next_frame()
                data_queue.put(TimeStampData(time.time(), frame_contents))
            else:
                time.sleep(0.1)

def gather_data(data_queue: mp.Queue, event_passed: Event, event_queue: mp.Queue, fmcw_custom: mp.Queue) -> None:
    """Gathers data to report back to the main process."""

    while True:
        try:        
            run_device_inner_loop(data_queue, event_passed, event_queue, fmcw_custom)
        except BufferError:
            time.sleep(0.5)
            

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
        self.data_process = mp.Process(target=gather_data, args=(self.data_queue, self.event_passed, self.event_queue, self.fmcw_custom))
        self.data_process.start()
        
        self.info_signal = None
        
        self.current_data = None
        self.waiting_for_data = True
        self._sent_once = False
        
        self.capture = False
        self.callback_function = None
        self._start_capture_time = None
        self._capture_count = None
        self._previous_redraw_time = 0

    def stop_acquisition(self) -> None:
        self.event_queue.put(EventsToHandle.STOP_ACQUISITION)
        self.event_passed.set()

    def start_acquisition(self) -> None:
        self.event_queue.put(EventsToHandle.START_ACQUISITION)
        self.event_passed.set()

    def create_new_config(self, first_element: ElementSequence, chirp_list: List[CreateLine]):
        self.updated_sequence.emit((first_element, chirp_list))
        self.fmcw_custom.put(first_element)
        self.event_queue.put(EventsToHandle.NEW_SEQUENCE)
        self.event_passed.set()

    def capture_for_x_time(self, capture_time: float, location: Path):
        """Inform the callback to capture data from separate process for x seconds.

        Args:
            capture_time: The amount of time to capture data.
            location: The location to save the data.
        """
        location.mkdir()
        self.capture = True
        self.callback_function = partial(self._handle_x_time_capture, capture_time=capture_time, location=location)
        self.info_signal.emit(f"Capturing for {capture_time} seconds to {location}")

    def capture_for_x_count(self, capture_count: int, location: Path):
        """Inform the callback to capture x frames from separate process.

        Args:
            capture_time: The amount of time to capture data.
            location: The location to save the data.
        """
        location.mkdir()
        self.capture = True
        self.callback_function = partial(self._handle_x_count_capture, capture_count=capture_count, location=location)
        self.info_signal.emit(f"Capturing for {capture_count} frames to {location}")
        
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
            self.info_signal.emit("Finished Capture")
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
            self.info_signal.emit("Finished Capture")
            return
            
        np.save(f"{location}/{datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")}", data.data)
        self._capture_count += 1

    def poll_data_queue(self):
        """Consistently poll data when anything needs to display live data or data needs to be drawn."""
        count = 0
        while True:
            try:
                data_value: TimeStampData = self.data_queue.get_nowait() 
                self.current_data = data_value
                if not count and data_value is not None:
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
                
                if self.capture and data_value is not None:
                    self.callback_function(data_value)

            except Empty:
                break
            
            count += 1
        