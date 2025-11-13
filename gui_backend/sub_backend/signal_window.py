from PyQt6.QtCore import QTimer
from gui.main_window import MainWindow
from gui.sub_widgets.signal_window import SignalWindow, Actions, ContainerLabel
from ifxradarsdk.fmcw.types import FmcwSequenceChirp, FmcwSequenceDelay, FmcwSequenceLoop, FmcwSequenceElement, FmcwElementType
from gui_backend.pull_data import DataHandler
from functools import partial
from ctypes import POINTER
from typing import Dict, Any

class SignalWindowBackend():
    """Manage data that goes between each back end."""
    
    def __init__(self, main_window: MainWindow, sub_window: SignalWindow, data_handler: DataHandler):
        """Initialize the wrapper with info from the main window gui.

        Args:
            main_window: The main gui window.
        """
        self.main_window = main_window
        self.sub_window = sub_window
        self.data_handler = data_handler
        self.sub_window.action_window.widgets.send_to_device.clicked.connect(self.acquire_specified_config)

    def acquire_specified_config(self):
        if self.sub_window.first_action is None:
            return
        first_element = self.action_loop(self.sub_window.first_action)
        self.data_handler.create_new_config(first_element)
        
    def action_loop(self, first_action: ContainerLabel) -> Dict[str, Any]:
        
        current_action = first_action
        previous_element_dictionary = None
        first_element_dictionary = None
        while True:
            element_dictionary = {}
            if previous_element_dictionary is not None:
                previous_element_dictionary["next_element"] = element_dictionary
            if current_action.label_name == Actions.Chirp.value:
                element_dictionary["type"] = FmcwElementType.IFX_SEQ_CHIRP
                element_dictionary["chirp"] = {
                    "start_frequency_Hz": current_action.values.start_freq,
                    "end_frequency_Hz": current_action.values.end_freq,
                    "sample_rate_Hz": current_action.values.sample_rate,
                    "num_samples": current_action.values.samples_per_chirp,
                    "rx_mask": 7,
                    "tx_mask": 1,
                    "tx_power_level": current_action.values.tx_power_level,
                    "lp_cutoff_Hz": current_action.values.low_pass,
                    "hp_cutoff_Hz": current_action.values.high_pass,
                    "if_gain_dB": current_action.values.if_gain,
                }
            elif current_action.label_name == Actions.Delay.value:
                element_dictionary["type"] = FmcwElementType.IFX_SEQ_DELAY
                element_dictionary["delay"] = {"time_s": current_action.values.time}
            elif current_action.label_name == Actions.Loop.value:
                element_dictionary["type"] = FmcwElementType.IFX_SEQ_LOOP
                loop_sequence = self.action_loop(current_action.action_child)
                element_dictionary["loop"] = {
                    "sub_sequence": loop_sequence,
                    "num_repetitions": current_action.values.number_of_reps,
                    "repetition_time_s": current_action.values.rep_time,   
                }
                
            if current_action == first_action:
                first_element_dictionary = element_dictionary
            
            if current_action.action_next is None:
                element_dictionary["next_element"] = None
                break
            
            previous_element_dictionary = element_dictionary
            current_action = current_action.action_next
        return first_element_dictionary
        
