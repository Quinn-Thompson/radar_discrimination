"""The window for displaying the rx information."""
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6 import QtWidgets, QtCore
from typing import Generator, Union, Optional
from gui.helpers import hover_color, DraggableLabel, global_budget_window_style, drop_area_style, border_color, LineEditWithText, ComboBoxWithText, WindowWidgets
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QColor, QPen
from PyQt6.QtCore import Qt
import types
from enum import Enum

class Actions(Enum):
    Loop = "Loop"
    Chirp = "Chirp"
    Delay = "Delay"

class LoopWidgets(WindowWidgets):
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.number_of_reps = LineEditWithText("Number Of Repetitions")
        self.rep_time = LineEditWithText("Repetition Time")
        super().__init__()

class ChirpWidgets(WindowWidgets):
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.start_freq = LineEditWithText("Start Frequency")
        self.end_freq = LineEditWithText("End Frequency")
        self.samples_per_chirp = ComboBoxWithText("High Pass Threshold", ["2", "4", "8", "16", "32", "64", "128", "256", "512", "1024"])
        self.sample_rate = LineEditWithText("Sample Rate")
        self.tx_power_level = LineEditWithText("Transmission Power Level")
        self.if_gain = LineEditWithText("IF Gain")
        self.high_pass = ComboBoxWithText("High Pass Threshold", ["20000", "45000", "70000", "80000"])
        self.low_pass = ComboBoxWithText("Low Pass Threshold", ["500000"])
        super().__init__()

class DelayWidgets(WindowWidgets):
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.time = LineEditWithText("Delay Time")
        super().__init__()
        
class ItemWindow(QtWidgets.QFrame):
    def __init__(self) -> None:
        """Initialize the bloch spheres window.
        """
        super().__init__()
        self.setMaximumWidth(400)
        self.main_layout = QtWidgets.QVBoxLayout()
        self.widgets: Optional[Union[DelayWidgets, ChirpWidgets, LoopWidgets]] = None
        self.setObjectName("BlochWindow")
        self.setLayout(self.main_layout)
        self.prev_action = None

    def reset_window(self, action: "ContainerLabel"):
        if self.widgets is not None and self.prev_action is not None:
            for key, value in self.widgets.__dict__.items():
                if isinstance(value, (LineEditWithText, ComboBoxWithText)):
                    try:
                        self.prev_action.values.__dict__[key] = type(self.prev_action.values.__dict__[key])(value.getInnerText())
                    except ValueError:
                        pass
        self.prev_action = action
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        self.widgets = None
        self.main_layout.update()
        self.main_layout.activate()
        QtWidgets.QApplication.processEvents()
        if action.label_name == Actions.Loop.value:
            self.widgets = LoopWidgets()
        elif action.label_name == Actions.Chirp.value:
            self.widgets = ChirpWidgets()
        elif action.label_name == Actions.Delay.value:
            self.widgets = DelayWidgets()
        
        for key, value in self.widgets.__dict__.items():
            if isinstance(value, (LineEditWithText, ComboBoxWithText)):
                self.main_layout.addWidget(value, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
                value.setInnerText(str(type(self.prev_action.values.__dict__[key])(action.values.__dict__[key])))
                
class ActionWindowWidgets(WindowWidgets):
    """The widgets for the rx info window.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.loop = DraggableLabel()
        self.delay = DraggableLabel()
        self.chirp = DraggableLabel()
        self.send_to_device = QtWidgets.QPushButton()
        super().__init__()

class ActionWindow(QtWidgets.QFrame):
    def __init__(self) -> None:
        """Initialize the bloch spheres window.
        """
        super().__init__()
        self.setMaximumWidth(400)
        self.main_layout = QtWidgets.QVBoxLayout()
        self.widgets: ActionWindowWidgets = ActionWindowWidgets()
        self.setObjectName("BlochWindow")
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.widgets.loop, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.widgets.delay, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.widgets.chirp, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.widgets.loop.setText(Actions.Loop.value)
        self.widgets.delay.setText(Actions.Delay.value)
        self.widgets.chirp.setText(Actions.Chirp.value)
        self.main_layout.addWidget(self.widgets.send_to_device, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.widgets.send_to_device.setText("Send Sequence To Device")

class SignalWindowWidgets():
    """The widgets for the rx info window.
    """
    def __init__(self, item_window) -> None:
        """Initialize each widget within the window.
        """
        self.drop_area = DropArea(item_window, True)

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

class SignalWindow(QtWidgets.QFrame):
    """The frame for displaying the bloch spheres.
    """
    def __init__(self) -> None:
        """Initialize the bloch spheres window.
        """
        super().__init__()
        self.main_layout = QtWidgets.QHBoxLayout()
        self.item_window = ItemWindow()
        self.widgets: SignalWindowWidgets = SignalWindowWidgets(self.item_window)
        self.setObjectName("BlochWindow")
        self.setLayout(self.main_layout)
        self.drop_layout = QtWidgets.QHBoxLayout()
        self.action_window = ActionWindow()
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self.action_window, "Actions")
        self.tabs.addTab(self.item_window, "Items")
        self.main_layout.addLayout(self.drop_layout)
        self.main_layout.addWidget(self.tabs)
        
        self.drop_layout.addWidget(
            self.widgets.drop_area
        )
        self.first_action: Optional[ContainerLabel] = None

class LoopValues():
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.sub_sequence = None
        self.num_repetitions: int = 0
        self.repetition_time_s: float = 0.0

class ChirpValues():
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.start_frequency_Hz: float = 58.0e9
        self.end_frequency_Hz: float = 63.5e9
        self.sample_rate_Hz: int = 2e6
        self.num_samples: int = 64
        self.rx_mask: int = 7
        self.tx_mask: int = 1
        self.tx_power_level: int = 31
        self.lp_cutoff_Hz: int = 80000
        self.hp_cutoff_Hz: int = 500000
        self.if_gain_dB: int = 23


class DelayValues():
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.time_s: int = 1000

class ContainerLabel(QtWidgets.QWidget):
    def __init__(self, item_window: ItemWindow, label_name: str):
        super().__init__()
        self.label_name = label_name
        self.setAcceptDrops(True)
        self.setMaximumHeight(200)
        self.drop_layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.drop_layout)
        
        self.close_button = QtWidgets.QPushButton("X", self)
        self.close_button.setFixedSize(20, 20)
        self.close_button.move(self.width() - 25, 5)
        self.close_button.clicked.connect(self.remove_widget)
        
        if label_name == Actions.Loop.value:
            self.dropEvent = types.MethodType(DropArea.dropEvent, self)
            self.dragEnterEvent = types.MethodType(DropArea.dragEnterEvent, self)
            self.values = LoopValues() 
        elif label_name == Actions.Delay.value:
            self.values = DelayValues()
        else:
            self.values = ChirpValues()
        self.call_up_stack = types.MethodType(DropArea.call_up_stack, self)
        self.update_width = types.MethodType(DropArea.update_width, self)
        self.drop_parent: Union[DropArea, ContainerLabel] = None
        self.drop_children: Union[DropArea, ContainerLabel] = None
        self.setStyleSheet(global_budget_window_style)
        self.first_drop = False
        self.item_window = item_window
        self.connected_drops: DropArea = []
        self.action_child: Optional[ContainerLabel] = None
        self.action_previous = None
        self.action_next = None

    def resizeEvent(self, event):
        # Move the button to top-right corner
        self.close_button.move(self.width() - 25, 5)
        # Call the base class implementation
        super().resizeEvent(event)

    def paintEvent(self, Event):
        painter = QPainter(self)
        painter.drawText(10, 20, self.label_name)  # x, y from top-left
        pen = QPen(QColor(int(border_color[1:3], 16), int(border_color[3:5], 16), int(border_color[5:7], 16)), 3)
        painter.setPen(pen)

        painter.drawRect(
            0, 
            0, 
            self.width(), 
            self.height()
        )

    def remove_widget(self):
        for drop in self.connected_drops:
            self.parent().drop_layout.removeWidget(drop)
            drop.close()
        self.parent().drop_layout.removeWidget(self)
        self.close()
        if isinstance(self.parent(), SignalWindow):
            parent: SignalWindow = self.parent()
            if parent.drop_layout.count() == 0:
                new_init_drop_area = DropArea(self.item_window, first_drop=True)
                parent.drop_layout.addWidget(new_init_drop_area)
                parent.widgets.drop_area = new_init_drop_area
        self.call_up_stack()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.item_window.reset_window(self)
                
class DropArea(QtWidgets.QWidget):
    def __init__(self, item_window: ItemWindow, first_drop = False, right_referential = False):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumSize(100, 100)
        self.setMaximumHeight(200)
        self.drop_layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.drop_layout)
        self.setStyleSheet(drop_area_style)
        self.layout_location = 0
        self.first_drop = first_drop
        self.right_referential = right_referential
        self.item_window = item_window
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(int(hover_color[1:3], 16), int(hover_color[3:5], 16), int(hover_color[5:7], 16)))

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-qwidget"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def call_up_stack(self):
        if hasattr(self.parent(), "call_up_stack"):
            self.parent().call_up_stack()
        else:
            self.update_width(self.width())
    
    def update_width(self, maximum_width: int):
        if self.children():
            children = 0
            for drop_child in self.children():
                if isinstance(drop_child, (DropArea, ContainerLabel)):
                    children += drop_child.update_width(maximum_width)
        else:
            children = 1
        self.setMinimumWidth(50 * children)
        return children    
            

    def dropEvent(self, event: QDropEvent):
        event_source: DraggableLabel = event.source() 
        new_label = ContainerLabel(self.item_window, event_source.text())
        new_label.drop_parent = self
        new_drop_area_left = DropArea(self.item_window)
        new_drop_area_left.setMaximumWidth(50)
        new_drop_area_left.setMaximumHeight(50)

        new_drop_area_right = DropArea(self.item_window, right_referential=True)
        new_drop_area_right.setMaximumWidth(50)
        new_drop_area_right.setMaximumHeight(50)

        
        new_drop_area_left.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,
                        QtWidgets.QSizePolicy.Policy.Fixed)
        new_drop_area_right.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,
                        QtWidgets.QSizePolicy.Policy.Fixed)
        new_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,
                                QtWidgets.QSizePolicy.Policy.Fixed)
        
        new_label.connected_drops.extend([new_drop_area_left, new_drop_area_right])
        
        if isinstance(self, ContainerLabel):
            layout = self.drop_layout
        else:
            layout = self.parent().drop_layout

        if self.first_drop:
            self.parent().first_action = new_label
            layout.removeWidget(self)
            self.setParent(None)
            self.deleteLater()

        if isinstance(self, DropArea) and not self.first_drop:
            new_drop_area_left.layout_location = self.layout_location + self.right_referential
            new_drop_area_right.layout_location = self.layout_location + 2 + self.right_referential
            previous_item = self.parent().drop_layout.itemAt(self.layout_location - (1 + (not self.right_referential)))
            if previous_item is not None:
                self.previous = previous_item.widget()
            next_item = self.parent().drop_layout.itemAt(self.layout_location + 1 + self.right_referential)
            if next_item is not None:
                self.next = next_item.widget()
            layout.insertWidget(self.layout_location+self.right_referential, new_drop_area_right)
            layout.insertWidget(self.layout_location+self.right_referential, new_label)
            layout.insertWidget(self.layout_location+self.right_referential, new_drop_area_left)
        else:
            new_drop_area_left.layout_location = 0
            new_drop_area_right.layout_location = 2
            self.action_child = new_label
            layout.addWidget(new_drop_area_left)
            layout.addWidget(new_label)
            layout.addWidget(new_drop_area_right)
        
        new_label.call_up_stack()
        
        event.acceptProposedAction()
        