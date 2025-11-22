"""The window for displaying the rx information live."""
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as Navigation
from matplotlib.figure import Figure
from PyQt6 import QtWidgets, QtCore
from typing import Generator, Union, Optional, Dict, List, Any
from gui.helpers import hover_color, DraggableLabel, global_budget_window_style, drop_area_style, border_color, \
LineEditWithText, ComboBoxWithText, WindowWidgets, small_item_window_style, background_color, clicked_color
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QColor, QPen
from PyQt6.QtCore import Qt
import types
from enum import Enum
from functools import partial

_SUB_ELEMENT = "sub_element"
_NEXT_ELEMENT = "next_element"
_ELEMENT_NAME = "type"
_ELEMENT_VALUES = "element_values"
_SEQUENCE = "sequence"

class Actions(Enum):
    """Simple Actions for creating a sequence."""
    Loop = "loop"
    Chirp = "chirp"
    Delay = "delay"
    Simple_Config = "Simple_Config"

class SimpleConfigWidgets(WindowWidgets):
    def __init__(self) -> None:
        """Initialize each widget when changing a chirp."""
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
        """Initialize each widget for when changing a loop."""
        self.num_repetitions = LineEditWithText("Number Of Repetitions")
        self.repetition_time_s = LineEditWithText("Repetition Time")
        super().__init__()

class ChirpWidgets(WindowWidgets):
    def __init__(self) -> None:
        """Initialize each widget when changing a chirp."""
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
        """Initialize each widget when changing a delay."""
        self.time_s = LineEditWithText("Delay Time")
        super().__init__()
        
class ItemWindow(QtWidgets.QFrame):
    def __init__(self, signal_window: "SignalWindow") -> None:
        """Initialize the window for displaying the values for an action."""
        super().__init__()
        self.setMaximumWidth(400)
        self.main_layout = QtWidgets.QVBoxLayout()
        self.widgets: Optional[Union[DelayWidgets, ChirpWidgets, LoopWidgets, SimpleConfigWidgets]] = None
        self.setObjectName("BlochWindow")
        self.setLayout(self.main_layout)
        self.prev_action = None
        self.signal_window = signal_window

    def reset_window(self, action: "ContainerLabel") -> None:
        """Reset the window when another item is clicked on.

        Args:
            action: The action item that has been clicked on.
        """
        
        # delete the current widgets for displaying values
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        # update so that is displayed
        self.widgets = None
        self.main_layout.update()
        self.main_layout.activate()
        QtWidgets.QApplication.processEvents()
        
        # set the current widgets object to be something different
        if action.label_name == Actions.Loop.value:
            self.widgets = LoopWidgets()
        elif action.label_name == Actions.Chirp.value:
            self.widgets = ChirpWidgets()
        elif action.label_name == Actions.Delay.value:
            self.widgets = DelayWidgets()
        elif action.label_name == Actions.Simple_Config.value:
            self.widgets = SimpleConfigWidgets()
        
        # setup the text values and then define the widget items to change the backend values when edited.
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
    """The widgets for the draggable actions within window."""
    
    def __init__(self) -> None:
        """Initialize each widget within the window."""
        self.loop = DraggableLabel()
        self.delay = DraggableLabel()
        self.chirp = DraggableLabel()
        self.simple_config = DraggableLabel()
        self.send_to_device = QtWidgets.QPushButton()
        super().__init__()

class ActionWindow(QtWidgets.QFrame):
    def __init__(self) -> None:
        """Initialize the window for the different draggable action items."""
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


class SignalWindowWidgets(WindowWidgets):
    """The widgets for the entirely of the sequence info window."""
    
    def __init__(self, item_window: ItemWindow) -> None:
        """Initialize each widget within the window."""
        self.figure = Figure(figsize=(14, 8), constrained_layout=True, edgecolor='white')
        self.graph_widgets: FigureCanvas = FigureCanvas(self.figure)
        self.drop_area = DropArea(item_window, layer=0, first_drop=True)

class SignalWindow(QtWidgets.QFrame):
    """The frame for the sequence info."""
    
    def __init__(self) -> None:
        """Initialize the sequence info window."""
        
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
        self.sub_element: Optional[ContainerLabel] = None
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
        
    def get_json_dictionary(self) -> Dict[str, str]:
        """Acquire the sequences from the action child for saving to json.

        Returns:
            All the information for recreating a sequence.
        """
        my_contents_dict = {}
        if self.sub_element is not None:
            my_contents_dict[_SEQUENCE] = self.sub_element.get_json_dictionary()
        return my_contents_dict
            
    def set_json_dictionary(self, json_dictionary: Dict[str, str]):
        """Setup the sequence based on the json values.
        
        Args:
            json_dictionary: The dictionary of information important to recreating the sequence.
        """
        setup_widgets = False

        if _SEQUENCE in json_dictionary and self.sub_element is not None:
            # have the widget delete itself
            self.sub_element.remove_widget()
            
        # if the dictionary has a sequence element and there isn't one currently in the gui
        if _SEQUENCE in json_dictionary and self.sub_element is None:
            # delete the drop area from the window
            self.drop_layout.removeWidget(self.widgets.drop_area)
            self.widgets.drop_area.setParent(None)
            self.widgets.drop_area.deleteLater()
            setup_widgets = True

        if setup_widgets:
            first_sequence = json_dictionary[_SEQUENCE][-1]
            self.sub_element = ContainerLabel(self.item_window, first_sequence[_ELEMENT_NAME], 0)
            self.sub_element.values.set_json_dictionary(first_sequence)
            self.drop_layout.addWidget(self.sub_element)
            self.sub_element.set_json_dictionary(first_sequence[_SEQUENCE])


class SequenceValues():
    """The values each sequence."""
    def get_json_dictionary(self) -> Dict[str, str]:
        """Get the values contained within the sequence.

        Returns:
            The different configurations of each action.
        """
        return {k: v for k, v in self.__dict__.items() if isinstance(v, (int, float, bool))}

    def set_json_dictionary(self, json_dictionary: Dict[str, str]):
        """Setup the values for the sequence element.

        Args:
            json_dictionary: The remaining key/values to set the sequence element values.
        """
        for key in self.__dict__:
            try:
                self.__dict__[key] = type(self.__dict__[key])(json_dictionary[key])
            except KeyError:
                pass

class SimpleConfigValues(SequenceValues):
    def __init__(self) -> None:
        """Recreation of the C like sequence object, used to save values for the gui front end."""
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
        
class LoopValues(SequenceValues):
    """Back end loop sequence values."""
    def __init__(self) -> None:
        """Recreation of the C like sequence object, used to save values for the gui front end."""
        self.sub_sequence: Optional[Any] = None
        self.num_repetitions: int = 0
        self.repetition_time_s: float = 0.1

class ChirpValues(SequenceValues):
    """Back end chirp sequence values."""
    def __init__(self) -> None:
        """Recreation of the C like sequence object, used to save values for the gui front end."""
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
        """Setup the values based on values provided by the simple config.

        Args:
            simple_config: A simple configuration to use for a chirp sequence.
        """
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

class DelayValues(SequenceValues):
    """Back end delay sequence values."""
    def __init__(self) -> None:
        """Recreation of the C like sequence object, used to save values for the gui front end."""
        # WARNING! These are named in consistency with FmcwSequenceDelay, do not change them!
        self.time_s: float = 10.0e-6

class ContainerLabel(QtWidgets.QWidget):
    """The container for one sequence element."""
    def __init__(self, item_window: ItemWindow, label_name: str, layer: int):
        """Initialize the container and setup it's close button alongside it's connection to the backend values.

        Args:
            item_window: The window to edit the values from.
            label_name: What this container will use for values.
            layer: which layer in the sequence the container lives on.
        """
        super().__init__()

        self.layer = layer

        self.label_name = label_name
        self.setup_values(label_name)
        self.setAcceptDrops(True)
        self.setFixedHeight(200 - (layer*50))
        self.setMinimumWidth(75)
        self.drop_layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.drop_layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.close_button = QtWidgets.QPushButton("X", self)
        self.close_button.setFixedSize(20, 20)
        self.drop_layout.setContentsMargins(5, 20, 5, 5)
        self.close_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.close_button.font().setPointSize(6)
        self.close_button.setStyleSheet(
            small_item_window_style
        )
        self.close_button.setMouseTracking(True)
        self.close_button.installEventFilter(self)
        self.close_button.move(self.width() - 25, 5)
        self.close_button.clicked.connect(self.remove_widget)
        
        self.installEventFilter(self)
        self.setMouseTracking(True)
        self.button_hover = False
        self.setStyleSheet(global_budget_window_style)
        self.first_drop = False
        self.item_window = item_window
        self.connected_drops: List[DropArea] = []
        self.action_previous: Optional[ContainerLabel] = None
        self.sub_element: Optional[ContainerLabel] = None
        self.next_element: Optional[ContainerLabel] = None
        self.hovering = False
        self.clicked = False

    def setup_values(self, label_name: str):
        """Setup which values are used for creating a sequence.

        Args:
            label_name: The string literal for the type of sequence element.
        """
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

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent):
        """Watch the events to see if there is a hovering event.
        
        Much better than a mouse over event call because that takes a literal position
        which means when hovered (even with an item covered it) the event will happen.

        Args:
            object: The object pertaining to the event.
            event: The event passing through the filter.

        Returns:
            The original function call.
        """
        # if not self.isVisible():
        #     return super().eventFilter(object, event)
        
        if object == self.close_button:
            if event.type() == QtCore.QEvent.Type.HoverLeave:
                if self.button_hover:
                    self.button_hover = False
                    self.close_button.setStyleSheet(f"background-color: {background_color}; border-radius: 0px;")
                    self.update()
        # for each mouse movement event (can be somewhat taxing)
        if event.type() == QtCore.QEvent.Type.MouseMove:
            if object == self.close_button:

                if self.hovering:
                    self.hovering = False
                
                if not self.button_hover:
                    self.button_hover = True
                    self.close_button.setStyleSheet(f"background-color: {hover_color}; border-radius: 0px;")

            else:

                event_position = event.position().toPoint()
                # hover only if the mouse is over the main widget
                if self.rect().contains(event_position) and self.childAt(event_position) is None:
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
        return super().eventFilter(object, event)
        
    def resizeEvent(self, event):
        """When the widget is resized.

        Args:
            event: The resize event object.
        """
        # top right corner
        self.close_button.move(self.width() - 35, 5)
        super().resizeEvent(event)

    def paintEvent(self, _):
        """When the widget is drawn to the screen."""
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

    def remove_widget(self) -> None:
        """Remove the widget and connect nearby widgets to one another."""
        
        # the first child of the parent needs to changed if it is deleted
        parent: Union[ContainerLabel, SignalWindow] = self.parent()
        if parent.sub_element == self:
            if self.next_element:
                parent.sub_element = self.next_element
            else:
                parent.sub_element = None
        
        # connect nearby widgets to one another
        if self.next_element is not None:
            if self.action_previous is not None:
                self.action_previous.next_element = self.next_element
                self.next_element.action_previous = self.action_previous
            else:
                self.next_element.action_previous = None
        elif self.action_previous is not None:
            self.action_previous.next_element = None
            
        # remove the drop areas next to this widget
        for drop in self.connected_drops:
            parent.drop_layout.removeWidget(drop)
            drop.close()
        parent.drop_layout.removeWidget(self)
        self.close()
        
        # if the parent is the signal window, we just recreate the original drop window
        if isinstance(parent, SignalWindow):
            parent: SignalWindow = parent
            if parent.drop_layout.count() == 0:
                new_init_drop_area = DropArea(self.item_window, layer=0, first_drop=True)
                parent.drop_layout.addWidget(new_init_drop_area)
                parent.widgets.drop_area = new_init_drop_area

    def mousePressEvent(self, event):
        """When the mouse is pressed on the widget.

        Args:
            event: The mouse clicking event.
        """
        self.clicked = True
        self.update()
        if event.button() == Qt.MouseButton.LeftButton:
            self.item_window.reset_window(self)
            self.item_window.signal_window.tabs.setCurrentIndex(1)
    
    def mouseReleaseEvent(self, _):
        """When the mouse is released from clicking on the widget."""
        self.clicked = False
        self.update()
        
    def get_json_dictionary(self) -> Dict[str, str]:
        """Recurse through every element in the sequence and get the pertinent info.

        Returns:
            A key value pair for recreating the sequence.
        """
        my_contents: List[Dict[str, str]] = []
        current_sequence = self

        while current_sequence is not None:
            my_contents.append({})
            my_contents[-1].update(**current_sequence.values.get_json_dictionary())
            if current_sequence.sub_element is not None:
                my_contents[-1][_SEQUENCE] = current_sequence.sub_element.get_json_dictionary()
            my_contents[-1][_ELEMENT_NAME] = current_sequence.label_name
            current_sequence = current_sequence.next_element
        return my_contents
        
    def set_json_dictionary(
        self, 
        json_list: List[Dict[str, str]], 
        layer: int = 1,
    ) -> None:
        """Recurse through every element to recreate the sequence objects.
        
        Args:
            json_dictionary: The dictionary containing the values to recreate the sequence.
            layer: What layer the sequence element exists on.
            parent_action: The parent sequence element which enacts upon this element.
            previous_action: The previous sequence element which precedes this one.
            previous_location: The previous literal location within the widget.
        """        

        previous_sub_element = None
        previous_location = 0
        for json_dictionary in json_list:
            current_sub_element = ContainerLabel(self.item_window, json_dictionary[_ELEMENT_NAME], layer)
            if _SEQUENCE in json_dictionary:
                current_sub_element.set_json_dictionary(json_dictionary[_SEQUENCE], layer+1)

            current_sub_element.values.set_json_dictionary(json_dictionary)
        
            if self.sub_element is None:
                self.sub_element = current_sub_element
            if previous_sub_element is not None:
                current_sub_element.action_previous = previous_sub_element
                previous_sub_element.next_element = current_sub_element

            current_sub_element.connected_drops = [DropArea(self.item_window, layer), DropArea(self.item_window, layer, right_referential=True)]
            current_sub_element.connected_drops[0].layout_location = previous_location
            current_sub_element.connected_drops[1].layout_location = previous_location + 2
        
            self.drop_layout.addWidget(current_sub_element.connected_drops[0], 0, Qt.AlignmentFlag.AlignCenter)
            self.drop_layout.addWidget(current_sub_element)
            self.drop_layout.addWidget(current_sub_element.connected_drops[1], 0, Qt.AlignmentFlag.AlignCenter)
            
            previous_sub_element = current_sub_element
            previous_location += 3
        
        
class DropArea(QtWidgets.QWidget):
    """The area to drop a new widget into and create surrounding drop areaas."""
    
    def __init__(self, item_window: ItemWindow, layer: int, first_drop = False, right_referential = False) -> None:
        """Initialize a single drop window.

        Args:
            item_window: The window to change item values in.
            layer: The layer in which this drop area exists within.
            first_drop: Whether this is the first drop box to drop into.
            right_referential: Whether this is a drop box to the right of the widget.
        """
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumSize(20, 20)


        self.drop_layout = QtWidgets.QHBoxLayout()
        if not first_drop:
            self.setFixedSize(20, 20)
            self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
            self.drop_layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        self.setLayout(self.drop_layout)
        self.setStyleSheet(drop_area_style)
        self.layout_location = 0
        self.first_drop = first_drop
        self.right_referential = right_referential
        self.item_window = item_window
        self.sub_element: Optional[ContainerLabel] = None
        self.next_element: Optional[ContainerLabel] = None
        self.action_previous: Optional[ContainerLabel] = None
        self.layer = layer
  
    def minimumSizeHint(self) -> QtCore.QSize:
        """Make sure that the drop boxes are a certain size.

        Returns:
            QtCore.QSize: The minimum size that the re-sizer will go to.
        """
        return QtCore.QSize(20, 20)

    def sizeHint(self) -> QtCore.QSize:
        """Make sure that the drop boxes are a certain size.

        Returns:
            QtCore.QSize: The size that the re-sizer will go to.
        """
        return QtCore.QSize(20, 20)

    def paintEvent(self, _) -> None:
        """When this widget is being drawn to the screen"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(int(hover_color[1:3], 16), int(hover_color[3:5], 16), int(hover_color[5:7], 16)))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """When a widget is being dragged over this widget.
        
        Args:
            event: The event for when a widget is dragged into this widget.
        """
        event_source: DraggableLabel = event.source()
        label_name = event_source.text()
        if event.mimeData().hasFormat("application/x-qwidget"):
            # restrict certain sequence elements.
            if self.layer == 0 and (label_name == Actions.Chirp.value and label_name == Actions.Delay.value):
                event.ignore()
            elif self.layer == 1 and (label_name == Actions.Chirp.value or label_name == Actions.Simple_Config.value):
                event.ignore()
            elif self.layer == 2 and (label_name == Actions.Loop.value or label_name == Actions.Simple_Config.value):
                event.ignore()
            else:
                event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """When a widget is dragged over this event and then released.

        Args:
            event: The information pertaining to the widgets in this event.
        """
        # honestly this would be way better with lists, the linked nature of this means a lot of strange
        # reconnections during widget dropping.
        
        # I forgot what this does
        if self.sub_element:
            return
        
        # get the dragged objects label
        parent: Union[ContainerLabel, SignalWindow] = self.parent()
        event_source: DraggableLabel = event.source()
        label_name = event_source.text()

         
        new_label = ContainerLabel(self.item_window, label_name, layer=self.layer + 1)
        # if we are the first layer, we must be an infinite loop
        if self.layer != 0:
            new_drop_area_left = DropArea(self.item_window, layer=self.layer)
            new_drop_area_right =  DropArea(self.item_window, layer=self.layer, right_referential=True)
            new_label.connected_drops = (new_drop_area_left, new_drop_area_right)
        
        # if we are not the first layer, use your own layout, else use the signal windows layout
        if isinstance(self, ContainerLabel):
            layout = self.drop_layout
        else:
            layout = parent.drop_layout

        # if we are the first widget to be dropped, remove the old drop window
        if self.first_drop:
            parent.sub_element = new_label
            layout.removeWidget(self)
            self.setParent(None)
            self.deleteLater()

        # if this is a drop area item
        if isinstance(self, DropArea) and not self.first_drop:
            # move around the drop area so it looks consistent
            new_drop_area_left.layout_location = self.layout_location + self.right_referential
            new_drop_area_right.layout_location = self.layout_location + 2 + self.right_referential
            previous_item = parent.drop_layout.itemAt(self.layout_location - (1 + (not self.right_referential)))
            # if there is a previous widget, we need to connect it
            if previous_item is not None:
                new_label.action_previous = previous_item.widget()
                new_label.action_previous.next_element = new_label
            next_item = parent.drop_layout.itemAt(self.layout_location + 1 + self.right_referential)
            # if there is a next widget, we need to connect this to the next and to connect the parent to it as the first
            if next_item is not None:
                new_label.next_element = next_item.widget()
                new_label.next_element.action_previous = new_label
                if self.next_element == parent.sub_element:
                    parent.sub_element = new_label
            layout.insertWidget(self.layout_location+self.right_referential, new_drop_area_right)
            layout.insertWidget(self.layout_location+self.right_referential, new_label)
            layout.insertWidget(self.layout_location+self.right_referential, new_drop_area_left)
        else:
            # this is within another widget, so just reset everything
            self.sub_element = new_label
            if self.layer != 0:
                new_drop_area_left.layout_location = 0
                new_drop_area_right.layout_location = 2
                layout.addWidget(new_drop_area_left, 0, Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(new_label)
            if self.layer != 0:
                layout.addWidget(new_drop_area_right, 0, Qt.AlignmentFlag.AlignCenter)
        
        event.acceptProposedAction()
