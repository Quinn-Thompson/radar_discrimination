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
    WaveformSections.PLL_LOCK.name: (0.1, 0.1, 0.5),
    WaveformSections.INIT_0.name: (0.1, 0.2, 0.5),
    WaveformSections.INIT_1.name: (0.1, 0.2, 0.6),
    WaveformSections.PRE_CHIRP.name: (0.1, 0.3, 0.6),
    WaveformSections.PA_DELAY.name: (0.1, 0.3, 0.7),
    WaveformSections.ADC_DELAY.name: (0.1, 0.4, 0.7),
    WaveformSections.RAMP.name: (0.1, 0.4, 0.8),
    WaveformSections.RAMP_END.name: (0.1, 0.5, 0.8),
    WaveformSections.LOWER_RAMP.name: (0.1, 0.5, 0.9),
    WaveformSections.POST_CHIRP.name: (0.1, 0.6, 0.9),
    WaveformSections.CHIRP_END_0.name: (0.1, 0.6, 1.0),
    WaveformSections.CHIRP_END_1.name: (0.1, 0.7, 1.0),
    WaveformSections.LOOP_TIME.name: (0.1, 0.8, 1.0),
    WaveformSections.DELAY.name: (0.1, 0.9, 1.0),
}

_STARTING_FREQ = 56.32e9

class SignalWindowBackend():
    """Create The sequences to generate with the TCR."""
    
    def __init__(self, main_window: MainWindow, sub_window: SignalWindow, data_handler: DataHandler) -> None:
        """Initialize teh backend info for the signal window.

        Args:
            main_window: The main gui window.
            sub_window: The window this backend pertains to.
            data_handler: The method for extracting data.
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
        self.chirp_info_list: Optional[List[CreateLine]] = None
        self.sub_window.action_window.widgets.send_to_device.clicked.connect(self.acquire_specified_config)

    def acquire_specified_config(self) -> None:
        """Recreate the waveform and config using the gui items."""
        if self.sub_window.sub_element is None:
            return
        if self.sub_window.sub_element.label_name == Actions.Simple_Config.value:
            first_element = self.recreate_simple_configuration(self.sub_window.sub_element)
        else:
            first_element, _ = self.loop_through_suquence(self.sub_window.sub_element)
        
        self.reconstruct_waveform(first_element)
        self.data_handler.create_new_config(first_element, self.chirp_info_list)
        
    def recreate_simple_configuration(self, first_widget: ContainerLabel) -> ElementSequence:
        """Create a simple configuration using loops and a chirp.

        Args:
            first_sequence: The first sequence within the gui.

        Returns:
            The simple sequence configuration.
        """
        outer_loop = ElementSequence()
        outer_loop.loop = LoopValues()
        outer_loop.type = FmcwElementType.IFX_SEQ_LOOP
        outer_loop.loop.repetition_time_s = first_widget.values.frame_repetition_time_s
        outer_loop.loop.num_repetitions = 0
        
        inner_loop = ElementSequence()
        inner_loop.loop = LoopValues()
        inner_loop.type = FmcwElementType.IFX_SEQ_LOOP
        inner_loop.loop.repetition_time_s = first_widget.values.chirp_repetition_time_s
        inner_loop.loop.num_repetitions = first_widget.values.num_chirps
        outer_loop.loop.sub_sequence = inner_loop

        chirp = ElementSequence()
        chirp.type = FmcwElementType.IFX_SEQ_CHIRP
        chirp.chirp = ChirpValues()
        chirp.chirp.setup_simple(first_widget.values)
        chirp.chirp_sequence = 0
        inner_loop.loop.sub_sequence = chirp
        return outer_loop
        
    def loop_through_suquence(self, first_widget: ContainerLabel, chirp_sequence: int = 0) -> ElementSequence:
        """Loop through the gui widgets to get the contained values to create a picklable object to pass through a queue.

        Args:
            action_first (ContainerLabel): _description_
            chirp_sequence (int, optional): _description_. Defaults to 0.

        Returns:
            ElementSequence: _description_
        """
        current_widget = first_widget
        previous_element_sequence: Optional[ElementSequence] = None
        first_element_sequence: Optional[ElementSequence] = None
        
        while True:
            element_sequence = ElementSequence()

            if current_widget.label_name == Actions.Chirp.value:
                element_sequence.type = FmcwElementType.IFX_SEQ_CHIRP
                element_sequence.chirp = current_widget.values
                element_sequence.chirp_sequence = chirp_sequence
                chirp_sequence += 1
            elif current_widget.label_name == Actions.Delay.value:
                element_sequence.type = FmcwElementType.IFX_SEQ_DELAY
                element_sequence.delay = current_widget.values
            elif current_widget.label_name == Actions.Loop.value:
                element_sequence.type = FmcwElementType.IFX_SEQ_LOOP
                loop_sequence, chirp_sequence = self.loop_through_suquence(current_widget.sub_element, chirp_sequence)
                current_widget.values.sub_sequence = loop_sequence
                element_sequence.loop = current_widget.values

            if previous_element_sequence is not None:
                previous_element_sequence.next_element = element_sequence
                
            if current_widget == first_widget:
                first_element_sequence = element_sequence
            
            if current_widget.next_element is None:
                element_sequence.next_element = None
                break
            
            previous_element_sequence = element_sequence
            current_widget = current_widget.next_element
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
                    current_movement_list.append(CreateLine(WaveformSections.LOOP_TIME.name, current_sequence.loop.repetition_time_s - child_duration, 0, 0))
        if current_sequence.type == FmcwElementType.IFX_SEQ_DELAY:
            current_movement_list.append(CreateLine(WaveformSections.DELAY.name, current_sequence.delay.time_s, 0, 0))
        if current_sequence.type == FmcwElementType.IFX_SEQ_CHIRP:
            ramp_time_period = current_sequence.chirp.num_samples / current_sequence.chirp.sample_rate_Hz
            ramp_speed = (current_sequence.chirp.end_frequency_Hz - current_sequence.chirp.start_frequency_Hz) / ramp_time_period
            pre_pa_frequnecy = current_sequence.chirp.start_frequency_Hz - (WaveformSections.PA_DELAY.value * ramp_speed)
            pre_ramp_frequency = current_sequence.chirp.start_frequency_Hz + (WaveformSections.ADC_DELAY.value * ramp_speed)
            end_ramp_frequency = current_sequence.chirp.end_frequency_Hz + (WaveformSections.RAMP_END.value * ramp_speed)
            
            current_movement_list.append(CreateLine(WaveformSections.PLL_LOCK.name, WaveformSections.PLL_LOCK.value, _STARTING_FREQ, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.INIT_0.name, WaveformSections.INIT_0.value, pre_pa_frequnecy, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.INIT_1.name, WaveformSections.INIT_1.value, pre_pa_frequnecy, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.PRE_CHIRP.name, WaveformSections.PRE_CHIRP.value, pre_pa_frequnecy, pre_pa_frequnecy))
            
            current_movement_list.append(CreateLine(WaveformSections.PA_DELAY.name, WaveformSections.PA_DELAY.value, pre_pa_frequnecy, current_sequence.chirp.start_frequency_Hz))
            current_movement_list.append(CreateLine(WaveformSections.ADC_DELAY.name, WaveformSections.ADC_DELAY.value, current_sequence.chirp.start_frequency_Hz, pre_ramp_frequency, chirp=True))
            current_movement_list[-1].chirp_sequence = current_sequence.chirp_sequence
            current_movement_list[-1].if_gain_dB = current_sequence.chirp.if_gain_dB
            current_movement_list[-1].hp_cutoff_Hz = current_sequence.chirp.hp_cutoff_Hz
            current_movement_list[-1].lp_cutoff_Hz = current_sequence.chirp.lp_cutoff_Hz
            current_movement_list[-1].tx_power_level = current_sequence.chirp.tx_power_level
            
            current_movement_list.append(CreateLine(WaveformSections.RAMP.name, ramp_time_period - WaveformSections.ADC_DELAY.value, pre_ramp_frequency, current_sequence.chirp.end_frequency_Hz, chirp=True))                        
            current_movement_list[-1].chirp_sequence = current_sequence.chirp_sequence
            current_movement_list[-1].if_gain_dB = current_sequence.chirp.if_gain_dB
            current_movement_list[-1].hp_cutoff_Hz = current_sequence.chirp.hp_cutoff_Hz
            current_movement_list[-1].lp_cutoff_Hz = current_sequence.chirp.lp_cutoff_Hz
            current_movement_list[-1].tx_power_level = current_sequence.chirp.tx_power_level
            
            current_movement_list.append(CreateLine(WaveformSections.RAMP_END.name, WaveformSections.RAMP_END.value, current_sequence.chirp.end_frequency_Hz, end_ramp_frequency))
            current_movement_list.append(CreateLine(WaveformSections.LOWER_RAMP.name, WaveformSections.LOWER_RAMP.value, end_ramp_frequency, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.POST_CHIRP.name, WaveformSections.POST_CHIRP.value, pre_pa_frequnecy, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.CHIRP_END_0.name, WaveformSections.CHIRP_END_0.value, pre_pa_frequnecy, pre_pa_frequnecy))
            current_movement_list.append(CreateLine(WaveformSections.CHIRP_END_1.name, WaveformSections.CHIRP_END_1.value, pre_pa_frequnecy, pre_pa_frequnecy))

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
        self.chirp_info_list = []
        current_location = 0
        movement_coordinates_list = []
        colors = []
        for movement_item in movement_list:
            next_location = current_location + movement_item.duration
            if movement_item.chirp:
                self.chirp_info_list.append(movement_item)
            if movement_item.name not in (WaveformSections.LOOP_TIME.name, WaveformSections.DELAY.name):
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

    def get_json_dictionary(self) -> Dict[str, str]:
        """Recurse through every element in the sequence and get the pertinent info.

        Returns:
            A key value pair for recreating the sequence.
        """
        my_contents: List[Dict[str, str]] = []

        for chirp_info in self.chirp_info_list:
            my_contents.append(chirp_info.get_json_dictionary)
        return {"chirp_info_list": my_contents}
        