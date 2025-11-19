"""The main window for the gui."""
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from gui.helpers import global_budget_window_style
from gui.sub_widgets.view_captured import ViewCaptured
from gui.sub_widgets.render_window import RenderWindowControl
from gui.sub_widgets.capture_window import CaptureWindow
from gui.sub_widgets.signal_window import SignalWindow

from dataclasses import dataclass

def start_application() -> QtWidgets.QApplication:
    """The application object which is used to start the window thread."""
    return QtWidgets.QApplication([])  

@dataclass
class SubWidgets():
    """The different windows that exist within the main one."""
    render_control: RenderWindowControl
    capture_window: CaptureWindow
    signal_window: SignalWindow
    view_captured: ViewCaptured


class MainWindow(QtWidgets.QMainWindow):
    """The main widget for the window."""
    def __init__(self) -> None:
        """The initialization for the main window."""
        super().__init__(parent=None)
        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Main Window")

        self.setStyleSheet(global_budget_window_style)
        render_window = RenderWindowControl()
        self.sub_window_widgets: SubWidgets = SubWidgets(
            render_window, CaptureWindow(), SignalWindow(), ViewCaptured(render_window)
        )

        # add the main widget to the root
        self.central_widget = QtWidgets.QWidget()

        self._init_widgets()

        self.central = self.setCentralWidget(self.central_widget)
        
    def _init_widgets(self) -> None:
        """Initialize th separate sub windows and toolbar."""
        self.root_layoutV = QtWidgets.QVBoxLayout()
        
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self.sub_window_widgets.view_captured, "View Captured Data")
        self.tabs.addTab(self.sub_window_widgets.capture_window, "Capture Window")
        self.tabs.addTab(self.sub_window_widgets.signal_window, "Signal Window")
        self.timeout_label = QtWidgets.QLabel()
        self.timeout_label.setText("Active")
        
        self.status_bar = QtWidgets.QToolBar()
        self.status_bar.addWidget(self.timeout_label)

        self.root_layoutV.addWidget(self.tabs)
        self.root_layoutV.addWidget(self.status_bar)
        self.central_widget.setLayout(self.root_layoutV)