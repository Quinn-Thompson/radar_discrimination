"""View the transforms through arbitrary code execution."""
from gui.sub_widgets.view_transforms import ViewTransforms, GraphTypes
from gui_backend.helpers import _RECEIVER_COUNT
from pathlib import Path
import matplotlib
matplotlib.use("Qt5Agg")
import importlib
import inspect
from matplotlib.axes import Axes
from typing import List, Union, Optional, Tuple
from gui.helpers import background_color
from functools import partial
import os
import numpy as np
import sys
from numpy.typing import NDArray
from gui.main_window import MainWindow
from matplotlib.lines import Line2D
from matplotlib.image import AxesImage
from functools import partial


_METHOD_FOLDER = Path("transformation_methods")
_METHOD_PATH = _METHOD_FOLDER / "transformations.py"

_NO_METHOD = "none"

_MODULE_NAME = "transforms"

class ViewTransformsBackend:
    """Visualize the transforms provided from methods in another file."""
    
    def __init__(self, main_window: MainWindow, sub_window: ViewTransforms):
        """Initialize the elements and events for the view transforms window.
        
        Args:
            main_window: The main gui window.
            sub_window: The window this backend is supporting.
        """
        self.main_window = main_window
        self.sub_window = sub_window
        self.figure_layout: List[Axes] = []
        self.sub_window.widgets.figure.patch.set_facecolor(background_color)
        # thickness
        for receiver in range(1, _RECEIVER_COUNT+1):

            self.figure_layout.append(sub_window.widgets.figure.add_subplot(1, _RECEIVER_COUNT, receiver))
            for spine in self.figure_layout[receiver-1].spines.values():
                spine.set_edgecolor('white')   # color of border lines
                spine.set_linewidth(2) 
            self.figure_layout[receiver-1].patch.set_facecolor(background_color)
            self.figure_layout[receiver-1].set_title(f"Receiver {receiver}", fontsize=10, pad=24, color="white")
            self.figure_layout[receiver-1].tick_params(axis='x', colors='white')
            self.figure_layout[receiver-1].tick_params(axis='y', colors='white')
        sub_window.widgets.refresh.clicked.connect(partial(self.load_file_methods, _METHOD_PATH))
        sub_window.widgets.method_dropdown.currentTextChanged.connect(partial(self.run_transformation, None))
        sub_window.widgets.graph_type.currentTextChanged.connect(partial(self.run_transformation, None))

        self.methods = []
        self.module = None
        self.current_data: Optional[NDArray[np.float64]] = None
        self.load_file_methods(_METHOD_PATH)
        
        self.current_index = 0
        self.subplots: List[Optional[Union[AxesImage, List[Line2D]]]] = [None, None, None]
    
    def load_file_methods(self, file_path: Path):
        """Load the methods from another file for arbitrary code execution.

        Args:
            file_path: The file to load the methods from.
        """
        if _MODULE_NAME in sys.modules:
            del sys.modules[_MODULE_NAME]

        # Load module again
        spec = importlib.util.spec_from_file_location(_MODULE_NAME, str(file_path.resolve()))
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[_MODULE_NAME] = self.module
        spec.loader.exec_module(self.module)
        
        self.methods = [name for name, obj in inspect.getmembers(self.module, inspect.isfunction)]
        self.sub_window.widgets.method_dropdown.clear()
        self.sub_window.widgets.method_dropdown.addItem(_NO_METHOD)
        self.sub_window.widgets.method_dropdown.addItems(self.methods)
        

    def run_arbitrary_code(self, data: NDArray[np.float64]):
        """Run the arbitrary code from the loaded methods.
        
        Args:
            data_list: The data to pass into the methods.
        """
        try:
            current_metod = self.sub_window.widgets.method_dropdown.currentText()
            if current_metod == _NO_METHOD:
                transformed_data = data
            else:
                method = getattr(self.module, self.sub_window.widgets.method_dropdown.currentText())   
                transformed_data = method(data)
            return transformed_data
        except Exception as exception:
            traceback_object = exception.__traceback__
            line_number = traceback_object.tb_lineno
            self.main_window.timeout_label.setText(f"{line_number}: {exception}")
            return None
        
    def run_transformation(self, data: Optional[NDArray[np.float64]] = None):
        """Run the transformations provided by gui widgets."""
        if data is not None:
            transformed_data = self.run_arbitrary_code(data)
        elif self.current_data is not None:
            transformed_data = self.run_arbitrary_code(self.current_data)
        else:
            return
        self.handle_graphs(transformed_data)

    def clear_graph(self, receiver: int):
        self.figure_layout[receiver].clear()
        self.figure_layout[receiver].patch.set_facecolor(background_color)
        self.figure_layout[receiver].set_title(f"Receiver {receiver}", fontsize=10, pad=24, color="white")

    def draw_color_mesh_plot(self, transformed_data: NDArray[np.float64], receiver: int, boundaries: Tuple[int, int]):
        if isinstance(self.subplots[receiver], AxesImage) and self.current_data.shape == transformed_data.shape:
            self.subplots[receiver].set_data(transformed_data[receiver])
            self.subplots[receiver].set_clim(boundaries[0], boundaries[1])
        else:
            self.clear_graph(receiver)
            self.subplots[receiver] = self.figure_layout[receiver].imshow(
                transformed_data[receiver], 
                cmap="viridis",
                aspect="auto"
            )
        self.current_data = transformed_data

    def draw_2d_plot(self, transformed_data: NDArray[np.float64], receiver: int, boundaries: Tuple[int, int]):
        if len(transformed_data[receiver].shape) > 1:
            if isinstance(self.subplots[receiver], list) and len(self.subplots[receiver]) == len(self.figure_layout[receiver].get_lines()):
                for old_line, new_line in zip(self.figure_layout[receiver].get_lines(), transformed_data[receiver]):
                    old_line.set_ydata(new_line)
                self.figure_layout[receiver].set_ylim(boundaries[0], boundaries[1])
            else:
                self.clear_graph(receiver)
                self.subplots[receiver] = []
                for new_line in transformed_data[receiver]:
                    self.subplots[receiver].append(self.figure_layout[receiver].plot(
                        np.arange(transformed_data[receiver].shape[1]), 
                        new_line
                    ))
                self.figure_layout[receiver].set_ylim(boundaries[0], boundaries[1])
                self.figure_layout[receiver].relim()
                self.figure_layout[receiver].autoscale(enable=True, axis="x")
        else:
            if isinstance(self.subplots[receiver], Line2D) and len(self.figure_layout[receiver].get_lines()) == 1:
                self.subplots[receiver].set_ydata(transformed_data[receiver])
                self.subplots[receiver].set_clim(boundaries[0], boundaries[1])
            else:
                self.clear_graph(receiver)
                self.subplots[receiver].append(self.figure_layout[receiver].plot(
                    np.arange(transformed_data.shape[1]), 
                    transformed_data[receiver]
                ))
                self.figure_layout[receiver].set_ylim(boundaries[0], boundaries[1])
                self.figure_layout[receiver].relim()
                self.figure_layout[receiver].autoscale(enable=True, axis="x")
                
        self.current_data = transformed_data
        
    def handle_graphs(self, transformed_data: NDArray[np.float64]):
        try:
            max_value = 0.0
            min_value = float("inf")
            for receiver in range(0, _RECEIVER_COUNT):
                data_max = np.max(transformed_data[receiver])
                data_min = np.min(transformed_data[receiver])
                if data_max > max_value:
                    max_value = data_max
                if data_min < min_value:
                    min_value = data_min
            boundaries = (min_value, max_value)
            graph_type = self.sub_window.widgets.graph_type.currentText()
            for receiver in range(0, _RECEIVER_COUNT):
                if graph_type == GraphTypes.colormesh.value:
                    self.draw_color_mesh_plot(transformed_data, receiver, boundaries)
                elif graph_type == GraphTypes.plot_2d.value:
                    self.draw_2d_plot(transformed_data, receiver, boundaries)

            self.figure_layout[receiver].figure.canvas.draw_idle()

        except (ValueError, TypeError) as exception:
            traceback_object = exception.__traceback__
            line_number = traceback_object.tb_lineno
            self.main_window.timeout_label.setText(f"{line_number}: {exception}")
            return None