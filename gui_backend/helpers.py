"""A helper function to prevent circular imports."""
from gui.sub_widgets.signal_window import ChirpValues, LoopValues, DelayValues
from typing import Optional
from ifxradarsdk.fmcw.types import FmcwElementType

_RECEIVER_COUNT = 3

class ElementSequence():
    def __init__(self):
        self.next_element: "ElementSequence" = None
        self.type: FmcwElementType = None
        self.delay: Optional[DelayValues]
        self.chirp: Optional[ChirpValues]
        self.loop: Optional[LoopValues]
