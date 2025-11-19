"""The window for displaying the bloch spheres."""
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from enum import Enum
from gui.helpers import WindowWidgets
from typing import List, Optional, Iterable, Union, NamedTuple, Dict
from functools import partial
import pyqtgraph as pg
from gui.helpers import _RECEIVER_COUNT, background_color, _FEATURES_INFO, _TRANSFORM_INFO, ComboBoxWithText, _NO_METHOD
from numpy.typing import NDArray
import numpy as np
import time

Boundaries = NamedTuple("Boundaries", [("minimum", float), ("maximum", float)])


class GraphTypes(Enum):
    plot_2d = "2D Plot"
    colormesh = "Color Mesh"


class ReceiverPlots(pg.GraphicsLayoutWidget):
    def __init__(self):
        super().__init__()

        # Set global background
        pg.setConfigOption("background", background_color)
        pg.setConfigOption("foreground", "w")

        self.plots: List[pg.PlotItem] = []
        self.sub_plots: List[pg.ImageItem, List[pg.PlotCurveItem]] = []
        self.current_boundaries = Boundaries(minimum=float("-inf"), maximum=float("inf"))
        
        self.graph_type: Optional[GraphTypes] = None
        for receiver in range(1, _RECEIVER_COUNT + 1):

            subplot = self.ci.addPlot(title=f"Receiver {receiver}")
            # subplot.getViewBox().disableAutoRange(axis='y')
            self.plots.append(subplot)
            subplot.getViewBox().setBackgroundColor(background_color)
            subplot.setTitle(f"Receiver {receiver}", color="w", size="12pt")

            subplot.getAxis("bottom").setPen(pg.mkPen("w", width=2))
            subplot.getAxis("left").setPen(pg.mkPen("w", width=2))
            subplot.getAxis("bottom").setTextPen("w")
            subplot.getAxis("left").setTextPen("w")

            subplot.getViewBox().setBorder(pg.mkPen(color="w", width=2))

            self.ci.nextCol()
    
    def update_plot(self, transformed_data: NDArray[np.float64]):
        max_value = 0.0
        min_value = float("inf")

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
                sub_plot.setImage(np.real(transformed_data[receiver]))
                sub_plot.setRect(QtCore.QRectF(0, 0, 300, 300))

                
            elif self.graph_type == GraphTypes.plot_2d.value:
                if changed_boundaries:
                        plot.setYRange(self.current_boundaries.minimum, self.current_boundaries.maximum)
                if len(transformed_data[receiver].shape) > 1:
                    for plot_index, line_plot in enumerate(self.sub_plots[receiver]):
                        # print(transformed_data.shape)
                        line_plot.setData(np.real(transformed_data[receiver][plot_index]))

    def clear_graph(self):
        for sub_plot in self.plots:
            sub_plot.clear()
            self.sub_plots = []
            
    def graphs_change(self, dummy_transformed_data: NDArray[np.float64]):
        self.clear_graph()
        for receiver, plot in enumerate(self.plots):
            if self.graph_type == GraphTypes.colormesh.value:
                image_item = pg.ImageItem()
                plot.addItem(image_item)
                self.sub_plots.append(image_item)
            else:
                if len(dummy_transformed_data[receiver].shape) > 1:
                    lines = []
                    for _ in range(dummy_transformed_data[receiver].shape[0]):
                        line_plot = plot.plot()
                        lines.append(line_plot)
                    self.sub_plots.append(lines)
                else:
                    line_plot = plot.plot()
                    self.sub_plots.append([line_plot])
    

class SingleChirpViewWindow(QtWidgets.QFrame):
    def __init__(self, graph_type: str) -> None:
        super().__init__()
        self.graph_widgets = ReceiverPlots()
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
            _TRANSFORM_INFO: ComboBoxWithText(_TRANSFORM_INFO.module_name, [_NO_METHOD]),
            _FEATURES_INFO: ComboBoxWithText(_FEATURES_INFO.module_name, [_NO_METHOD]),
        }
        self.graph_type = ComboBoxWithText("Graph Type", [graph_type.value for graph_type in GraphTypes])
        self.refresh = QtWidgets.QPushButton()
        super().__init__()

class AllChirpContainerWindow(QtWidgets.QFrame):
    def __init__(self, identification: str):
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
        
        self.graph_layout.addWidget(
            self.widgets.graph_type,
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        
        self.method_layout.addWidget(
            self.widgets.method_dropdowns[_TRANSFORM_INFO],
            0, 
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.method_layout.addWidget(
            self.widgets.method_dropdowns[_FEATURES_INFO],
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
    
    def add_new_views(self, view_count: int):
        self.plots_set = False

        for chirp_tab in self.chirp_tabs:
            self.chirp_tabs_bar.removeTab(self.chirp_tabs_bar.indexOf(chirp_tab))
        self.chirp_tabs: List[SingleChirpViewWindow] = []
        for chirp_number in range(view_count):
            self.chirp_tabs.append(SingleChirpViewWindow(self.graph_type))
            self.chirp_tabs_bar.addTab(self.chirp_tabs[-1], f"Chirp #{chirp_number}")
    
    def setup_new_sub_plots(self, frame_list: List[NDArray[np.float64]]):
        for chirp, frame in zip(self.chirp_tabs, frame_list):
            chirp.graph_widgets.graphs_change(frame)
    
    def update_graph_type(self, graph_type: GraphTypes):
        self.graph_type = graph_type
        for chirp_tab in self.chirp_tabs:
            chirp_tab.graph_widgets.graph_type = self.graph_type
    
    def clear_views(self):
        for chirp_tab in self.chirp_tabs:
            chirp_tab.graph_widgets.clear_graph()
    
    def update_views(self, transformed_data: List[NDArray[np.float64]]):
        self.current_data = transformed_data
        if self.isVisible():
            for chirp_index, chirp_tab in enumerate(self.chirp_tabs):
                chirp_tab.graph_widgets.update_plot(transformed_data[chirp_index])


class AddTab(QtWidgets.QTabWidget):
    added_new_tab = QtCore.pyqtSignal(object)
    
    def __init__(self):
        self._unique_tab_names = 0
        super().__init__()

        self.addTab(QtWidgets.QWidget(), "+")
        self.tabBarClicked.connect(self.handle_tab_click)
        
        self.tabCloseRequested.connect(lambda index: self.removeTab(index))
        self.view_tabs: Dict[str, AllChirpContainerWindow] = {}
        self.all_chirps = None

    def handle_tab_click(self, index):
        if index == self.count() - 1:
            self.create_new_tab()

    def create_new_tab(self):
        print(f"New tab {time.time()}")
        self._unique_tab_names += 1
        self.view_tabs[str(self._unique_tab_names)] = AllChirpContainerWindow(str(self._unique_tab_names))
        self.root_layoutH = QtWidgets.QHBoxLayout()
        self.root_layoutH.addWidget(self.all_chirps)
        index = self.insertTab(self.count() - 1, self.view_tabs[str(self._unique_tab_names)], f"View {self.count()}")
        self.setCurrentIndex(self.count() - 2) 
        self.root_layoutH.setContentsMargins(5, 0, 0, 0)
        self.root_layoutH.setSpacing(5)

        tab_name = QtWidgets.QLabel(f"View {index}")
        close_button = QtWidgets.QToolButton()
        close_button.setText("X")
        close_button.clicked.connect(partial(self.close_tab, self.widget(index)))

        self.root_layoutH.addWidget(tab_name)
        self.root_layoutH.addWidget(close_button)

        self.tabBar().setTabButton(index, QtWidgets.QTabBar.ButtonPosition.RightSide, close_button)
        self.added_new_tab.emit(self.view_tabs[str(self._unique_tab_names)])

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
        self.seperate_viewer_tabs = AddTab()
        self.root_layoutV.addWidget(self.seperate_viewer_tabs)
    
    def __iter__(self) -> Iterable[AddTab]:
        return iter(self.seperate_viewer_tabs.view_tabs)
