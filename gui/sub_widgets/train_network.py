"""The window for displaying the bloch spheres."""
from gui.sub_widgets.render_window import RenderWindowControl
from gui.sub_widgets.view_transforms import ViewTransforms
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from gui.helpers import WindowWidgets, LineEditWithText, ComboBoxWithText, Models, LossType

class NetworkInfoWidgets(WindowWidgets):
    """The widgets for the rx transforms.
    """
    def __init__(self) -> None:
        """Initialize each widget within the window.
        """
        self.run_button = QtWidgets.QPushButton("Train Model")
        self.epoch_count = LineEditWithText("Number Of Epochs")
        self.batch_count = ComboBoxWithText("Batch Count", ["16", "32", "64", "128", "256"])
        self.train_val_split = ComboBoxWithText("Training Percent", ["80", "90", "95", "98", "99"])
        self.loss_type = ComboBoxWithText("Loss", [loss.name for loss in LossType])
        self.data_file_explorer = QtWidgets.QPushButton("Data Explorer")
        self.data_location = LineEditWithText("Data Location")
        self.label_file_explorer = QtWidgets.QPushButton("Label Explorer")
        self.label_location = LineEditWithText("Label Location")
        self.noise_file_explorer = QtWidgets.QPushButton("Noise Explorer")
        self.noise_location = LineEditWithText("Noise Location")
        self.model_selection = ComboBoxWithText("Model", [model.name for model in Models])
        self.learning_rate = LineEditWithText("Learning Rate")
        self.time_between_draws = LineEditWithText("Draw Time")

        self.begin_training = QtWidgets.QPushButton()
        super().__init__()

class NetworkInfoWindow(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.widgets = NetworkInfoWidgets()
        self.root_layoutV = QtWidgets.QVBoxLayout()
        
        self.setLayout(self.root_layoutV)
        
        self.root_layoutV.addWidget(self.widgets.model_selection, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.data_file_explorer, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.data_location, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.label_file_explorer, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.label_location, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.noise_file_explorer, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.noise_location, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.loss_type, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.epoch_count, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.learning_rate, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.batch_count, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.time_between_draws, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.train_val_split, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.root_layoutV.addWidget(self.widgets.run_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

class TrainNetwork(QtWidgets.QFrame):
    """The frame for displaying the transforms for the rx information.
    """
    def __init__(self) -> None:
        """Initialize the window for the rx transforms.
        """
        super().__init__()
        self.root_layoutH = QtWidgets.QHBoxLayout()
        self.display_layout = QtWidgets.QVBoxLayout()
        self.load_layout = QtWidgets.QHBoxLayout()
        
        self.view_transforms_window = ViewTransforms()
        self.display_layout.addWidget(self.view_transforms_window)
        self.network_info = NetworkInfoWindow()
        self.setLayout(self.root_layoutH)
        self.root_layoutH.addWidget(self.network_info)
        self.display_layout.addWidget(self.view_transforms_window)
        self.root_layoutH.addLayout(self.display_layout)
    