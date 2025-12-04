"""View the transforms through arbitrary code execution."""
from gui.sub_widgets.view_transforms import ViewTransforms, AllChirpContainerWindow
from ifxradarsdk.fmcw.types import FmcwElementType
from gui_backend.pull_data import DataHandler
from gui_backend.helpers import Popup, ElementSequence, CreateLine, TimeStampData, TertiaryData
from gui.helpers import ModuleInfo, _NO_METHOD, _SINGLE_TRANSFORM_NAME, _HISTORY_FEATURES_NAME, _HISTORY_TRANSFORMS_INFO
from PyQt6 import QtWidgets, QtCore
import importlib
import inspect
from typing import List, Union, Optional, Dict, Callable, NamedTuple
from functools import partial
import numpy as np
import sys
from numpy.typing import NDArray
from gui.main_window import MainWindow
import traceback
from types import ModuleType
import multiprocessing as mp
from multiprocessing.synchronize import Event
from dataclasses import dataclass
from enum import Enum
from queue import Empty
import time

ViewingData = NamedTuple("ViewingData", [("time_stamp_data", TimeStampData), ("tertiary_data", TertiaryData),])

_GRAB_SPEED = 16
_ALLOWED_LENGTH = 1000

class NoTransformNoAcquisitionError(Exception):
    pass


class MethodArgumentsError(Exception):
    pass


@dataclass
class AllData:
    frame_data: Dict[str, NDArray[np.float64]]
    tertiary_data: Dict[str, Optional[TertiaryData]] = None

@dataclass
class DataPacket:
    frame_data: TimeStampData
    chirp_info_list: List[CreateLine]
    tab_to_update: str

@dataclass
class MethodPacket:
    module_info: ModuleInfo
    method_name: str

@dataclass
class PassInPacket:
    data_packet: DataPacket
    method_packets: List[MethodPacket]
    tertiary_data: Optional[TertiaryData]

@dataclass
class PassbackPacket:
    transformed_data: Optional[TimeStampData]
    tab_to_update: Optional[str]
    error: Optional[str] = None
    end_transmission: bool = False
    tertiary_data: Optional[TertiaryData] = None
    
class DataEventsToHandle(Enum):
    NEW_DATA = 0
    CLEAR_DATA = 1
    NEW_MODULES = 2
    END_TRANSMISSION = 3

def new_methods(method_packets: List[MethodPacket], modules: Dict[ModuleInfo, ModuleType]) -> None:
    """Grab the new methods within a module for the new process.

    Args:
        method_packets: A list of the different file locations to check.
        modules: A dictionary containing all the already known modules.
    """
    for method_packet in method_packets:
        if method_packet.module_info.module_name in sys.modules:
            del sys.modules[method_packet.module_info.module_name]

        # load module again
        spec = importlib.util.spec_from_file_location(method_packet.module_info.module_name, str(method_packet.module_info.module_path.resolve()))
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create spec for {method_packet.module_info.module_path}")
        modules[method_packet.module_info.module_name] = importlib.util.module_from_spec(spec)
        sys.modules[method_packet.module_info.module_name] = modules[method_packet.module_info.module_name]
        spec.loader.exec_module(modules[method_packet.module_info.module_name])

def different_method_calls(
    method_call: Callable, 
    to_transform_data: Optional[Union[List[NDArray[np.float64]], List[List[NDArray[np.float64]]]]], 
    chirp_info_list: List[CreateLine],
    tertiary_data: Optional[TertiaryData]
) -> List[NDArray[np.float64]]:
    """Method to attempt many different method calls to see which work.

    Args:
        method_call: The method to attempt to call.
        transformed_data: The data to transform.
        chirp_info_list: The info to recreate the chirp.
    """
    argument_options = [

        {"frame_list": to_transform_data, "chirp_info_list": chirp_info_list, "tertiary_data": tertiary_data},
        {"frame_list": to_transform_data, "tertiary_data": tertiary_data},
        {"frame_list": to_transform_data, "chirp_info_list": chirp_info_list},
        {"frame_list": to_transform_data},
        {"frame_history": to_transform_data, "chirp_info_list": chirp_info_list, "tertiary_data": tertiary_data},
        {"frame_history": to_transform_data, "tertiary_data": tertiary_data},
        {"frame_history": to_transform_data, "chirp_info_list": chirp_info_list},
        {"frame_history": to_transform_data},
        {"chirp_info_list": chirp_info_list},
        [to_transform_data, chirp_info_list, tertiary_data],
        [to_transform_data, chirp_info_list],
        [to_transform_data],
    ]

    for attempted_arguments in argument_options:
        try:
            if isinstance(attempted_arguments, list):
                transformed_info = method_call(*attempted_arguments)
            else:
                transformed_info = method_call(**attempted_arguments)
            if isinstance(transformed_info, tuple):
                return transformed_info
            else:
                return transformed_info, tertiary_data
        except TypeError:
            continue
    else:
        raise MethodArgumentsError(f"Method arguments failed to pass Typing for {method_call.__name__}.")

def handle_methods(
    data_packet: DataPacket, 
    method_packets: List[MethodPacket],
    tertiary_data: Optional[TertiaryData],
    modules: Dict[ModuleInfo, ModuleType], 
    data_list: AllData
) -> List[NDArray[np.float64]]:
    """Handles transforming the data for the GUI window.

    Args:
        data_packet: A packet of data containing the frame data and which tab to port the transform to.
        method_packets: A packet containing a list of the method names to transform using.
        modules: A dictionary containing all the already known modules.
        data_list: A dictionary containing previous data.

    Returns:
        A list (each chirp sequence) of frames (receiver, chirp per frame, sample per chirp)
    """
    transformed_data = data_packet.frame_data.data
    transformed_tertiary_data = tertiary_data
    if transformed_tertiary_data is not None:
        transformed_tertiary_data.fundamentals["label"] = data_packet.frame_data.name
    if data_packet.tab_to_update not in data_list.frame_data and transformed_data is not None: 
        data_list.frame_data[data_packet.tab_to_update] = []
        data_list.tertiary_data[data_packet.tab_to_update] = []
    
    transform_name = ""
    for method_packet in method_packets:
        # Single Data Transform
        if method_packet.module_info.module_name == _SINGLE_TRANSFORM_NAME:
            if method_packet.method_name == _NO_METHOD:
                if transformed_data is None:
                    raise NoTransformNoAcquisitionError("Value must be transformed if there is no acquisition to display")
                
                if not isinstance(transformed_data, list):
                    transformed_data = [transformed_data]
            else:
                transform_name += method_packet.method_name
                transform_method = getattr(modules[method_packet.module_info.module_name], method_packet.method_name)
                if not isinstance(transformed_data, list) and transformed_data is not None:
                    transformed_data, transformed_tertiary_data = different_method_calls(
                        transform_method, [transformed_data], data_packet.chirp_info_list, transformed_tertiary_data
                    )
                else:
                    transformed_data, transformed_tertiary_data = different_method_calls(
                        transform_method, transformed_data, data_packet.chirp_info_list, transformed_tertiary_data
                    )

        # Data Transform With History
        if method_packet.module_info.module_name == _HISTORY_FEATURES_NAME:
            if method_packet.method_name != _NO_METHOD:
                transform_name += method_packet.method_name
                if len(data_list.frame_data[data_packet.tab_to_update]) > _ALLOWED_LENGTH:
                    data_list.frame_data[data_packet.tab_to_update].pop(0)
                    data_list.tertiary_data[data_packet.tab_to_update].pop(0)
                data_list.frame_data[data_packet.tab_to_update].append(AllData(transformed_data, transformed_tertiary_data))
                data_list.tertiary_data[data_packet.tab_to_update].append(AllData(transformed_data, transformed_tertiary_data))
                feature_method = getattr(modules[method_packet.module_info.module_name], method_packet.method_name)
                transformed_data, transformed_tertiary_data = different_method_calls(
                    feature_method, data_list.frame_data[data_packet.tab_to_update], data_packet.chirp_info_list, data_list.tertiary_data[data_packet.tab_to_update]
                )
            else:
                data_list.frame_data[data_packet.tab_to_update] = [transformed_data]
                data_list.tertiary_data[data_packet.tab_to_update] = [transformed_tertiary_data]
                
    return TimeStampData(
        data_packet.frame_data.name, 
        data_packet.frame_data.time_stamp, 
        transformed_data, 
        transform=transform_name
    ), transformed_tertiary_data

def run_arbitrary_code(
    event_queue: mp.Queue, pass_in_queue: mp.Queue, new_module_methods: mp.Queue, transformed_data_queue: mp.Queue, empty_queues: Event
):
    """Run arbitrary code within some files.

    Args:
        event_queue: A queue to handle when an event occurs.
        pass_in_queue: A queue to handle the data.
        new_module_methods: A queue to handle to tell the process which files to re check for modules.
        transformed_data_queue: A queue to handle the passed back .
        empty_queues: The event of the event queue being empty.
    """
    modules = {}
    data_list = AllData({}, {})
    while True:
        try:
            try:
                event = event_queue.get(timeout=0.05)
                empty_queues.clear()
                if event == DataEventsToHandle.NEW_DATA:
                    pass_in_data: PassInPacket = pass_in_queue.get(timeout=0.16)
                    feature_data, transformed_tertiary_data = handle_methods(
                        pass_in_data.data_packet, pass_in_data.method_packets, pass_in_data.tertiary_data, modules, data_list
                    )
                    transformed_data_queue.put(PassbackPacket(
                        feature_data, pass_in_data.data_packet.tab_to_update, tertiary_data=transformed_tertiary_data
                    ))
                elif event == DataEventsToHandle.NEW_MODULES:
                    method_packets = new_module_methods.get_nowait()
                    new_methods(method_packets, modules)
                    
                elif event == DataEventsToHandle.CLEAR_DATA:
                    data_list = AllData({},{})
                elif event == DataEventsToHandle.END_TRANSMISSION:
                    transformed_data_queue.put(PassbackPacket(None, None, end_transmission=True))
            except Empty:
                empty_queues.set()
                pass
        except Exception as exception:
            traceback_object = exception.__traceback__
            pop_up_string = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            while traceback_object.tb_next:
                traceback_object = traceback_object.tb_next
            line_number = traceback_object.tb_lineno
            file_name = traceback_object.tb_frame.f_code.co_filename

            transformed_data_queue.put(PassbackPacket(None, None, pop_up_string))


class ViewTransformsBackend(QtCore.QObject):
    """Visualize the transforms provided from methods in another file."""
    
    def __init__(
        self, 
        main_window: MainWindow, 
        sub_window: ViewTransforms, 
        callback_raised_error: Callable, 
        callback_no_packets_in_flight: Optional[Callable],
        callback_new_transform_data: Optional[Callable] = None,
    ):
        """Initialize the elements and events for the view transforms window.
        
        Args:
            main_window: The main gui window.
            sub_window: The window this backend is supporting.
        """
        super().__init__()
        self.main_window = main_window
        self.sub_window = sub_window
        self.sub_window.seperate_viewer_tabs.added_new_tab.connect(lambda new_tab: self.connect_widgets(new_tab))

        self.methods: Dict[ModuleInfo, str] = {}
        self.data_list: List[List[NDArray[np.float64]]] = []
        self.current_number_of_views = 0
        self.chirp_info_list = None
        self.modules: Dict[ModuleInfo, ModuleType] = {}
        self.current_data: Dict[AllChirpContainerWindow, ViewingData] = {}
        self.pass_in_queue = mp.Queue()
        self.event_queue = mp.Queue()
        self.transform_queue = mp.Queue()
        self.new_module_methods = mp.Queue()
        self.empty_queues = mp.Event()
        self.data_process = mp.Process(
            target=run_arbitrary_code, 
            args=(self.event_queue, self.pass_in_queue, self.new_module_methods, self.transform_queue, self.empty_queues)
        )
        self.data_process.start()
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_arbitrary_run_request)
        self.timer.start(_GRAB_SPEED)
        self.packets_in_flight = 0
        
        self.wait_for_packets = False
        
        self.callback_raised_error = callback_raised_error
        self.callback_no_packets_in_flight = callback_no_packets_in_flight
        self.callback_new_transform_data = callback_new_transform_data
    
    def connect_widgets(self, new_tab: AllChirpContainerWindow):
        """When a new tab is created, connect the sub widgets to their perspective calls.

        Args:
            new_tab: The tab object which has been created.
        """
        self.load_all_files(new_tab)
        if new_tab in self.current_data:
            new_tab.add_new_views(self.current_number_of_views, self.current_data[new_tab].tertiary_data)
        else:
            new_tab.add_new_views(self.current_number_of_views, TertiaryData())
            
        new_tab.update_graph_type(new_tab.widgets.graph_type.combo_box.currentText())
        new_tab.widgets.refresh.clicked.connect(partial(
            self.load_all_files, new_tab
        ))
        new_tab.widgets.graph_type.combo_box.currentTextChanged.connect(partial(self.update_graph_type, new_tab))
        for method_dropdown in new_tab.widgets.method_dropdowns.values():
            method_dropdown.combo_box.currentTextChanged.connect(partial(self.reset_view, new_tab))

    def load_all_files(self, new_tab: AllChirpContainerWindow):
        """Load the methods from the arbitrary code execution files.

        Args:
            new_tab: The tab object which has just been created.
        """
        self.timer.stop()
        for module_info, method_dropdown in new_tab.widgets.method_dropdowns.items():
            self.load_file_methods(module_info, method_dropdown.combo_box)
        self.send_new_method_request(new_tab)
        self.timer.start()

    def load_file_methods(self, module_info: ModuleInfo, dropdown: QtWidgets.QComboBox):
        """Load the methods from another file for arbitrary code execution.

        Args:
            module_info: The different module information used to load.
            dropdown: Where to add the new methods to.
        """
        if module_info.module_name in sys.modules:
            del sys.modules[module_info.module_name]

        # Load module again
        spec = importlib.util.spec_from_file_location(module_info.module_name, str(module_info.module_path.resolve()))
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create spec for {module_info.module_path}")
        self.modules[module_info.module_name] = importlib.util.module_from_spec(spec)
        sys.modules[module_info.module_name] = self.modules[module_info.module_name]
        spec.loader.exec_module(self.modules[module_info.module_name])
        
        self.methods[module_info.module_name] = [
            name for name, _ in inspect.getmembers(self.modules[module_info.module_name], inspect.isfunction) if name.startswith("t_")
        ]
        dropdown.clear()
        dropdown.addItem(_NO_METHOD)
        dropdown.addItems(self.methods[module_info.module_name])
        
    def send_new_method_request(self, tab_to_run: AllChirpContainerWindow):
        """Request the other process to update what methods it has

        Args:
            tab_to_run: The tab that needs to update those methods.
        """
        method_list = []
        for method_type, dropdown in tab_to_run.widgets.method_dropdowns.items():
            method_list.append(MethodPacket(method_type, dropdown.getInnerText()))
        self.new_module_methods.put(method_list)
        self.event_queue.put(DataEventsToHandle.NEW_MODULES)
        
    def clear_data(self):
        """Clear all data within the processes data list."""
        self.event_queue.put(DataEventsToHandle.CLEAR_DATA)
        
    def send_arbitrary_run_request(
        self, 
        tab_to_run: AllChirpContainerWindow, 
        data: TimeStampData,
        tertiary_data: Optional[TertiaryData] = None,
        check_visibility: bool = True
    ):
        """Run the arbitrary code from the loaded methods.
        
        Args:
            tab_to_run: Where to put the data once it has been transformed.
            data: The data to transform.
            check_visibility: Whether to check visibility to reduce overhead.
        """
        method_packets: List[MethodPacket] = []
        all_data_group = False
        for method_type, dropdown in tab_to_run.widgets.method_dropdowns.items():
            method_packets.append(MethodPacket(method_type, dropdown.getInnerText()))
            if method_type == _HISTORY_TRANSFORMS_INFO and method_packets[-1].method_name != _NO_METHOD:
                all_data_group = True
        if check_visibility and (not tab_to_run.isVisible() and not all_data_group):
            self.packets_in_flight -= 1
            return 
        data_packet = DataPacket(data, self.chirp_info_list, tab_to_run.identification)
        self.pass_in_queue.put(PassInPacket(data_packet, method_packets, tertiary_data))
        self.event_queue.put(DataEventsToHandle.NEW_DATA)

    def check_arbitrary_run_request(self):
        """Poll the transform queue to see if new data has been transformed."""
        try:
            passback_packet: PassbackPacket = self.transform_queue.get_nowait()
            self.packets_in_flight -= 1
            # if we are not waiting for the data being sent to empty
            if not self.wait_for_packets:
                if passback_packet.error is not None:
                    self.callback_raised_error()
                    self.pop_up = Popup(passback_packet.error)
                    self.pop_up.launch()
                    self.wait_for_packets = True
                else:
                    tab_to_run = self.sub_window.seperate_viewer_tabs.view_tabs[passback_packet.tab_to_update]
                    self.handle_graphs(tab_to_run, passback_packet.transformed_data, passback_packet.tertiary_data)
                    self.current_data[tab_to_run] = ViewingData(passback_packet.transformed_data, passback_packet.tertiary_data)
        except Empty:
            if not self.packets_in_flight:
                if self.callback_no_packets_in_flight is not None:
                    self.callback_no_packets_in_flight()
                if self.wait_for_packets:
                    self.wait_for_packets = False
                    self.clear_data()
                    # self.main_window.timeout_label.setText(f"{file_name} Line {line_number}: {exception}")


    def create_new_chirp_views(self, first_element: ElementSequence, chirp_info_list: List[CreateLine]):
        """Create new tabs for when the data has a new shape or when a new tab is added.

        Args:
            first_element: Unused.
            chirp_info_list: A list of objects storing the start and ned frequency of the chirps and their duration.
        """
        self.chirp_info_list = chirp_info_list
        for view_tab in self.sub_window.seperate_viewer_tabs.view_tabs.values():
            view_tab.add_new_views(self.current_number_of_views)
            view_tab.update_graph_type(view_tab.widgets.graph_type.combo_box.currentText())
    
    def iterate_through_each_view_tab(self, chirp_frames: TimeStampData, tertiary_data: Optional[TertiaryData] = None):
        """Iterate through all tabs within the window.

        Args:
            chirp_frames: The list of chirp frames to transform.
        """
        view_tabs = self.sub_window.seperate_viewer_tabs.view_tabs.values()
        self.packets_in_flight = len(view_tabs)
        for view_tab in view_tabs:
            self.send_arbitrary_run_request(view_tab, chirp_frames, tertiary_data)
        
    def update_graph_type(self, tab_to_run: AllChirpContainerWindow) -> None:
        tab_to_run.update_graph_type(tab_to_run.widgets.graph_type.combo_box.currentText())
        if tab_to_run in self.current_data:
            tab_to_run.setup_new_sub_plots(self.current_data[tab_to_run].time_stamp_data.data, self.current_data[tab_to_run].tertiary_data)
    
    def reset_view(self, tab_to_run: AllChirpContainerWindow) -> None:
        """Reset the data within the other process. 

        Args:
            tab_to_run: The tab to update the view of.
        """
        self.timer.stop()
        self.empty_queues.wait()
        self.clear_data()
        # tab_to_run.add_new_views(len(self.current_data[tab_to_run].time_stamp_data.data), self.current_data[tab_to_run].tertiary_data)
        # tab_to_run.setup_new_sub_plots(self.current_data[tab_to_run].time_stamp_data.data, self.current_data[tab_to_run].tertiary_data)
        self.timer.start()
        

    def handle_graphs(self, tab_to_run: AllChirpContainerWindow, transformed_data: TimeStampData, tertiary_data: TertiaryData) -> None:
        """Manage updating the graphs dependant on the shape of the data.

        Args:
            tab_to_run: The tab to update the data in.
            transformed_data: The data that has been transformed.
        """
        try:
            if tab_to_run in self.current_data:
                if len(transformed_data.data) != len(self.current_data[tab_to_run].time_stamp_data.data):
                    self.current_number_of_views = len(transformed_data.data)
                    tab_to_run.add_new_views(self.current_number_of_views, tertiary_data)
                    print(f"New tab plots {time.time()}")
                    
                for current_chirp_data, transformed_chirp_data in zip(self.current_data[tab_to_run].time_stamp_data.data, transformed_data.data):
                    if len(current_chirp_data.shape) > 2 and current_chirp_data.shape[0] != transformed_chirp_data.shape[0]:
                        tab_to_run.setup_new_sub_plots(transformed_data.data, tertiary_data)

                        break
            else:
                print(f"New tab plots {time.time()}")
                self.current_number_of_views = len(transformed_data.data)
                tab_to_run.add_new_views(self.current_number_of_views, tertiary_data)
                tab_to_run.setup_new_sub_plots(transformed_data.data, tertiary_data)
                
            if self.callback_new_transform_data:
                self.callback_new_transform_data(transformed_data)
            tab_to_run.update_views(transformed_data.data, tertiary_data)

        except (ValueError, TypeError) as exception:
            self.wait_for_packets = True
            self.callback_raised_error()
            traceback_object = exception.__traceback__
            while traceback_object.tb_next:
                traceback_object = traceback_object.tb_next
            line_number = traceback_object.tb_lineno
            file_name = traceback_object.tb_frame.f_code.co_filename
            self.main_window.timeout_label.setText(f"{file_name} Line {line_number}: {exception}")
            
            pop_up_string = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            self.pop_up = Popup(pop_up_string)
            self.pop_up.launch()