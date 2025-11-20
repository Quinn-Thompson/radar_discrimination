"""The main window for the gui."""
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from gui.helpers import global_budget_window_style
from gui.sub_widgets.view_captured import ViewCaptured
from gui.sub_widgets.render_window import RenderWindowControl
from gui.sub_widgets.capture_window import CaptureWindow
from gui.sub_widgets.signal_window import SignalWindow
from typing import Dict
from dataclasses import dataclass
import json

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
        self.save_load_layout = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton()
        self.save_button.setText("Save JSON")
        self.load_button = QtWidgets.QPushButton()
        self.load_button.setText("Load JSON")

        self.save_load_layout.addWidget(self.save_button)
        self.save_load_layout.addWidget(self.load_button)
        
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self.sub_window_widgets.view_captured, "View Captured Data")
        self.tabs.addTab(self.sub_window_widgets.capture_window, "Capture Window")
        self.tabs.addTab(self.sub_window_widgets.signal_window, "Signal Window")
        self.timeout_label = QtWidgets.QLabel()
        self.timeout_label.setText("Active")
        
        self.status_bar = QtWidgets.QToolBar()
        self.status_bar.addWidget(self.timeout_label)
        self.root_layoutV.addLayout(self.save_load_layout)
        self.root_layoutV.addWidget(self.tabs)
        self.root_layoutV.addWidget(self.status_bar)
        self.central_widget.setLayout(self.root_layoutV)
        
    def get_json_dictionary(self) -> Dict[str, str]:
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Select JSON file",
            "",
            "JSON Files (*.json)"
        )
        
        if file_path:
            data = self.sub_window_widgets.signal_window.get_json_dictionary()

            if not file_path.endswith(".json"):
                file_path += ".json"
            with open(file_path, "w") as file_pointer:
                json.dump(data, file_pointer, indent=4)


            
    def set_json_dictionary(self, json_dictionary: Dict[str, str]):
        
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select JSON file",
            "",
            "JSON Files (*.json)"
        )

        if file_path:
            with open(file_path, "r") as file_pointer:
                json_dictionary = json.load(file_pointer)
                self.sub_window_widgets.signal_window.set_json_dictionary(json_dictionary)