"""Some helpers that the front end and backend can use."""
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag, QPixmap, QDragMoveEvent
from typing import Generator, List

from pathlib import Path
from typing import NamedTuple, Dict, Any
from enum import Enum

from dataclasses import dataclass

ModuleInfo = NamedTuple("ModuleInfo", [("module_path", Path), ("module_name", str)])

_METHOD_FOLDER = Path("transformation_methods")

_SINGLE_TRANSFORM_PATH = _METHOD_FOLDER / "single_frame_transforms.py"
_SINGLE_TRANSFORM_NAME = "Single Frame Transforms"
_SINGLE_TRANSFORM_INFO = ModuleInfo(_SINGLE_TRANSFORM_PATH, _SINGLE_TRANSFORM_NAME)

_HISTORY_TRANSFORM_PATH = _METHOD_FOLDER / "frame_history_transforms.py"
_HISTORY_FEATURES_NAME = "Frame History Transforms"
_HISTORY_TRANSFORMS_INFO = ModuleInfo(_HISTORY_TRANSFORM_PATH, _HISTORY_FEATURES_NAME)

_NO_DATA_EDIT = "NOEDIT"
_SEPERATE_FIRST_DIM = "ONE_DIM"

_RECEIVER_COUNT = 3

_NO_METHOD = "none"

background_color = "#1A1A1A"
hover_color = "#4A4A4A"
clicked_color = "#8A8A8A"
border_color = "#5A5A5A"


global_budget_window_style = (
    f"background-color: {background_color};"
    "border-style: outset;"
    "border-width: 4px;"
    "border-radius: 10px;"
    f"border-color: {border_color};"
    f"color: {border_color};"
    "font: bold 14px;"
    "min-width: 10px;"
    "padding: 6px;"
)

drop_area_style = (
    f"background-color: {background_color};"
    f"color: {border_color};"
    "font: bold 14px;"
    "min-width: 10px;"
    "border: none;"
    "padding: 6px;"
)

small_item_window_style = (
    "border-radius: 0px;"
)

@dataclass
class Label:
    name: str
    units: str
    
    def __str__(self) -> str:
        return f"{self.name} {self.units}"

@dataclass
class PerSubPlot:
    def __init__(self):
        self.sub_plot_name: str = "Receiver"
        self.x_axis_label = Label("Long Time", "Bin(s)")

class GraphInfo:
    def __init__(self):
        self.line_color: str = "white"
        self.tab_names: List[str] = []
        self.per_subplot_info: List[PerSubPlot] = []
        self.y_axis_label: Label = Label("Short Time", "Bin(s)")
        self.z_axis_label: Label = Label("Amplitude", "ADC Return(s)")
    
class TertiaryData:
    """Numpy data that has a time stamp."""
    def __init__(self):
        self.notable_events: Dict[str, int] = {}
        self.fundamentals: Dict[str, Any] = {}
        self.graph_info = GraphInfo()


class LoadType(Enum):
    NO_APPEND = "No Append"
    APPEND_FLATTEN_CHIRPS = "Append Flattened Chirps"
    APPEND_SHORT_TIME = "Append Short Time"
    APPEND_CHIRPS = "Append Chirps"

class Models(Enum):
    SMALLAUTOENCODER = "Small Auto Encoder"
    AUTOENCODER = "Auto Encoder"

class LossType(Enum):
    MSE = "MSE"
    MAE = "MAE"

class DraggableLabel(QtWidgets.QLabel):
    def mouseMoveEvent(self, event: QDragMoveEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData("application/x-qwidget", b"MyWidgetInfo")
            drag.setMimeData(mime)

            pixmap = QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)

            drag.exec(Qt.DropAction.CopyAction)

class WindowWidgets():
    def __init__(self):
        """Setup button style so it has feedback.
        """
        for button in self.buttons:
            button.setStyleSheet(
                "QPushButton:hover {"
                f"background-color: {hover_color};"
                "}"
                "QPushButton:pressed {"
                f"background-color: {clicked_color};"
                "}"
            )
    
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

    def get_json_dictionary(self) -> Dict[str, str]:
        my_contents_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, (LineEditWithText, ComboBoxWithText)):
                my_contents_dict[key] = value.getInnerText()
        return my_contents_dict

    def set_json_dictionary(self, json_dictionary: Dict[str, str]) -> None:
        for key, value in json_dictionary.items():
            self.__dict__[key].setInnterText(value)

class LineEditWithText(QtWidgets.QWidget):
    def __init__(self, text: str):
        super().__init__()
        self.setObjectName(text)
        self.line_edit = QtWidgets.QLineEdit(self)
        self.label = QtWidgets.QLabel(self)
        self.label.setText(text)
        self.root_layout = QtWidgets.QHBoxLayout()
        self.root_layout.addWidget(self.label)
        self.root_layout.addWidget(self.line_edit)
        self.setLayout(self.root_layout)
        self.label.setStyleSheet(drop_area_style)
        self.setMinimumSize(250, 50)
    
    def getInnerText(self) -> str:
        return self.line_edit.text()
        
    def setInnerText(self, text: str):
        self.line_edit.setText(text)

class ComboBoxWithText(QtWidgets.QWidget):
    def __init__(self, text: str, options: List[str]):
        super().__init__()
        self.setObjectName(text)
        self.combo_box = QtWidgets.QComboBox(self)
        self.combo_box.addItems(options)
        self.combo_box.setCurrentIndex(0)
        self.label = QtWidgets.QLabel(self)
        self.label.setText(text)
        self.root_layout = QtWidgets.QHBoxLayout()
        self.root_layout.addWidget(self.label)
        self.root_layout.addWidget(self.combo_box)
        self.setLayout(self.root_layout)
        self.label.setStyleSheet(drop_area_style)
        self.setMinimumSize(250, 50)
    
    def getInnerText(self) -> str:
        return self.combo_box.currentText()
    
    def setInnerText(self, text: str):
        self.combo_box.setCurrentText(text)