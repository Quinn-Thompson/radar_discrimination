"""View the transforms through arbitrary code execution."""
from gui.sub_widgets.view_transforms import ViewTransforms, GraphTypes
from gui_backend.helpers import _RECEIVER_COUNT
from pathlib import Path
import importlib
import inspect
from matplotlib.axes import Axes
from typing import List
from gui.helpers import background_color
from functools import partial
import os
import numpy as np
import sys
from numpy.typing import NDArray
from PyQt6.QtWidgets import QFileDialog
from gui.main_window import MainWindow

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
        for receiver in range(1, _RECEIVER_COUNT+1):
            self.figure_layout.append(sub_window.widgets.figure.add_subplot(1, receiver, 1))
            self.figure_layout[receiver-1].patch.set_facecolor(background_color)
            self.figure_layout[receiver-1].set_title(f"Receiver {receiver}", fontsize=10, pad=24, color="white")
        sub_window.widgets.refresh.clicked.connect(partial(self.load_file_methods, _METHOD_PATH))
        sub_window.widgets.run_transforms.clicked.connect(self.run_transformation)
        sub_window.widgets.load_button.clicked.connect(self.find_location_to_load)
        self.methods = []
        self.module = None
        self.load_file_methods(_METHOD_PATH)
    
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
        
    def find_location_to_load(self):
        """Use the file explorer to determine where to load the data from."""
        folder = QFileDialog.getExistingDirectory(
            self.main_window, 
            "Select Folder", 
            "" 
        )

        if folder:
            self.sub_window.widgets.data_location.setText(folder)
        else:
            self.sub_window.widgets.data_location.setText("No file selected")

    def run_arbitrary_code(self, data_list: List[NDArray[np.float64]]):
        """Run the arbitrary code from the loaded methods.
        
        Args:
            data_list: The data to pass into the methods.
        """
        try:
            transformed_data_list = []
            current_metod = self.sub_window.widgets.method_dropdown.currentText()
            if current_metod == _NO_METHOD:
                transformed_data_list = data_list.copy()
            else:
                method = getattr(self.module, self.sub_window.widgets.method_dropdown.currentText())
                for data in data_list:            
                    transformed_data_list.append(method(data))
            return transformed_data_list
        except Exception as exception:
            traceback_object = exception.__traceback__
            line_number = traceback_object.tb_lineno
            self.main_window.timeout_label.setText(f"{line_number}: {exception}")
            return None
        
    def run_transformation(self):
        """Run the transformations provided by gui widgets."""
        data_list = []
        file_names = []
        for root, directories, files in os.walk(self.sub_window.widgets.data_location.text()):
            for file in files:
                data_list.append(np.load(os.path.join(root,file)))
                file_names.append(file)
                
        transformed_data_list = self.run_arbitrary_code(data_list)
        if transformed_data_list is None:
            return
        
        graph_type = self.sub_window.widgets.graph_type.currentText()
        if graph_type == GraphTypes.colormesh.value:
            self.p_color_mesh = []
            for receiver in range(0, _RECEIVER_COUNT):
                array_shape = transformed_data_list[0][receiver].shape
                self.p_color_mesh.append(self.figure_layout[receiver].pcolormesh(
                    np.arange(array_shape[1]), 
                    np.arange(array_shape[0]), 
                    transformed_data_list[0][receiver], 
                    shading="gouraud"
                ))
                
            for data in transformed_data_list:
                self.p_color_mesh[receiver].set_array(data[receiver])
                self.figure_layout[receiver].figure.canvas.draw_idle()