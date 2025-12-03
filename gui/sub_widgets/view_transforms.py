"""The window for displaying the bloch spheres."""
from PyQt6 import QtWidgets, QtGui
from PyQt6 import QtCore
from enum import Enum
from gui.helpers import WindowWidgets
from typing import List, Optional, Iterable, Union, NamedTuple, Dict
from functools import partial
import pyqtgraph as pg
from gui.helpers import _RECEIVER_COUNT, background_color, _HISTORY_TRANSFORMS_INFO, \
_SINGLE_TRANSFORM_INFO, ComboBoxWithText, _NO_METHOD, TertiaryData
from numpy.typing import NDArray
import numpy as np
import time

Boundaries = NamedTuple("Boundaries", [("minimum", float), ("maximum", float)])

class GraphTypes(Enum):
    plot_2d = "Line Plots"
    colormesh = "Grid Plot"


class ReceiverPlots(pg.GraphicsLayoutWidget):
    def __init__(self, glyph_cache: Dict[str, NDArray[np.float64]]):
        super().__init__()
        self.glyph_cache = glyph_cache
        # Set global background
        pg.setConfigOption("background", background_color)
        pg.setConfigOption("foreground", "w")
        self.plots: List[pg.PlotItem] = []
        self.lines: List[pg.PlotDataItem] = [] 
        self.sub_plots: List[pg.ImageItem, List[pg.PlotCurveItem]] = []
        self.notable_events = {}
        self.graph_type: Optional[GraphTypes] = None
        self.current_boundaries = Boundaries(minimum=float("-inf"), maximum=float("inf"))
        self.ci.setMinimumHeight(400)

    def setup_plots(self, plot_count: int, tertiary_data: TertiaryData):
        self.current_boundaries = Boundaries(minimum=float("-inf"), maximum=float("inf"))
        for receiver in range(plot_count):
            if receiver >= len(tertiary_data.graph_info.per_subplot_info):
                plot_title = "Receiver"
            else:
                plot_title = tertiary_data.graph_info.per_subplot_info[receiver].sub_plot_name
            subplot = self.ci.addPlot(title=plot_title)
            # subplot.getViewBox().disableAutoRange(axis='y')
            self.plots.append(subplot)
            subplot.getViewBox().setBackgroundColor(background_color)
            subplot.setTitle(plot_title, color="w", size="12pt")

            subplot.getAxis("bottom").setPen(pg.mkPen("w", width=2))
            subplot.getAxis("left").setPen(pg.mkPen("w", width=2))
            subplot.getAxis("bottom").setTextPen("w")
            subplot.getAxis("left").setTextPen("w")

            subplot.getViewBox().setBorder(pg.mkPen(color="w", width=2))
            self.lines.append(pg.PlotDataItem([], [], pen='r'))
            self.plots[receiver].addItem(self.lines[receiver])

            self.ci.nextCol()
    
    def text_array_to_qimage(self, transformed_data: NDArray[np.str_]):
        cell_size = 30
        rows, columns = transformed_data.shape
        image = np.zeros((columns * int(transformed_data.dtype.str[2:]) * cell_size, rows * cell_size, 4))

        for row_index, row in enumerate(transformed_data):
            for column_index, column in enumerate(row):
                for character_index, character in enumerate(column):
                    glyph = self.glyph_cache.get(character, self.glyph_cache[' '])  # fallback to space
                    height, width = glyph.shape[:2]
                    start_column_location = (len(column) * column_index + character_index)*cell_size
                    end_column_location = (len(column) * column_index + character_index)*cell_size+width
                    image[start_column_location:end_column_location, row_index*cell_size:row_index*cell_size+height] = glyph

        return image

    def update_plot(self, transformed_data: NDArray[np.float64], tertiary_data: TertiaryData):
        max_value = 0.0
        min_value = float("inf")

        if self.graph_type == GraphTypes.plot_2d.value:
            data_max = np.max(transformed_data)
            data_min = np.min(transformed_data)
            if data_max > max_value:
                max_value = data_max
            if data_min < min_value:
                min_value = data_min
            changed_boundaries = False        
            if (
                min_value < self.current_boundaries.minimum 
                or min_value > self.current_boundaries.minimum + (max_value * 0.6)
                or max_value > self.current_boundaries.maximum 
                or max_value < self.current_boundaries.maximum - (max_value * 0.6)
            ):
                changed_boundaries = True
                self.current_boundaries = Boundaries(min_value - (max_value * 0.3), max_value + (max_value * 0.3))
            
        for receiver, (sub_plot, plot) in enumerate(zip(self.sub_plots, self.plots)):
            
            if self.graph_type == GraphTypes.colormesh.value:
                # if changed_boundaries:
                #     sub_plot.setLevels([self.current_boundaries.minimum, self.current_boundaries.maximum])
                if transformed_data.dtype == np.str_ or transformed_data.dtype.str.startswith("<U"):
                    to_set_image = self.text_array_to_qimage(transformed_data)
                else:
                    to_set_image = np.real(transformed_data[receiver])
                sub_plot.setImage(to_set_image)
                sub_plot.setRect(QtCore.QRectF(0, 0, 300, 300))

            elif self.graph_type == GraphTypes.plot_2d.value:
                ymin, ymax = plot.getViewBox().viewRange()[1]
                xs = []
                ys = [] 
                for notable_event, notable_index in tertiary_data.notable_events.items():
                    if notable_event not in self.notable_events:
                        xs.extend([notable_index, notable_index, np.nan])
                        ys.extend([ymin, ymax, np.nan])
                
                self.lines[receiver].setData(xs, ys)

                
                if transformed_data.dtype == np.str_ or transformed_data.dtype.str.startswith("<U"):
                    raise TypeError("Line Plots do not support text formats.")
                if changed_boundaries:
                        plot.setYRange(self.current_boundaries.minimum, self.current_boundaries.maximum)
                for plot_index, line_plot in enumerate(sub_plot):
                    # print(transformed_data.shape)
                    if len(transformed_data.shape) == 3:
                        line_plot.setData(np.real(transformed_data[receiver][plot_index]))
                    elif len(transformed_data.shape) == 2:
                        line_plot.setData(np.real(transformed_data[plot_index]))
                    else:
                        line_plot.setData(np.real(transformed_data))
                        
    def clear_graph(self):
        for plot in self.plots:
            self.ci.removeItem(plot)
        
        self.lines = []
        self.plots = []
        self.sub_plots = []
        self.ci.update()
            
    def graphs_change(self, dummy_transformed_data: NDArray[np.float64], tertiary_data: TertiaryData):
        self.clear_graph()
        dummy_size = len(dummy_transformed_data.shape)
        if dummy_size == 3:
            plot_count = dummy_transformed_data.shape[0]
        elif dummy_size == 2:
            plot_count = 1
        else:
            plot_count = 1
        
        self.setup_plots(plot_count, tertiary_data)
        if self.graph_type == GraphTypes.colormesh.value:
            self.plots[0].setLabel(
                "left", 
                tertiary_data.graph_info.y_axis_label.name,
                units=tertiary_data.graph_info.y_axis_label.units
            )
        elif self.graph_type == GraphTypes.plot_2d.value:
            self.plots[0].setLabel(
                "left", 
                tertiary_data.graph_info.z_axis_label.name,
                units=tertiary_data.graph_info.z_axis_label.units
            )
        
        for receiver, plot in enumerate(self.plots):
            plot.setLabel(
                "bottom", 
                tertiary_data.graph_info.per_subplot_info[receiver].x_axis_label.name, 
                units=tertiary_data.graph_info.per_subplot_info[receiver].x_axis_label.units
            )
            if self.graph_type == GraphTypes.colormesh.value:
                image_item = pg.ImageItem()
                plot.addItem(image_item)

                plot.setLabel('left', 'Amplitude', units='ADC')
                self.sub_plots.append(image_item)
            else:
                if dummy_size > 1:
                    lines = []
                    for _ in range(dummy_transformed_data.shape[dummy_size-2]):
                        line_plot = plot.plot()
                        lines.append(line_plot)
                    self.sub_plots.append(lines)
                else:
                    line_plot = plot.plot()
                    self.sub_plots.append([line_plot])
                    

    

class SingleChirpViewWindow(QtWidgets.QFrame):
    def __init__(self, graph_type: str, glyph_cache: Dict[str, NDArray[np.float64]]) -> None:
        super().__init__()
        self.graph_widgets = ReceiverPlots(glyph_cache)
        self.graph_widgets.graph_type = graph_type
        self.root_layoutV = QtWidgets.QVBoxLayout()
        self.setObjectName("ViewTransforms")
        self.setLayout(self.root_layoutV)
        self.root_layoutV.addWidget(self.graph_widgets)

class AllChirpContainerWidget(WindowWidgets):
    """The widgets for the rx transforms.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.method_dropdowns = {
            _SINGLE_TRANSFORM_INFO: ComboBoxWithText(_SINGLE_TRANSFORM_INFO.module_name, [_NO_METHOD]),
            _HISTORY_TRANSFORMS_INFO: ComboBoxWithText(_HISTORY_TRANSFORMS_INFO.module_name, [_NO_METHOD]),
        }
        self.graph_type = ComboBoxWithText("Graph Type", [graph_type.value for graph_type in GraphTypes])
        self.refresh = QtWidgets.QPushButton()
        super().__init__()

class AllChirpContainerWindow(QtWidgets.QFrame):
    def __init__(self, identification: str, glyph_cache: Dict[str, NDArray[np.float64]]):
        super().__init__()
        self.identification = identification
        self.root_layoutV = QtWidgets.QVBoxLayout()
        self.setObjectName("ViewTransforms")
        self.setLayout(self.root_layoutV)
        self.widgets = AllChirpContainerWidget()
        self.chirp_tabs: List[SingleChirpViewWindow] = []
        self.chirp_tabs_bar = QtWidgets.QTabWidget()
        self.matplotlib_layout = QtWidgets.QGridLayout()
        self.graph_layout = QtWidgets.QGridLayout()
        self.method_layout = QtWidgets.QGridLayout()
        self.root_layoutV.addLayout(self.matplotlib_layout)
        self.root_layoutV.addLayout(self.graph_layout)
        self.root_layoutV.addLayout(self.method_layout)
        self.root_layoutV.addWidget(self.chirp_tabs_bar)
        self.current_data = None
        self.plots_set = False
        self.graph_type = GraphTypes.plot_2d.value
        self.glyph_cache = glyph_cache
        
        self.graph_layout.addWidget(
            self.widgets.graph_type,
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        
        self.method_layout.addWidget(
            self.widgets.method_dropdowns[_SINGLE_TRANSFORM_INFO],
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.method_layout.addWidget(
            self.widgets.method_dropdowns[_HISTORY_TRANSFORMS_INFO],
            0, 
            1,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.method_layout.addWidget(
            self.widgets.refresh,
            0, 
            2,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        
        self.widgets.refresh.setText("Refresh")
    
    def showEvent(self, event):
        super().showEvent(event)
        if self.current_data is not None:
            self.update_views(self.current_data)
    
    def add_new_views(self, view_count: int, tertiary_data: TertiaryData):
        self.plots_set = False

        for chirp_tab in self.chirp_tabs:
            self.chirp_tabs_bar.removeTab(self.chirp_tabs_bar.indexOf(chirp_tab))
        self.chirp_tabs: List[SingleChirpViewWindow] = []
        for chirp_number in range(view_count):
            self.chirp_tabs.append(SingleChirpViewWindow(self.graph_type, self.glyph_cache))
            
            if chirp_number >= len(tertiary_data.graph_info.tab_names):
                self.chirp_tabs_bar.addTab(self.chirp_tabs[-1], f"Chirp {chirp_number}")            
            else:
                self.chirp_tabs_bar.addTab(self.chirp_tabs[-1], tertiary_data.graph_info.tab_names[chirp_number])
    
    def setup_new_sub_plots(self, frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
        for chirp, frame in zip(self.chirp_tabs, frame_list):
            chirp.graph_widgets.graphs_change(frame, tertiary_data)
    
    def update_graph_type(self, graph_type: GraphTypes):
        self.graph_type = graph_type
        for chirp_tab in self.chirp_tabs:
            chirp_tab.graph_widgets.graph_type = self.graph_type
    
    def clear_views(self):
        for chirp_tab in self.chirp_tabs:
            chirp_tab.graph_widgets.clear_graph()
    
    def update_views(self, transformed_data: List[NDArray[np.float64]], tertiary_data: TertiaryData):
        self.current_data = transformed_data
        if self.isVisible():
            for chirp_index, chirp_tab in enumerate(self.chirp_tabs):
                chirp_tab.graph_widgets.update_plot(transformed_data[chirp_index], tertiary_data)


class AddTab(QtWidgets.QTabWidget):
    """The tab bar that has a dedicated tab for adding more tabs."""
    added_new_tab = QtCore.pyqtSignal(object)
    
    def __init__(self, glyph_cache: Dict[str, NDArray]):
        """Initialize the tab and define some behavior."""
        self._unique_tab_names = 0
        self.glyph_cache = glyph_cache
        super().__init__()

        self.addTab(QtWidgets.QWidget(), "+")
        self.tabBarClicked.connect(self.handle_tab_click)
        
        self.tabCloseRequested.connect(lambda index: self.removeTab(index))
        self.view_tabs: Dict[str, AllChirpContainerWindow] = {}

    def handle_tab_click(self, index: int):
        """Event for when a tab is clicked on. If it is the rightmost, add a new tab.
        
        Args:
            index: The index for the tab that was pressed
        """
        if index == self.count() - 1:
            self.create_new_tab()

    def create_new_tab(self):
        print(time.time())
        self._unique_tab_names += 1
        self.view_tabs[str(self._unique_tab_names)] = AllChirpContainerWindow(str(self._unique_tab_names), self.glyph_cache)
        self.root_layoutH = QtWidgets.QHBoxLayout()
        index = self.insertTab(self.count() - 1, self.view_tabs[str(self._unique_tab_names)], f"View {self.count()}")
        self.setCurrentIndex(self.count() - 2) 
        self.root_layoutH.setContentsMargins(5, 0, 0, 0)
        self.root_layoutH.setSpacing(5)
        print(f" before Tool button{time.time()}")

        tab_name = QtWidgets.QLabel(f"View {index}")
        close_button = QtWidgets.QToolButton()
        close_button.setText("X")
        close_button.clicked.connect(partial(self.close_tab, self.widget(index)))
        print(f" after Tool button{time.time()}")
        self.root_layoutH.addWidget(tab_name)
        self.root_layoutH.addWidget(close_button)
        print(f" after add widget{time.time()}")

        self.tabBar().setTabButton(index, QtWidgets.QTabBar.ButtonPosition.RightSide, close_button)
        print(f" tab button{time.time()}")

        self.added_new_tab.emit(self.view_tabs[str(self._unique_tab_names)])
        print(time.time())

    def close_tab(self, tab: AllChirpContainerWindow):
        self.removeTab(self.indexOf(tab))
        del self.view_tabs[tab.identification]
        
    def add_new_views(self, view_count: int):
        for tab in self.view_tabs.values():
            tab.add_new_views(view_count)
        
    def update_views(self, transformed_data: Union[List[NDArray[np.float64]], NDArray[np.float64]]):
        for tab in self.view_tabs.values():
            tab.update_views(transformed_data)


class ViewTransforms(QtWidgets.QFrame):
    """The frame for displaying the transforms for the rx information.
    """
    def __init__(self) -> None:
        """Initialize the window for the rx transforms.
        """
        super().__init__()
        self.root_layoutV = QtWidgets.QVBoxLayout()
        self.setObjectName("ViewTransforms")
        self.setLayout(self.root_layoutV)
        self.glyph_cache = self.create_glyph_cache()
        self.seperate_viewer_tabs = AddTab(self.glyph_cache)
        self.root_layoutV.addWidget(self.seperate_viewer_tabs)
        self.setMinimumHeight(800)
    
    def create_glyph_cache(self, font_name: str = "Monospace", font_size: int = 12, chars: Optional[List[str]] = None):
        if chars is None:
            chars = [chr(i) for i in range(32, 127)]

        glyph_cache = {}
        font = QtGui.QFont(font_name)
        font.setPointSize(font_size)

        for c in chars:
            # create a small image just big enough for one character
            image = QtGui.QImage(font_size*2, font_size*2, QtGui.QImage.Format.Format_ARGB32)
            image.fill(QtGui.QColor(0, 0, 0, 0))
            painter = QtGui.QPainter(image)
            painter.setFont(font)
            painter.setPen(QtGui.QColor(255, 255, 255))
            painter.drawText(0, font_size, c)
            painter.end()

            # convert to numpy array if you want to manipulate with numpy
            ptr = image.bits()
            ptr.setsize(image.width() * image.height() * image.depth() // 8)

            arr = np.rot90(np.array(ptr).reshape((image.height(), image.width(), 4)), k = 3)
            glyph_cache[c] = arr

        return glyph_cache
    
    def __iter__(self) -> Iterable[AddTab]:
        return iter(self.seperate_viewer_tabs.view_tabs)
