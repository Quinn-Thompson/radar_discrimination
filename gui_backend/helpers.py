"""A helper function to prevent circular imports."""
from gui.sub_widgets.signal_window import ChirpValues, LoopValues, DelayValues
from typing import Optional
from ifxradarsdk.fmcw.types import FmcwElementType
from PyQt6 import QtWidgets, QtCore
import numpy as np
from enum import Enum

_RECEIVER_COUNT = 3


class EventsToHandle(Enum):
    NEW_SEQUENCE = 0
    STOP_ACQUISITION = 1
    START_ACQUISITION = 2


class WaveformSections(Enum):
    PLL_LOCK = 4.0e-6
    INIT_0 = 41.05e-6
    INIT_1= 7.0375e-6
    PRE_CHIRP = 1.125e-6
    PA_DELAY = 1.875e-6
    ADC_DELAY = 3.1125e-6

    RAMP = 0.0

    RAMP_END = 12.5e-9
    LOWER_RAMP = 75.0e-9
    POST_CHIRP = 1.4625e-6
    CHIRP_END_0 = 25.0e-9
    CHIRP_END_1 = 25.0e-9
    
    LOOP_TIME = -1.0
    DELAY = -2.0

class CreateLine():
    def __init__(self, name: WaveformSections, duration: float, starting_frequency: float, ending_frequency: float, chirp: Optional[bool] = False):
        self.name = name
        self.duration = duration    
        self.starting_frequency = starting_frequency
        self.ending_frequency = ending_frequency
        self.chirp = chirp
        if chirp:
            self.chirp_sequence = 0
    
    def enact_movement(self, total_size: int, total_duration: Optional[float] = None):
        if total_duration is None:
            total_duration = self.duration
        sub_space = int(round((self.duration / total_duration) * total_size))
        return np.linspace(self.starting_frequency, self.ending_frequency, sub_space)

class Popup(QtWidgets.QDialog):
    def __init__(self, string_to_display: str):
        super().__init__()
        self.root_layoutH = QtWidgets.QHBoxLayout()
        self.setWindowTitle("Traceback")
        self.setLayout(self.root_layoutH)
        
        self.error_label = QtWidgets.QLabel(string_to_display)
        self.root_layoutH.addWidget(self.error_label)
        self.root_layoutH.addWidget(QtWidgets.QPushButton("Ok", clicked=self.accept))
        
        self.error_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse | QtCore.Qt.TextInteractionFlag.TextSelectableByKeyboard)

    def launch(self):
        self.exec()

class ElementSequence():
    def __init__(self):
        self.next_element: "ElementSequence" = None
        self.type: FmcwElementType = None
        self.delay: Optional[DelayValues]
        self.chirp: Optional[ChirpValues]
        self.loop: Optional[LoopValues]
        
        self.chirp_sequence = -1
