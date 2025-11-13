"""Some helpers that the front end and backend can use."""
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag, QPixmap, QDragMoveEvent
from typing import Generator, List

background_color = "#1A1A1A"
hover_color = "#4A4A4A"
clicked_color = "#8A8A8A"
border_color = "#90ADC3"


global_budget_window_style = (
    f"background-color: {background_color};"
    "border-style: outset;"
    "border-width: 2px;"
    "border-radius: 10px;"
    f"border-color: {border_color};"
    f"color: {border_color};"
    "font: bold 14px;"
    "min-width: 50px;"
    "padding: 6px;"
)

drop_area_style = (
    f"background-color: {background_color};"
    f"color: {border_color};"
    "font: bold 14px;"
    "min-width: 50px;"
    "border: none;"
    "padding: 6px;"
)

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