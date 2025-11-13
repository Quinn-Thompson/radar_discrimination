"""The window for displaying the bloch spheres."""
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from gui.sub_widgets.render_window import RenderWindowControl
from matplotlib.figure import Figure
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from enum import Enum
from gui.helpers import WindowWidgets
from typing import Generator

class GraphTypes(Enum):
    plot_2d = "2D Plot"
    colormesh = "Color Mesh"


class ViewTransformsWidgets(WindowWidgets):
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
        super().__init__()


class ViewTransforms(QtWidgets.QFrame):
    """The frame for displaying the transforms for the rx information.
    """
    def __init__(self) -> None:
        """Initialize the window for the rx transforms.
        """
        super().__init__()
        self.root_layoutV = QtWidgets.QVBoxLayout()
        self.widgets: ViewTransformsWidgets = ViewTransformsWidgets()
        self.setObjectName("ViewTransforms")
        self.setLayout(self.root_layoutV)
        self.matplotlib_layout = QtWidgets.QGridLayout()
        self.graph_layout = QtWidgets.QGridLayout()
        self.method_layout = QtWidgets.QGridLayout()
        
        self.root_layoutV.addLayout(self.matplotlib_layout)
        self.root_layoutV.addLayout(self.graph_layout)
        self.root_layoutV.addLayout(self.method_layout)
        
        self.matplotlib_layout.addWidget(
            self.widgets.graph_widgets,
            0, 
            0,
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
        
        for graph_type in GraphTypes:
            self.widgets.graph_type.addItem(graph_type.value)
        
        self.widgets.refresh.setText("Refresh")
