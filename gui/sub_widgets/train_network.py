"""The window for displaying the bloch spheres."""
from gui.sub_widgets.render_window import RenderWindowControl
from gui.sub_widgets.view_transforms import ViewTransforms
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from gui.helpers import WindowWidgets


class TrainNetworkWidgets(WindowWidgets):
    """The widgets for the rx transforms.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.load_button = QtWidgets.QPushButton()
        super().__init__()


class TrainNetwork(QtWidgets.QFrame):
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
        
    