"""The window for displaying the bloch spheres."""
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from gui.sub_widgets.render_window import RenderWindowControl
from matplotlib.figure import Figure
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from enum import Enum
from gui.helpers import hover_color, clicked_color
from typing import Generator

class GraphTypes(Enum):
    plot_2d = "2D Plot"
    colormesh = "Color Mesh"


class ViewTransformsWidgets():
    """The widgets for the rx transforms.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """

        self.figure = Figure(figsize=(14, 8), constrained_layout=True, edgecolor='white')
        self.graph_widgets: FigureCanvas = FigureCanvas(self.figure)
        self.method_dropdown = QtWidgets.QComboBox()
        self.graph_type = QtWidgets.QComboBox()
        self.refresh = QtWidgets.QPushButton()
        self.data_location = QtWidgets.QLineEdit()
        self.load_button = QtWidgets.QPushButton()
        self.run_transforms = QtWidgets.QPushButton()

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

class ViewTransforms(QtWidgets.QFrame):
    """The frame for displaying the transforms for the rx information.
    """
    def __init__(self, render_window: RenderWindowControl) -> None:
        """Initialize the window for the rx transforms.
        """
        super().__init__()
        self.render_window = render_window
        self.root_layoutH = QtWidgets.QHBoxLayout()
        self.display_layout = QtWidgets.QVBoxLayout()
        self.widgets: ViewTransformsWidgets = ViewTransformsWidgets()
        self.setObjectName("ViewTransforms")
        self.root_layoutH.addWidget(self.render_window)
        self.root_layoutH.addLayout(self.display_layout)
        self.setLayout(self.root_layoutH)
        self.matplotlib_layout = QtWidgets.QGridLayout()
        self.data_layout = QtWidgets.QGridLayout()
        self.graph_layout = QtWidgets.QGridLayout()
        self.method_layout = QtWidgets.QGridLayout()
        
        self.display_layout.addLayout(self.matplotlib_layout)
        self.display_layout.addLayout(self.data_layout)
        self.display_layout.addLayout(self.graph_layout)
        self.display_layout.addLayout(self.method_layout)
        
        self.matplotlib_layout.addWidget(
            self.widgets.graph_widgets,
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        
        self.data_layout.addWidget(
            self.widgets.data_location,
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.data_layout.addWidget(
            self.widgets.load_button,
            0, 
            1,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.graph_layout.addWidget(
            self.widgets.graph_type,
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        
        self.method_layout.addWidget(
            self.widgets.method_dropdown,
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.method_layout.addWidget(
            self.widgets.refresh,
            0, 
            1,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.method_layout.addWidget(
            self.widgets.run_transforms,
            0, 
            2,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

        for graph_type in GraphTypes:
            self.widgets.graph_type.addItem(graph_type.value)
        
        self.widgets.refresh.setText("Refresh")
        self.widgets.load_button.setText("Load Data From Folder")
        self.widgets.run_transforms.setText("Run Transforms")
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