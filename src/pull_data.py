"""Pull live data from the TR13CTO"""
import multiprocessing as mp
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp, ifxStructure
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
from time import time

class_registry: Dict[str, ifxStructure] = {
    "FmcwSequenceChirp": FmcwSequenceChirp,
}

_CONFIG_DIR = Path("config")
_CONFIG_PATH = _CONFIG_DIR / "device_configs.json"

@dataclass
class RequestFrames():
    time_period: Optional[float] = None
    frame_count: Optional[int] = None

def run_time_loop(data_queue: mp.Queue, request_frames: mp.Queue, run_event: mp.Event, finished_event: mp.Event, device: DeviceFmcw):
    """_summary_

    Args:
        data_queue (mp.Queue): _description_
        request_frames (mp.Queue): _description_
        run_event (mp.Event): _description_
        finished_event (mp.Event): _description_
        device (DeviceFmcw): _description_

    Raises:
        ValueError: _description_
    """
    run_event.wait()
    requested_frame_info: RequestFrames = request_frames.pop()
    count = 0
    start_time = time()
    while True:
        count += 1
        frame_contents = device.get_next_frame()
        data_queue.put(frame_contents)
        if requested_frame_info.frame_count is not None and count == requested_frame_info.frame_count:
            break
        elif requested_frame_info.time_period is not None and time() > start_time + requested_frame_info.time_period:
            break
        else:
            raise ValueError("Requesting frames must include a time period of frame count.")
            
    finished_event.set()

def request_frames_for_x_time(time_period: float, run_event: mp.Event, request_frames: mp.Queue, wait_period: bool = False, finished_event: Optional[mp.Event] = None):
    request_frames.put(RequestFrames(time_period=time_period))
    run_event.set()
    if wait_period:
        if finished_event is not None:
            finished_event.wait()

def request_x_frames(frame_count: float, run_event: mp.Event, request_frames: mp.Queue, wait_period: bool = False, finished_event: Optional[mp.Event] = None):
    request_frames.put(RequestFrames(frame_count=frame_count))
    run_event.set()
    if wait_period:
        if finished_event is not None:
            finished_event.wait()

def gather_data(data_queue: mp.Queue, request_frames: mp.Queue, run_event: mp.Event, finished_event: mp.Event, fmcw_config: Dict[str, Any]) -> None:
    """Gathers data to report back to the main process."""
    
    # unloads the json dicts into object types
    chirp_class = class_registry[fmcw_config["chirp"]["chirp_chirp_type"]]
    del fmcw_config["chirp"]["chirp_chirp_type"]
    chirp_class_inst = chirp_class(**class_registry[fmcw_config["chirp"]])
    fmcw_config["chirp"] = chirp_class_inst
    config = FmcwSimpleSequenceConfig(**fmcw_config)
    
    with DeviceFmcw as device:
        
        sequence = device.create_simple_sequence(config)
        device.set_acquisition_sequence(sequence)

        while True:
            run_time_loop(data_queue, request_frames, run_event, finished_event, device)

def initialize_processes() -> None:
    """Initialize the process for gathering data."""
    with open(_CONFIG_PATH, "r") as config_pointer:
        loaded_Config = json.load(config_pointer)
    data_queue = mp.Queue()
    data_process = mp.Process(target=gather_data, args=(data_queue, loaded_Config))
    data_process.start()

if __name__ == "__main__":
    # Prevent multithreading from re-running teh main script.
    initialize_processes()