"""The window for controlling the animation."""
from PyQt6 import QtCore
from PyQt6 import QtWidgets
from PyQt6 import QtGui
from gui.helpers import hover_color, clicked_color
from typing import Generator

_LABEL_WIDTH = 400

class RenderWindowControlWidgets():
    """The widgets for the animation control window."""
    
    def __init__(self) -> None:
        """Initialize each widget within the window."""
        
        self.next_button = QtWidgets.QPushButton()
        self.prev_button = QtWidgets.QPushButton()
        self.play_button = QtWidgets.QPushButton()
        self.to_x_block = QtWidgets.QPushButton()
        self.which_bloch = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.array_title = QtWidgets.QLabel()
        
    @property
    def buttons(self) -> Generator[QtWidgets.QPushButton, None, None]:
        """Get every button that exists in the frame.
        
        Yields:
            A button that exists in the frame.
        """
        buttons = []
        for item in self.__dict__.values():
            if isinstance(item, QtWidgets.QPushButton):
                buttons.append(item)
        return buttons

class RenderWindowControl(QtWidgets.QFrame):
    """The frame for controlling the animation."""
    
    def __init__(self) -> None:
        """Initialize the animation control window."""
        
        super().__init__()
        self.main_layout = QtWidgets.QGridLayout()
        
        self.widgets = RenderWindowControlWidgets()

        self.setLayout(self.main_layout)
        self.widgets.next_button.setText("next")
        self.widgets.prev_button.setText("prev")
        self.widgets.to_x_block.setText("go to x")
        self.main_layout.addWidget(
            self.widgets.next_button,
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(
            self.widgets.prev_button,
            0, 
            1,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.main_layout.addWidget(self.widgets.to_x_block, 0, 2, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.widgets.which_bloch, 1, 1, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.widgets.array_title, 2, 1, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred)
        self.widgets.array_title.setFixedHeight(50)
        self.setMaximumWidth(_LABEL_WIDTH)
        self.widgets.array_title.setMaximumWidth(200)
        self.widgets.array_title.setMinimumWidth(200)
        self.widgets.array_title.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        self.widgets.array_title.setWordWrap(False)
        self.main_layout.setColumnStretch(1, 0)

        self.setup_buttons()

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
        
    def setup_buttons(self):
        """Setup button style so it has feedback.
        """
        for button in self.widgets.buttons:
            button.setStyleSheet(
                "QPushButton:hover {"
                f"background-color: {hover_color};"
                "}"
                "QPushButton:pressed {"
                f"background-color: {clicked_color};"
                "}"
            )
