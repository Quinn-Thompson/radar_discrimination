"""The window for displaying the rx information."""
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from gui.sub_widgets.view_transforms import ViewTransforms
from matplotlib.figure import Figure
from PyQt6 import QtWidgets, QtCore
from typing import Generator
from gui.helpers import WindowWidgets

class CaptureWindowWidgets(WindowWidgets):
    """The widgets for the rx info window.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.capture_button_time = QtWidgets.QPushButton()
        self.capture_button_frames = QtWidgets.QPushButton()
        self.input_line = QtWidgets.QLineEdit()
        self.save_button = QtWidgets.QPushButton()
        self.save_location = QtWidgets.QLineEdit()
        self.packet_prefix = QtWidgets.QLineEdit()
        super().__init__()


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
        self.view_transforms_window = ViewTransforms()
        self.main_layout.addWidget(self.view_transforms_window)
        self.main_layout.addLayout(self.buttons_layout)
        self.main_layout.addLayout(self.save_layout)
        
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