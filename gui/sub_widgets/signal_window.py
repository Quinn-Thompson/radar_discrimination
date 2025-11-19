"""The window for displaying the rx information."""
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as Navigation
from matplotlib.figure import Figure
from PyQt6 import QtWidgets, QtCore
from typing import Generator, Union, Optional, List
from gui.helpers import hover_color, DraggableLabel, global_budget_window_style, drop_area_style, border_color, \
LineEditWithText, ComboBoxWithText, WindowWidgets, small_item_window_style, background_color, clicked_color
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QColor, QPen
from PyQt6.QtCore import Qt
import types
from enum import Enum
from functools import partial

class Actions(Enum):
    Loop = "Loop"
    Chirp = "Chirp"
    Delay = "Delay"
    Simple_Config = "Simple_Config"

class SimpleConfigWidgets(WindowWidgets):
    def __init__(self) -> None:
        """Initialize each widget when changing a chirp.
        """
        # WARNING! These are named in consistency with ChirpValues, do not change them!
        self.frame_repetition_time_s = LineEditWithText("Frame Repetition")
        self.chirp_repetition_time_s = LineEditWithText("Chirp Repetition")
        self.num_chirps = LineEditWithText("Number of Chirps")
        self.start_frequency_Hz = LineEditWithText("Start Frequency")
        self.end_frequency_Hz = LineEditWithText("End Frequency")
        self.num_samples = ComboBoxWithText("High Pass Threshold", ["2", "4", "8", "16", "32", "64", "128", "256", "512", "1024"])
        self.sample_rate_Hz = LineEditWithText("Sample Rate")
        self.tx_power_level = LineEditWithText("Transmission Power Level")
        self.if_gain_dB = LineEditWithText("IF Gain")
        self.hp_cutoff_Hz = ComboBoxWithText("High Pass Threshold", ["20000", "45000", "70000", "80000"])
        self.lp_cutoff_Hz = ComboBoxWithText("Low Pass Threshold", ["500000"])
        super().__init__()

class LoopWidgets(WindowWidgets):
    def __init__(self) -> None:
        """Initialize each widget for when changing a loop.
        """
        self.num_repetitions = LineEditWithText("Number Of Repetitions")
        self.repetition_time_s = LineEditWithText("Repetition Time")
        super().__init__()

class ChirpWidgets(WindowWidgets):
    def __init__(self) -> None:
        """Initialize each widget when changing a chirp.
        """
        # WARNING! These are named in consistency with ChirpValues, do not change them!
        self.start_frequency_Hz = LineEditWithText("Start Frequency")
        self.end_frequency_Hz = LineEditWithText("End Frequency")
        self.num_samples = ComboBoxWithText("High Pass Threshold", ["2", "4", "8", "16", "32", "64", "128", "256", "512", "1024"])
        self.sample_rate_Hz = LineEditWithText("Sample Rate")
        self.tx_power_level = LineEditWithText("Transmission Power Level")
        self.if_gain_dB = LineEditWithText("IF Gain")
        self.hp_cutoff_Hz = ComboBoxWithText("High Pass Threshold", ["20000", "45000", "70000", "80000"])
        self.lp_cutoff_Hz = ComboBoxWithText("Low Pass Threshold", ["500000"])
        super().__init__()

class DelayWidgets(WindowWidgets):
    def __init__(self) -> None:
        """Initialize each widget when changing a delay.
        """
        self.time_s = LineEditWithText("Delay Time")
        super().__init__()
        
class ItemWindow(QtWidgets.QFrame):
    def __init__(self, signal_window: "SignalWindow") -> None:
        """Initialize the bloch spheres window.
        """
        super().__init__()
        self.setMaximumWidth(400)
        self.main_layout = QtWidgets.QVBoxLayout()
        self.widgets: Optional[Union[DelayWidgets, ChirpWidgets, LoopWidgets, SimpleConfigWidgets]] = None
        self.setObjectName("BlochWindow")
        self.setLayout(self.main_layout)
        self.prev_action = None
        self.signal_window = signal_window

    def reset_window(self, action: "ContainerLabel"):
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
        elif action.label_name == Actions.Simple_Config.value:
            self.widgets = SimpleConfigWidgets()
        
        for key, value in self.widgets.__dict__.items():
            if isinstance(value, (LineEditWithText, ComboBoxWithText)):
                self.main_layout.addWidget(value, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
                value.setInnerText(str(type(action.values.__dict__[key])(action.values.__dict__[key])))
                if isinstance(value, LineEditWithText):
                    value.line_edit.editingFinished.connect(partial(self.setup_passback, key, value))
                else:
                    value.combo_box.currentTextChanged.connect(partial(self.setup_passback, key, value))
        self.prev_action = action
    
    def setup_passback(self, name: str, editable_widget: Union[LineEditWithText, ComboBoxWithText]):
        try:
            self.prev_action.values.__dict__[name] = type(self.prev_action.values.__dict__[name])(editable_widget.getInnerText())
        except ValueError:
            pass
    
class ActionWindowWidgets(WindowWidgets):
    """The widgets for the rx info window.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.loop = DraggableLabel()
        self.delay = DraggableLabel()
        self.chirp = DraggableLabel()
        self.simple_config = DraggableLabel()
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
        self.main_layout.addWidget(self.widgets.simple_config, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.widgets.loop.setText(Actions.Loop.value)
        self.widgets.delay.setText(Actions.Delay.value)
        self.widgets.chirp.setText(Actions.Chirp.value)
        self.widgets.simple_config.setText(Actions.Simple_Config.value)
        self.main_layout.addWidget(self.widgets.send_to_device, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.widgets.send_to_device.setText("Send Sequence To Device")


class SignalWindowWidgets():
    """The widgets for the rx info window.
    """
    def __init__(self, item_window) -> None:
        """Initialize each widget within the window.
        """
        self.figure = Figure(figsize=(14, 8), constrained_layout=True, edgecolor='white')
        self.graph_widgets: FigureCanvas = FigureCanvas(self.figure)
        self.drop_area = DropArea(item_window, layer=0, first_drop=True)

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
        self.main_layout = QtWidgets.QVBoxLayout()
        self.item_window = ItemWindow(self)
        self.widgets: SignalWindowWidgets = SignalWindowWidgets(self.item_window)
        self.setObjectName("BlochWindow")
        self.setLayout(self.main_layout)
        self.drop_layout = QtWidgets.QHBoxLayout()
        self.widgets.drop_area.setMinimumSize(200, 200)
        self.action_window = ActionWindow()
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setMaximumHeight(300)
        self.action_child: Optional[ContainerLabel] = None
        self.toolbar = Navigation(self.widgets.graph_widgets, self)

        self.tabs.addTab(self.action_window, "Actions")
        self.tabs.addTab(self.item_window, "Items")
        self.matplotlib_layout = QtWidgets.QVBoxLayout()

        self.matplotlib_layout.addWidget(self.widgets.graph_widgets, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.matplotlib_layout.addWidget(self.toolbar)

        self.widgets.graph_widgets.setMaximumHeight(400)
        self.drop_layout.addWidget(
            self.widgets.drop_area
        )

        self.main_layout.addLayout(self.drop_layout)
        self.main_layout.addWidget(self.tabs)
        self.main_layout.addLayout(self.matplotlib_layout)


class SimpleConfigValues():
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        # WARNING! These are named in consistency with FmcwSequenceChirp, do not change them!
        self.frame_repetition_time_s: float = 100.325e-3
        self.chirp_repetition_time_s: float = 500e-6
        self.num_chirps: int = 16
        self.tdm_mimo: bool = False
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


class LoopValues():
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.sub_sequence = None
        self.num_repetitions: int = 0
        self.repetition_time_s: float = 0.1

class ChirpValues():
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        # WARNING! These are named in consistency with FmcwSequenceChirp, do not change them!
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
    
    def setup_simple(self, simple_config: SimpleConfigValues):
        self.start_frequency_Hz = simple_config.start_frequency_Hz
        self.end_frequency_Hz = simple_config.end_frequency_Hz
        self.sample_rate_Hz = simple_config.sample_rate_Hz
        self.num_samples = simple_config.num_samples
        self.rx_mask = simple_config.rx_mask
        self.tx_mask = simple_config.tx_mask
        self.tx_power_level = simple_config.tx_power_level
        self.lp_cutoff_Hz = simple_config.lp_cutoff_Hz
        self.hp_cutoff_Hz = simple_config.hp_cutoff_Hz
        self.if_gain_dB = simple_config.if_gain_dB

class DelayValues():
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.time_s: float = 10.0e-6


class ContainerLabel(QtWidgets.QWidget):
    def __init__(self, item_window: ItemWindow, label_name: str, layer: int):
        super().__init__()
        self.installEventFilter(self)
        self.setMouseTracking(True)
        self.layer = layer

        self.label_name = label_name
        self.setAcceptDrops(True)
        self.setMaximumHeight(200)
        self.setMaximumHeight(100)
        self.drop_layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.drop_layout)
        
        self.close_button = QtWidgets.QPushButton("X", self)
        self.close_button.setFixedSize(20, 20)
        self.close_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,
                        QtWidgets.QSizePolicy.Policy.Fixed)
        self.close_button.font().setPointSize(6)
        self.close_button.setStyleSheet(
            small_item_window_style
        )
        self.close_button.move(self.width() - 25, 5)
        self.close_button.clicked.connect(self.remove_widget)
        
        if label_name == Actions.Loop.value:
            self.dropEvent = types.MethodType(DropArea.dropEvent, self)
            self.dragEnterEvent = types.MethodType(DropArea.dragEnterEvent, self)
            self.values = LoopValues() 
        elif label_name == Actions.Delay.value:
            self.values = DelayValues()
        elif label_name == Actions.Simple_Config.value:
            self.values = SimpleConfigValues()
        else:
            self.values = ChirpValues()
        self.call_up_stack = types.MethodType(DropArea.call_up_stack, self)
        self.update_width = types.MethodType(DropArea.update_width, self)
        self.action_parent: Union[DropArea, ContainerLabel] = None
        self.setStyleSheet(global_budget_window_style)
        self.first_drop = False
        self.item_window = item_window
        self.connected_drops: DropArea = []
        self.action_previous: Optional[ContainerLabel] = None
        self.action_child: Optional[ContainerLabel] = None
        self.action_next: Optional[ContainerLabel] = None
        self.hovering = False
        self.clicked = False

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent):
        if event.type() == QtCore.QEvent.Type.MouseMove:
            pos = event.position().toPoint()
            # Hover only if mouse is over main widget, not any child
            if self.rect().contains(pos) and self.childAt(pos) is None:
                if not self.hovering:
                    self.hovering = True
                    self.update()
            else:
                if self.hovering:
                    self.hovering = False
                    self.update()
        elif event.type() in (QtCore.QEvent.Type.Leave, QtCore.QEvent.Type.HoverLeave):
            if self.hovering:
                self.hovering = False
                self.update()
        return super().eventFilter(obj, event)
        
    def resizeEvent(self, event):
        # Move the button to top-right corner
        self.close_button.move(self.width() - 35, 5)
        # Call the base class implementation
        super().resizeEvent(event)

    def paintEvent(self, Event):
        painter = QPainter(self)

        hover_or_not = hover_color if self.hovering else background_color
        clicked_or_not = clicked_color if self.clicked else hover_or_not
        
        painter.fillRect(self.rect(), QColor(int(clicked_or_not[1:3], 16), int(clicked_or_not[3:5], 16), int(clicked_or_not[5:7], 16)))

        pen = QPen(QColor(int(border_color[1:3], 16), int(border_color[3:5], 16), int(border_color[5:7], 16)), 3)
        painter.setPen(pen)
        painter.drawRect(
            0, 
            0, 
            self.width(), 
            self.height()
        )
        
        painter.drawText(10, 20, self.label_name)  # x, y from top-left

    def remove_widget(self):
        parent: Union[ContainerLabel, SignalWindow] = self.parent()
        if parent.action_child == self:
            if self.action_next:
                parent.action_child = self.action_next
            else:
                parent.action_child = None
                
        if self.action_next is not None:
            if self.action_previous is not None:
                self.action_previous.action_next = self.action_next
                self.action_next.action_previous = self.action_previous
            else:
                self.action_next.action_previous = None
        elif self.action_previous is not None:
            self.action_previous.action_next = None
            
            
        for drop in self.connected_drops:
            parent.drop_layout.removeWidget(drop)
            drop.close()
        parent.drop_layout.removeWidget(self)
        self.close()
        if isinstance(parent, SignalWindow):
            parent: SignalWindow = parent
            if parent.drop_layout.count() == 0:
                new_init_drop_area = DropArea(self.item_window, layer=0, first_drop=True)
                parent.drop_layout.addWidget(new_init_drop_area)
                parent.widgets.drop_area = new_init_drop_area
        self.call_up_stack()

    def mousePressEvent(self, event):
        self.clicked = True
        self.update()
        if event.button() == Qt.MouseButton.LeftButton:
            self.item_window.reset_window(self)
            self.item_window.signal_window.tabs.setCurrentIndex(1)
    
    def mouseReleaseEvent(self, event):
        self.clicked = False
        self.update()        
        
class DropArea(QtWidgets.QWidget):
    def __init__(self, item_window: ItemWindow, layer: int, first_drop = False, right_referential = False):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumSize(1, 1)
        self.drop_layout = QtWidgets.QHBoxLayout()
        if not first_drop:
            self.drop_layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        self.setLayout(self.drop_layout)
        self.setStyleSheet(drop_area_style)
        self.layout_location = 0
        self.first_drop = first_drop
        self.right_referential = right_referential
        self.item_window = item_window
        self.action_parent: Optional[ContainerLabel] = None
        self.action_child: Optional[ContainerLabel] = None
        self.action_next: Optional[ContainerLabel] = None
        self.action_previous: Optional[ContainerLabel] = None
        self.layer = layer
  
    def minimumSizeHint(self):
        return QtCore.QSize(10, 10)

    def sizeHint(self):
        return QtCore.QSize(10, 10)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(int(hover_color[1:3], 16), int(hover_color[3:5], 16), int(hover_color[5:7], 16)))

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-qwidget") and self.action_child is None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def call_up_stack(self):
        if hasattr(self.parent(), "call_up_stack"):
            self.parent().call_up_stack()
        else:
            self.update_width(self.width())
    
    def update_width(self, maximum_width: int):
        width = 0
        if isinstance(self, ContainerLabel) and self.action_child is not None:
            current_action = self.action_child
            while current_action is not None:
                width += current_action.update_width(maximum_width) + 20
                current_action = current_action.action_next
            self.setMinimumWidth(width + 10)
        else:
            width = 75
        return width    
            

    def dropEvent(self, event: QDropEvent):
        if self.action_child:
            return
        parent: Union[ContainerLabel, SignalWindow] = self.parent()
        event_source: DraggableLabel = event.source()
        label_name = event_source.text()
        if self.layer == 0 and (label_name != Actions.Simple_Config.value and label_name != Actions.Loop.value):
            return
        elif self.layer == 1 and label_name == Actions.Chirp.value:
            return
        elif self.layer == 2 and label_name != Actions.Chirp.value:
            return
         
        new_label = ContainerLabel(self.item_window, label_name, layer=self.layer + 1)
        if self.layer != 0:
            new_drop_area_left = DropArea(self.item_window, layer=self.layer)
            new_drop_area_left.setFixedSize(10, 10)


            new_drop_area_right = DropArea(self.item_window, layer=self.layer, right_referential=True)
            new_drop_area_right.setFixedSize(10, 10)

            
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
            layout = parent.drop_layout

        if self.first_drop:
            parent.action_child = new_label
            layout.removeWidget(self)
            self.setParent(None)
            self.deleteLater()

        if isinstance(self, DropArea) and not self.first_drop:
            new_drop_area_left.layout_location = self.layout_location + self.right_referential
            new_drop_area_right.layout_location = self.layout_location + 2 + self.right_referential
            previous_item = parent.drop_layout.itemAt(self.layout_location - (1 + (not self.right_referential)))
            if previous_item is not None:
                new_label.action_previous = previous_item.widget()
                new_label.action_previous.action_next = new_label
            next_item = parent.drop_layout.itemAt(self.layout_location + 1 + self.right_referential)
            if next_item is not None:
                new_label.action_next = next_item.widget()
                new_label.action_next.action_previous = new_label
                if self.action_next == parent.action_child:
                    parent.action_child = new_label
            layout.insertWidget(self.layout_location+self.right_referential, new_drop_area_right)
            layout.insertWidget(self.layout_location+self.right_referential, new_label)
            layout.insertWidget(self.layout_location+self.right_referential, new_drop_area_left)
        else:
            new_label.action_parent = parent
            self.action_child = new_label
            if self.layer != 0:
                new_drop_area_left.layout_location = 0
                new_drop_area_right.layout_location = 2
                layout.addWidget(new_drop_area_left, 0, Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(new_label)
            if self.layer != 0:
                layout.addWidget(new_drop_area_right, 0, Qt.AlignmentFlag.AlignCenter)
        
        new_label.call_up_stack()
        
        event.acceptProposedAction()
        