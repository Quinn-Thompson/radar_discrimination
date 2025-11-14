from gui.main_window import MainWindow
from gui.sub_widgets.signal_window import SignalWindow, Actions, ContainerLabel
from ifxradarsdk.fmcw.types import FmcwElementType
from gui_backend.pull_data import DataHandler
from typing import Dict, Any, Optional
from gui_backend.helpers import ElementSequence

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
        previous_element_sequence: Optional[ElementSequence] = None
        first_element_sequence: Optional[ElementSequence] = None
        
        while True:
            element_sequence = ElementSequence()
            if previous_element_sequence is not None:
                previous_element_sequence.next_element = element_sequence
            if current_action.label_name == Actions.Chirp.value:
                element_sequence.type = FmcwElementType.IFX_SEQ_CHIRP
                element_sequence.chirp = current_action.values
            elif current_action.label_name == Actions.Delay.value:
                element_sequence.type = FmcwElementType.IFX_SEQ_DELAY
                element_sequence.delay = current_action.values
            elif current_action.label_name == Actions.Loop.value:
                element_sequence.type = FmcwElementType.IFX_SEQ_LOOP
                loop_sequence = self.action_loop(current_action.action_child)
                current_action.values.sub_sequence = loop_sequence
                element_sequence = current_action.values
                
            if current_action == first_action:
                first_element_sequence = element_sequence
            
            if current_action.action_next is None:
                element_sequence.next_element = None
                break
            
            previous_element_sequence = element_sequence
            current_action = current_action.action_next
        return first_element_sequence
        
