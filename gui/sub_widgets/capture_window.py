"""The window for displaying the rx information."""
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from gui.sub_widgets.view_transforms import ViewTransforms
from matplotlib.figure import Figure
from PyQt6 import QtWidgets, QtCore
from typing import Generator, Dict
from gui.helpers import WindowWidgets, LineEditWithText

class CaptureWindowWidgets(WindowWidgets):
    """The widgets for the rx info window.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.capture_button_time = QtWidgets.QPushButton()
        self.capture_button_frames = QtWidgets.QPushButton()
        self.amount_to_capture = LineEditWithText("Capture Amount/Time")
        self.save_button = QtWidgets.QPushButton()
        self.save_location = LineEditWithText("Save Location")
        self.packet_prefix = LineEditWithText("Capture Save Prefix")
        
        self.start_acq = QtWidgets.QPushButton()
        self.stop_acq = QtWidgets.QPushButton()
        
        super().__init__()

class CaptureWindow(QtWidgets.QFrame):
    """The frame for displaying the bloch spheres.
    """
    def __init__(self) -> None:
        """Initialize the bloch spheres window.
        """
        super().__init__()
        self.main_layout = QtWidgets.QHBoxLayout()
        self.widgets: CaptureWindowWidgets = CaptureWindowWidgets()
        self.setObjectName("BlochWindow")
        self.setLayout(self.main_layout)
        self.buttons_layout = QtWidgets.QVBoxLayout()
        self.view_transforms_window = ViewTransforms()

        self.main_layout.addLayout(self.buttons_layout)
        self.main_layout.addWidget(self.view_transforms_window)
        
        self.buttons_layout.addWidget(
            self.widgets.capture_button_time,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.buttons_layout.addWidget(
            self.widgets.capture_button_frames,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.buttons_layout.addWidget(
            self.widgets.amount_to_capture,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.widgets.capture_button_time.setText("Capture For X Time")
        self.widgets.capture_button_frames.setText("Capture X Frames")
        
        self.buttons_layout.addWidget(
            self.widgets.save_location,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.buttons_layout.addWidget(
            self.widgets.packet_prefix,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.buttons_layout.addWidget(
            self.widgets.save_button,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        
        self.buttons_layout.addWidget(
            self.widgets.start_acq,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        
        self.buttons_layout.addWidget(
            self.widgets.stop_acq,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        
        self.widgets.start_acq.setText("Start Acquiring")
        self.widgets.stop_acq.setText("Stop Acquiring")
        
        self.widgets.save_button.setText("Save Data Location")