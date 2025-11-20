from gui.main_window import MainWindow
from gui.sub_widgets.signal_window import SignalWindow, Actions, ContainerLabel, ChirpValues, LoopValues
from ifxradarsdk.fmcw.types import FmcwElementType
from gui_backend.pull_data import DataHandler
from typing import Dict, Any, Optional
from gui_backend.helpers import ElementSequence
from typing import List, Optional
from ifxradarsdk.fmcw.types import FmcwElementType
from gui.helpers import background_color
from gui_backend.helpers import WaveformSections, CreateLine
from matplotlib.collections import LineCollection




color_lookup = {
    WaveformSections.PLL_LOCK: (0.1, 0.1, 0.5),
    WaveformSections.INIT_0: (0.1, 0.2, 0.5),
    WaveformSections.INIT_1: (0.1, 0.2, 0.6),
    WaveformSections.PRE_CHIRP: (0.1, 0.3, 0.6),
    WaveformSections.PA_DELAY: (0.1, 0.3, 0.7),
    WaveformSections.ADC_DELAY: (0.1, 0.4, 0.7),
    WaveformSections.RAMP: (0.1, 0.4, 0.8),
    WaveformSections.RAMP_END: (0.1, 0.5, 0.8),
    WaveformSections.LOWER_RAMP: (0.1, 0.5, 0.9),
    WaveformSections.POST_CHIRP: (0.1, 0.6, 0.9),
    WaveformSections.CHIRP_END_0: (0.1, 0.6, 1.0),
    WaveformSections.CHIRP_END_1: (0.1, 0.7, 1.0),
    WaveformSections.LOOP_TIME: (0.1, 0.8, 1.0),
    WaveformSections.DELAY: (0.1, 0.9, 1.0),
}



class SignalWindowBackend():
    """Manage data that goes between each back end."""
    
    def __init__(self, main_window: MainWindow, sub_window: SignalWindow, data_handler: DataHandler):
        """Initialize the wrapper with info from the main window gui.

        Args:
            main_window: The main gui window.
        """
        self.main_window = main_window
        self.data_handler = data_handler
        self.sub_window = sub_window
        self.sub_window.widgets.figure.patch.set_facecolor(background_color)

        self.subplot = sub_window.widgets.figure.add_subplot(1, 1, 1)
        for spine in self.subplot.spines.values():
            spine.set_edgecolor('white')   # color of border lines
            spine.set_linewidth(2) 
        self.subplot.patch.set_facecolor(background_color)
        self.subplot.set_title("Signal", fontsize=10, pad=24, color="white")
        self.subplot.tick_params(axis='x', colors='white')
        self.subplot.tick_params(axis='y', colors='white')
        self.chirp_list = None
        self.sub_window.action_window.widgets.send_to_device.clicked.connect(self.acquire_specified_config)

    def acquire_specified_config(self):
        if self.sub_window.sub_element is None:
            return
        if self.sub_window.sub_element.label_name == Actions.Simple_Config.value:
            first_element = self.simple_config(self.sub_window.sub_element)
        else:
            first_element, _ = self.action_loop(self.sub_window.sub_element)
        
        self.reconstruct_waveform(first_element)
        self.data_handler.create_new_config(first_element, self.chirp_list)
        
    def simple_config(self, action_first: ContainerLabel):
        outer_loop = ElementSequence()
        outer_loop.loop = LoopValues()
        outer_loop.type = FmcwElementType.IFX_SEQ_LOOP
        outer_loop.loop.repetition_time_s = action_first.values.frame_repetition_time_s
        outer_loop.loop.num_repetitions = 0
        
        inner_loop = ElementSequence()
        inner_loop.loop = LoopValues()
        inner_loop.type = FmcwElementType.IFX_SEQ_LOOP
        inner_loop.loop.repetition_time_s = action_first.values.chirp_repetition_time_s
        inner_loop.loop.num_repetitions = action_first.values.num_chirps
        outer_loop.loop.sub_sequence = inner_loop

        chirp = ElementSequence()
        chirp.type = FmcwElementType.IFX_SEQ_CHIRP
        chirp.chirp = ChirpValues()
        chirp.chirp.setup_simple(action_first.values)
        chirp.chirp_sequence = 0
        inner_loop.loop.sub_sequence = chirp
        return outer_loop
        
    def action_loop(self, action_first: ContainerLabel, chirp_sequence: int = 0) -> ElementSequence:
        current_action = action_first
        previous_element_sequence: Optional[ElementSequence] = None
        first_element_sequence: Optional[ElementSequence] = None
        
        while True:
            element_sequence = ElementSequence()
            if previous_element_sequence is not None:
                previous_element_sequence.next_element = element_sequence
            if current_action.label_name == Actions.Chirp.value:
                element_sequence.type = FmcwElementType.IFX_SEQ_CHIRP
                element_sequence.chirp = current_action.values
                element_sequence.chirp_sequence = chirp_sequence
                chirp_sequence += 1
            elif current_action.label_name == Actions.Delay.value:
                element_sequence.type = FmcwElementType.IFX_SEQ_DELAY
                element_sequence.delay = current_action.values
            elif current_action.label_name == Actions.Loop.value:
                element_sequence.type = FmcwElementType.IFX_SEQ_LOOP
                loop_sequence, chirp_sequence = self.action_loop(current_action.sub_element, chirp_sequence)
                current_action.values.sub_sequence = loop_sequence
                element_sequence.loop = current_action.values
                
            if current_action == action_first:
                first_element_sequence = element_sequence
            
            if current_action.next_element is None:
                element_sequence.next_element = None
                break
            
            previous_element_sequence = element_sequence
            current_action = current_action.sub_element
        return first_element_sequence, chirp_sequence

    def create_signal(self, current_sequence: ElementSequence, movement_list: List[CreateLine]):
        current_movement_list: List[CreateLine] = []
        if current_sequence.type == FmcwElementType.IFX_SEQ_LOOP:
            for _ in range(max(current_sequence.loop.num_repetitions, 1)):
                # if we have no next element, we want to keep track of how long we are chirping
                # otherwise, if there is, we just add the length of the loop
                child_duration = self.create_signal(current_sequence.loop.sub_sequence, current_movement_list)
                repetition_difference = current_sequence.loop.repetition_time_s - child_duration
                if repetition_difference < 0:
                    current_sequence.loop.repetition_time_s = -repetition_difference
                if current_sequence.loop.num_repetitions:
                    current_movement_list.append(CreateLine(WaveformSections.LOOP_TIME, current_sequence.loop.repetition_time_s - child_duration, 0, 0))
        if current_sequence.type == FmcwElementType.IFX_SEQ_DELAY:
            current_movement_list.append(CreateLine(WaveformSections.DELAY, current_sequence.delay.time_s, 0, 0))
        if current_sequence.type == FmcwElementType.IFX_SEQ_CHIRP:
            ramp_time_period = current_sequence.chirp.num_samples / current_sequence.chirp.sample_rate_Hz
            ramp_speed = (current_sequence.chirp.end_frequency_Hz - current_sequence.chirp.start_frequency_Hz) / ramp_time_period
            pre_pa_frequnecy = current_sequence.chirp.start_frequency_Hz - (WaveformSections.PA_DELAY.value * ramp_speed)
            pre_ramp_frequency = current_sequence.chirp.start_frequency_Hz + (WaveformSections.ADC_DELAY.value * ramp_speed)
            end_ramp_frequency = current_sequence.chirp.end_frequency_Hz + (WaveformSections.RAMP_END.value * ramp_speed)
            
            current_movement_list.append(CreateLine(WaveformSections.PLL_LOCK, WaveformSections.PLL_LOCK.value, 56.32e9, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.INIT_0, WaveformSections.INIT_0.value, pre_pa_frequnecy, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.INIT_1, WaveformSections.INIT_1.value, pre_pa_frequnecy, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.PRE_CHIRP, WaveformSections.PRE_CHIRP.value, pre_pa_frequnecy, pre_pa_frequnecy))
            
            current_movement_list.append(CreateLine(WaveformSections.PA_DELAY, WaveformSections.PA_DELAY.value, pre_pa_frequnecy, current_sequence.chirp.start_frequency_Hz))
            current_movement_list.append(CreateLine(WaveformSections.ADC_DELAY, WaveformSections.ADC_DELAY.value, current_sequence.chirp.start_frequency_Hz, pre_ramp_frequency, chirp=True))
            current_movement_list[-1].chirp_sequence = current_sequence.chirp_sequence
            current_movement_list.append(CreateLine(WaveformSections.RAMP, ramp_time_period, pre_ramp_frequency, current_sequence.chirp.end_frequency_Hz, chirp=True))                        
            current_movement_list[-1].chirp_sequence = current_sequence.chirp_sequence
            
            current_movement_list.append(CreateLine(WaveformSections.RAMP_END, WaveformSections.RAMP_END.value, current_sequence.chirp.end_frequency_Hz, end_ramp_frequency))
            current_movement_list.append(CreateLine(WaveformSections.LOWER_RAMP, WaveformSections.LOWER_RAMP.value, end_ramp_frequency, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.POST_CHIRP, WaveformSections.POST_CHIRP.value, pre_pa_frequnecy, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.CHIRP_END_0, WaveformSections.CHIRP_END_0.value, pre_pa_frequnecy, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.CHIRP_END_1, WaveformSections.CHIRP_END_1.value, pre_pa_frequnecy, pre_pa_frequnecy))

        if current_sequence.next_element is not None:
            self.create_signal(current_sequence.next_element, current_movement_list)
        
        total_duration = 0

        for movement_item in current_movement_list:
            total_duration += movement_item.duration

        movement_list.extend(current_movement_list)
        
        return total_duration

    def reconstruct_waveform(self, first_sequence: ElementSequence):
        movement_list: List[CreateLine] = []

        self.create_signal(first_sequence, movement_list)
        self.chirp_list = []
        current_location = 0
        movement_coordinates_list = []
        colors = []
        for movement_item in movement_list:
            next_location = current_location + movement_item.duration
            if movement_item.chirp:
                self.chirp_list.append(movement_item)
            if movement_item.name not in (WaveformSections.LOOP_TIME, WaveformSections.DELAY):
                colors.append(color_lookup[movement_item.name])
                movement_coordinates = [(current_location, movement_item.starting_frequency), (next_location, movement_item.ending_frequency)]
                movement_coordinates_list.append(movement_coordinates)
            current_location = next_location
        self.subplot.clear()
        self.subplot.patch.set_facecolor(background_color)
        self.subplot.set_title("Signal", fontsize=10, pad=24, color="white")
        self.subplot.add_collection(LineCollection(movement_coordinates_list, colors=colors, linewidth=2))
        self.subplot.autoscale()
        self.subplot.figure.canvas.draw_idle()
