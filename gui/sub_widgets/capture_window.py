"""The window for displaying the rx information."""
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6 import QtWidgets, QtCore
from typing import Generator
from gui.helpers import hover_color, clicked_color

class CaptureWindowWidgets():
    """The widgets for the rx info window.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.figure = Figure(figsize=(14, 8), constrained_layout=True, edgecolor='white')
        self.graph_widgets: FigureCanvas = FigureCanvas(self.figure)
        self.capture_button_time = QtWidgets.QPushButton()
        self.capture_button_frames = QtWidgets.QPushButton()
        self.input_line = QtWidgets.QLineEdit()
        self.save_button = QtWidgets.QPushButton()
        self.save_location = QtWidgets.QLineEdit()
        self.packet_prefix = QtWidgets.QLineEdit()

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

class CaptureWindow(QtWidgets.QFrame):
    """The frame for displaying the bloch spheres.
    """
    def __init__(self) -> None:
        """Initialize the bloch spheres window.
        """
        super().__init__()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.widgets: CaptureWindowWidgets = CaptureWindowWidgets()
        self.setObjectName("BlochWindow")
        self.setLayout(self.main_layout)
        self.matplotlib_layout = QtWidgets.QGridLayout()
        self.buttons_layout = QtWidgets.QGridLayout()
        self.save_layout = QtWidgets.QGridLayout()
        self.main_layout.addLayout(self.buttons_layout)
        self.main_layout.addLayout(self.matplotlib_layout)
        self.main_layout.addLayout(self.save_layout)
        
        self.matplotlib_layout.addWidget(
            self.widgets.graph_widgets,
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        
        self.buttons_layout.addWidget(
            self.widgets.capture_button_time,
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.buttons_layout.addWidget(
            self.widgets.capture_button_frames,
            0, 
            1,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.buttons_layout.addWidget(
            self.widgets.input_line,
            0, 
            2,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.widgets.capture_button_time.setText("Capture For X Time")
        self.widgets.capture_button_frames.setText("Capture X Frames")
        
        self.save_layout.addWidget(
            self.widgets.save_location,
            0,
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.save_layout.addWidget(
            self.widgets.packet_prefix,
            0,
            1,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.save_layout.addWidget(
            self.widgets.save_button,
            0,
            2,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        
        self.widgets.save_button.setText("Save Data Location")

        self.setup_buttons()
        
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