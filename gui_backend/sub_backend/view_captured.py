
from gui.sub_widgets.view_captured import ViewCaptured
from gui_backend.sub_backend.view_transforms import ViewTransformsBackend
from gui_backend.pull_data import DataHandler
from gui.main_window import MainWindow
from PyQt6.QtWidgets import QFileDialog
import os
import numpy as np

class ViewCapturedBackend:
    """Visualize the transforms provided from methods in another file."""
    
    def __init__(self, main_window: MainWindow, sub_window: ViewCaptured, data_handler):
        """Initialize the elements and events for the view transforms window.
        
        Args:
            main_window: The main gui window.
            sub_window: The window this backend is supporting.
        """
        self.main_window = main_window
        self.sub_window = sub_window
        self.data_handler = data_handler
        self.current_folder = None
        sub_window.widgets.load_button.clicked.connect(self.find_location_to_load)
        self.main_window.sub_window_widgets.render_control.widgets.which_bloch.valueChanged.connect(self.on_slider_change)
        self.main_window.sub_window_widgets.render_control.widgets.next_button.clicked.connect(self.next_plot)
        self.main_window.sub_window_widgets.render_control.widgets.prev_button.clicked.connect(self.prev_plot)
        
        # self.transforms_backend = ViewTransformsBackend(self.main_window, self.sub_window.view_transforms_window, None, None)
        self.data_list = []
        self.file_names = []
        
        
    def find_location_to_load(self):
        """Use the file explorer to determine where to load the data from."""
        folder = QFileDialog.getExistingDirectory(
            self.main_window, 
            "Select Folder", 
            "" 
        )

        if folder:
            self.current_folder = folder
            self.data_list = []
            self.file_names = []      
            self.current_index = 0
            for root, directories, files in os.walk(folder):
                for file in files:
                    self.data_list.append(np.load(os.path.join(root,file)))
                    self.file_names.append(file)
                    
            self.main_window.sub_window_widgets.render_control.widgets.which_bloch.setMaximum(len(self.file_names) - 1)
            self.transforms_backend.run_transformation(self.data_list[self.current_index])
 
    def on_slider_change(self, value):
        self.current_index = value
        self.transforms_backend.run_transformation(self.data_list[self.current_index])

    def next_plot(self):
        self.current_index += 1 if self.current_index < (len(self.data_list) - 1) else 0
        self.transforms_backend.run_transformation(self.data_list[self.current_index])
        
    def prev_plot(self):
        self.current_index -= 1 if self.current_index > 0 else 0
        self.transforms_backend.run_transformation(self.data_list[self.current_index])

    
