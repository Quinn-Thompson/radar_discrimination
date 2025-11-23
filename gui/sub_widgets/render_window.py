"""The window for controlling the animation."""
from PyQt6 import QtCore
from PyQt6 import QtWidgets
from PyQt6 import QtGui
from gui.helpers import hover_color, clicked_color, LineEditWithText, WindowWidgets
from typing import Generator

_LABEL_WIDTH = 400

class RenderWindowControlWidgets(WindowWidgets):
    """The widgets for the animation control window."""
    
    def __init__(self) -> None:
        """Initialize each widget within the window."""
        
        self.next_button = QtWidgets.QPushButton("Next Frame")
        self.prev_button = QtWidgets.QPushButton("Previous Frame")
        self.next_session = QtWidgets.QPushButton("Next Capture Session")
        self.prev_session = QtWidgets.QPushButton("Previous Capture Session")
        self.replay_button = QtWidgets.QPushButton("Replay Session")
        self.play_button = QtWidgets.QPushButton("Play Session From Index")
        self.which_session = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.which_data = LineEditWithText("Frame Index")
        self.array_title = QtWidgets.QLabel()

class RenderWindowControl(QtWidgets.QFrame):
    """The frame for controlling the animation."""
    
    def __init__(self) -> None:
        """Initialize the animation control window."""
        
        super().__init__()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.session_layout = QtWidgets.QHBoxLayout()
        self.frame_layout = QtWidgets.QHBoxLayout()
        self.play_session_layout = QtWidgets.QHBoxLayout()
        self.widgets = RenderWindowControlWidgets()

        self.setLayout(self.main_layout)
        self.session_layout.addWidget(self.widgets.next_session, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.session_layout.addWidget(self.widgets.prev_session, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addLayout(self.session_layout)
        
        self.main_layout.addWidget(self.widgets.which_session, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        
        self.frame_layout.addWidget(self.widgets.next_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.frame_layout.addWidget(self.widgets.prev_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addLayout(self.frame_layout)

        self.main_layout.addWidget(self.widgets.array_title, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.widgets.which_data, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        self.play_session_layout.addWidget(self.widgets.play_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.play_session_layout.addWidget(self.widgets.replay_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addLayout(self.play_session_layout)

        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred)
        self.widgets.array_title.setFixedHeight(50)
        self.setMaximumWidth(_LABEL_WIDTH)
        self.widgets.array_title.setMaximumWidth(200)
        self.widgets.array_title.setMinimumWidth(200)
        self.widgets.array_title.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        self.widgets.array_title.setWordWrap(False)

    def set_elided_text(self, text: str):
        metrics = QtGui.QFontMetrics(self.widgets.array_title.font())
        text += " "*100
        result = ""
        current_width = 0
        for char in text:
            char_width = metrics.horizontalAdvance(char)
            if current_width + char_width > (self.width() - 20):
                break
            result += char
            current_width += char_width
                    

        self.widgets.array_title.setText(result)
