"""The window for displaying the bloch spheres."""
from gui.sub_widgets.render_window import RenderWindowControl
from gui.sub_widgets.view_transforms import ViewTransforms
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from gui.helpers import WindowWidgets, LineEditWithText


class ViewCapturedWidgets(WindowWidgets):
    """The widgets for the rx transforms.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.load_button = QtWidgets.QPushButton("Load Frames Recursively")
        self.apply_transform = QtWidgets.QPushButton("Apply Viewed Transform To All Data")
        self.save_location = LineEditWithText("Save Location")
        self.save_file_explorer = QtWidgets.QPushButton("Save Transformed Data At")
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
        self.load_layout.addWidget(
            self.widgets.save_file_explorer,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.load_layout.addWidget(
            self.widgets.save_location,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.load_layout.addWidget(
            self.widgets.apply_transform,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

