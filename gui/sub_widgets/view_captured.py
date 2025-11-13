"""The window for displaying the bloch spheres."""
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from gui.sub_widgets.render_window import RenderWindowControl
from gui.sub_widgets.view_transforms import ViewTransforms
from matplotlib.figure import Figure
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from enum import Enum
from gui.helpers import WindowWidgets
from typing import Generator

class ViewCapturedWidgets(WindowWidgets):
    """The widgets for the rx transforms.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.load_button = QtWidgets.QPushButton()
        super().__init__()

class ViewCaptured(QtWidgets.QFrame):
    """The frame for displaying the transforms for the rx information.
    """
    def __init__(self, render_window: RenderWindowControl) -> None:
        """Initialize the window for the rx transforms.
        """
        super().__init__()
        self.render_window = render_window
        self.root_layoutH = QtWidgets.QHBoxLayout()
        self.display_layout = QtWidgets.QVBoxLayout()
        self.load_layout = QtWidgets.QHBoxLayout()
        self.view_transforms_window = ViewTransforms()
        self.widgets: ViewCapturedWidgets = ViewCapturedWidgets()
        self.setObjectName("ViewCaptured")
        self.setLayout(self.root_layoutH)
        self.root_layoutH.addWidget(self.render_window)
        self.display_layout.addWidget(self.view_transforms_window)
        self.display_layout.addLayout(self.load_layout)
        self.root_layoutH.addLayout(self.display_layout)
        
        self.load_layout.addWidget(
            self.widgets.load_button,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.widgets.load_button.setText("Load Frames Recursively")
