"""Window to allow for capturing and saving data."""
from gui.sub_widgets.train_network import TrainNetwork
from gui_backend.helpers import TimeStampData, TertiaryData, PerSubPlot, Label
from gui_backend.sub_backend.view_transforms import ViewTransformsBackend, _ALLOWED_LENGTH
from gui.main_window import MainWindow
from gui.helpers import Models, LossType
import numpy as np
import torch
from numpy.typing import NDArray
from matplotlib.axes import Axes
from typing import List, Optional
from PyQt6 import QtCore, QtWidgets
from pathlib import Path
import os
from typing import Callable, Dict
from random import sample
from torch.autograd import Variable
from gui_backend.sub_backend.networks import AutoEncoder, Network, AutoEncoderSmall, Classifier
import time
import multiprocessing as mp
from dataclasses import dataclass
from enum import Enum
from queue import Empty
import random


model_lookup: Dict[str, Network] = {
    Models.AUTOENCODER.name: AutoEncoder,
    Models.SMALLAUTOENCODER.name: AutoEncoderSmall,
    Models.CLASSIFIER.name: Classifier,
}

loss_lookup = {
    LossType.MSE.name: torch.nn.MSELoss(),
    LossType.MAE.name: torch.nn.L1Loss(),
    LossType.CEL.name: torch.nn.CrossEntropyLoss(),
}

@dataclass
class PassbackData:
    timestamp_data: TimeStampData
    tertiary_data: TertiaryData

class DataEventsToHandle(Enum):
    RUN_MODEL = "RUN_MODEL"
    STOP_MODEL = "STOP_MODEL"

label_map = {
    "5860Up-0-CornerBlanket": 0,
    "5860Up-0-FlatBlanket": 0,
    "5860Up-0-CornerCard": 1,
    "5860Up-0-FlatCard": 1,
    "5860Up-0-CornerFoil": 2,
    "5860Up-0-FlatFoil": 2,
    "5860Up-0-CornerWood": 3,
    "5860Up-0-FlatWood": 3,
    "5860Up-0-Disk": 2,
    "5860Up-0-Grill": 2,
    "5860Up-0-Oscope": 2,
    "5860Up-0-Foam": 4,
    "5860Up-0-Nothing": 5,   
}

class Dataset(torch.utils.data.Dataset):
    """
    initialization of the labels 
    """
    def __init__(self, data_path: Path, file_list: List[str], label_path: Optional[Path] = None, noise_path: Optional[Path] = None, label_map: Optional[Dict[str, int]] = None):
        self._data_path = data_path
        self._label_path = label_path
        self._file_list = file_list
        self._noise_path = noise_path
        self._noise_contents = os.listdir(noise_path)
        self._label_lookup = label_map
        if self._label_lookup is not None:
            self._num_labels = max(self._label_lookup.values()) + 1

    """
    gets the length of the folder
    """
    def __len__(self):
        return len(self._file_list)

    """
    gets the item from the hard drive
    """
    def __getitem__(self, index: int):
        # Select sample
        file = self._file_list[index]
        if self._noise_path is not None:
            with open(f"{self._noise_path}/{random.choice(self._noise_contents)}", "rb") as fd:
                noise = (np.load(fd) + 1) / 2
        
        # load the input_data
        with open(f"{self._data_path}/{file}", "rb") as fd:
            input_data = (np.load(fd) + 1) / 2
            
        if self._noise_path is not None:
            input_data = (input_data - noise) + 0.5
            
        if self._label_path is not None:
            # load the label
            with open(f"{self._label_path}/{file}", "rb") as fd:
                label_data = (np.load(fd) + 1) / 2
        else:
            label_data = input_data


        if not self._label_lookup or self._label_path is not None:
            output_label = torch.tensor(label_data)
            return input_data, output_label
        else:
            label = os.path.normpath(file).split(os.sep)[0]
            output = torch.nn.functional.one_hot(torch.tensor(self._label_lookup[label], dtype=torch.long), num_classes=self._num_labels)
            return input_data, output
            

class TrainBackend(QtCore.QObject):
    """The backend operations for the capturing window."""
    
    def __init__(self, main_window: MainWindow, sub_window: TrainNetwork):
        """Initialize the elements and events for the capture window.
        
        Args:
            main_window: The main gui window.
            sub_window: The window this backend is supporting.
            data_handler: The logic for getting data from another thread.
        """
        super().__init__()
        
        self.main_window = main_window
        self.sub_window = sub_window
        self.transforms_backend = ViewTransformsBackend(
            self.main_window, 
            self.sub_window.view_transforms_window,
            self.stop_nn,
            None
        )
        self.pass_in_queue = mp.Queue()
        self.event_queue = mp.Queue()
        self.passback_queue = mp.Queue()
        self.data_process = mp.Process(
            target=nn_operation_loop, 
            args=(self.event_queue, self.pass_in_queue, self.passback_queue)
        )
        self.data_process.start()
        
        self.sub_window.network_info.widgets.data_file_explorer.clicked.connect(self.find_data_location)
        self.sub_window.network_info.widgets.label_file_explorer.clicked.connect(self.find_label_location)
        self.sub_window.network_info.widgets.noise_file_explorer.clicked.connect(self.find_noise_location)
        self.sub_window.network_info.widgets.run_button.clicked.connect(self.start_nn)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_for_nn_data)

    def find_data_location(self):
        """Use the file explorer to determine where to load the data from."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.main_window, 
            "Select Folder", 
            "" 
        )
        self.sub_window.network_info.widgets.data_location.setInnerText(folder)
        
    def find_label_location(self):
        """Use the file explorer to determine where to load the data from."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.main_window, 
            "Select Folder", 
            "" 
        )
        self.sub_window.network_info.widgets.label_location.setInnerText(folder)
        
    def find_noise_location(self):
        """Use the file explorer to determine where to load the data from."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.main_window, 
            "Select Folder", 
            "" 
        )
        self.sub_window.network_info.widgets.noise_location.setInnerText(folder)
        
        
    def check_for_nn_data(self):
        try:
            passback_data: PassbackData = self.passback_queue.get_nowait()
            
            self.transforms_backend.iterate_through_each_view_tab(passback_data.timestamp_data, passback_data.tertiary_data)
        except Empty:
            pass
        
    def start_nn(self):

        data_path = self.sub_window.network_info.widgets.data_location.getInnerText()
        label_path = self.sub_window.network_info.widgets.label_location.getInnerText()
        noise_path = self.sub_window.network_info.widgets.noise_location.getInnerText()
        if not noise_path:
            noise_path = None
        train_val_split = int(self.sub_window.network_info.widgets.train_val_split.getInnerText())
        model = self.sub_window.network_info.widgets.model_selection.getInnerText()
        learning_rate = float(self.sub_window.network_info.widgets.learning_rate.getInnerText())
        batch_size = int(self.sub_window.network_info.widgets.batch_count.getInnerText())
        time_between_draws = float(self.sub_window.network_info.widgets.time_between_draws.getInnerText())
        epoch_count = int(self.sub_window.network_info.widgets.epoch_count.getInnerText())
        loss_type = self.sub_window.network_info.widgets.loss_type.getInnerText()
        pass_in_data = PassInData(
            data_path, label_path, noise_path, train_val_split, batch_size, learning_rate, model, time_between_draws, epoch_count, loss_type
        )
        
        self.pass_in_queue.put(pass_in_data)
        self.event_queue.put(DataEventsToHandle.RUN_MODEL)
        
        self.timer.start(int(time_between_draws*1.0e3))

    def stop_nn(self):
        self.event_queue.put(DataEventsToHandle.STOP_MODEL)


@dataclass
class PassInData:
    data_path: str
    label_path: str
    noise_path: str
    train_val_split: int
    batch_size: int
    learning_rate: float
    model: str
    time_between_draws: float
    epoch_count: int
    loss_type: str

def nn_operation_loop(event_queue: mp.Queue, pass_in_queue: mp.Queue, passback_queue: mp.Queue):
    while True:
        try:
            event = event_queue.get(timeout=0.05)
            if event == DataEventsToHandle.RUN_MODEL:
                pass_in_data: PassInData = pass_in_queue.get(timeout=0.05)
                train_network = TrainNetworks(pass_in_data, passback_queue)
                
                train_network.train_and_eval()
            if event == DataEventsToHandle.STOP_MODEL:
                print("stop")
        except Empty:
            pass

class TrainNetworks():
    def __init__(self, pass_in_data: PassInData, passback_queue: mp.Queue):
        self.tertiary_data = TertiaryData()
        
        self.tertiary_data.graph_info.tab_names = ["Network Input", "Network Output", "Target Output"]
        self.tertiary_data.graph_info.per_subplot_info = [PerSubPlot()]
        self.tertiary_data.graph_info.per_subplot_info[0].sub_plot_name = "Network Data"
        self.tertiary_data.graph_info.per_subplot_info[0].x_axis_label = Label("Short Time", "Bin(s)")
        self.passback_queue = passback_queue
        self.pass_in_data = pass_in_data
        self.draw_index = 0
        self.current_epoch = 0
        
    
    def train_and_eval(self):

        # check if torch is running on a gpu
        avail = torch.cuda.is_available()
        if (avail):
            print(torch.cuda.get_device_name(0))

        files = []
        labels = []
        for dirpath, dirnames, filenames in os.walk(self.pass_in_data.data_path):
            if self.pass_in_data.model == Models.CLASSIFIER.name and dirnames:
                for dir_name in dirnames:
                    labels.append(dir_name)
                    
            for file_name in filenames:
                relative_directory = os.path.relpath(dirpath, self.pass_in_data.data_path)
                relative_path = os.path.join(relative_directory, file_name)
                files.append(relative_path)
            # shuffle the file names for splitting
                
        file_array_shuffle = sample(files, len(files))
        # sys.stdout = open('stdout.txt', 'w')
                
        # split the validation and training files
        training_files=file_array_shuffle[:int(len(file_array_shuffle)*self.pass_in_data.train_val_split*0.01)]
        validation_files=file_array_shuffle[int(len(file_array_shuffle)*self.pass_in_data.train_val_split*0.01):]
        
        dataset_train = Dataset(
            self.pass_in_data.data_path, training_files, noise_path=self.pass_in_data.noise_path, label_map=None
        )
        dataset_val = Dataset(
            self.pass_in_data.data_path, validation_files, noise_path=self.pass_in_data.noise_path, label_map=None
        )

        dataloader_train = torch.utils.data.DataLoader(dataset_train, batch_size=self.pass_in_data.batch_size, shuffle=True, num_workers=4, pin_memory=True)
        dataloader_validation = torch.utils.data.DataLoader(dataset_val, batch_size=self.pass_in_data.batch_size, shuffle=True,  num_workers=4, pin_memory=True)

        model = model_lookup[self.pass_in_data.model]()
        model_cuda = model.cuda()
        
        # adam optimizer, default beta 1 and beta 2, only learning rate set
        parameters = list(model_cuda.parameters())
        optimizer = torch.optim.Adam(parameters, lr=self.pass_in_data.learning_rate)
        # create graph
        # test_batch, _ = next(iter(dataloader_train))
        # yhat = model_c(test_batch.float().cuda())
        # make_dot(yhat, params=dict(model_c.named_parameters())).render("rnn_torchviz", format="png")
        self.epoch_iteration(model_cuda, dataloader_train, dataloader_validation, optimizer)

    @staticmethod
    def operate_nn(input_image_batch, output_label_batch, model, loss_function):
        # convert image inputs to gpu
        cinput_image_batch = input_image_batch.cuda(non_blocking=True)
        coutput_label_batch = output_label_batch.cuda(non_blocking=True)
        # encode the image, get max pool indeces and skip connections
        nn_output_batch = model(cinput_image_batch)
        # calculate loss using MSE
        loss = loss_function(nn_output_batch, coutput_label_batch)

        return loss, nn_output_batch
        

    def epoch_iteration( 
        self,
        model_cuda: Network, 
        dataloader_train: Dataset, 
        dataloader_val: Dataset,
        optimizer: torch.optim.Optimizer,
    ):
        # mean squared error loss calculation
        lowest_val_loss = float("inf")
        for epoch in range(self.pass_in_data.epoch_count):
            print(f"Epoch: {epoch}")
            self.current_epoch = epoch
            ####################
            # BEGIN TRAINING   #
            ####################
            model_cuda.train()
            _, t_input_data_batch, t_output_data_batch, t_output_label_batch = self.train_network(dataloader_train, model_cuda, optimizer=optimizer)
        
            # enact validation
            model_cuda.eval()
            # no gradiant activation
            with torch.no_grad():
                validation_loss, v_input_data_batch, v_output_data_batch, v_output_label_batch = self.train_network(dataloader_val, model_cuda)
            
            input_data_batch = torch.empty(((2,) + v_input_data_batch.shape))
            input_data_batch[0] = t_input_data_batch
            input_data_batch[1] = v_input_data_batch
            output_data_batch = torch.empty(((2,) + v_output_data_batch.shape))
            output_data_batch[0] = t_output_data_batch
            output_data_batch[1] = v_output_data_batch
            output_label_batch = torch.empty(((2,) + v_output_label_batch.shape))
            output_label_batch[0] = t_output_label_batch
            output_label_batch[1] = v_output_label_batch
            
            self.draw_to_screen(model_cuda, 0.0, input_data_batch, output_data_batch, output_label_batch)
            # if this is the new lowest validation loss
            if validation_loss < lowest_val_loss:
                print(f'new minimum at epoch {epoch}, saved')
                # save the network to hard drive
                torch.save(model_cuda.state_dict(), f"./models/{model_cuda}.pth")
                # fresh_model = model_lookup[self.pass_in_data.model]().cuda()
                # fresh_model.load_state_dict(torch.load(f"./models/{model_cuda}.pth"))
                # fresh_model.eval()
                # output = fresh_model(input_data_batch.float().cuda(non_blocking=True))
                # print(torch.max(torch.abs(output - output_label_batch)))

        
    def train_network(self, dataloader: Dataset, model_cuda: Network, optimizer = None):

        loss_function = loss_lookup[self.pass_in_data.loss_type]
        previous_draw = time.time()
        # run through each batch
        for data_index, (input_data_batch, output_label_batch) in enumerate(dataloader):
            # soemtimes loads in batch size of 16
            if input_data_batch.size()[0] == self.pass_in_data.batch_size:
                last_input = input_data_batch
                last_output = output_label_batch
                # if there is an optimizer, IE we are training
                if optimizer is not None:
                    optimizer.zero_grad()

                loss, nn_output_batch = self.operate_nn(input_data_batch.float(), output_label_batch.float(), model_cuda, loss_function)
                if optimizer is not None:
                    # backwards propogation based on loss
                    loss.backward()
                    optimizer.step()
        
        return loss, last_input, last_output, nn_output_batch

    def draw_to_screen(
        self, 
        model_cuda: Network, 
        previous_draw: float, 
        input_data_batch: torch.Tensor, 
        output_label_batch: torch.Tensor, 
        nn_output_batch: torch.Tensor
    ):
        current_time = time.time()

        if current_time - previous_draw > self.pass_in_data.time_between_draws:
            self.draw_index += 1
            # re dimensionalize for drawing
            input_values = input_data_batch.cpu().detach().numpy()
            known_values = output_label_batch.cpu().detach().numpy()
            
            guessed_values = nn_output_batch.cpu().detach().numpy()
            
            if f"epoch {self.current_epoch}" not in self.tertiary_data.notable_events:
                self.tertiary_data.notable_events[f"epoch {self.current_epoch}"] = self.draw_index
            
            tab_names, pertinant_info = model_cuda.return_pertinent_information()
            to_draw = [input_values, guessed_values, known_values]
            if tab_names is not None and pertinant_info is not None:
                self.tertiary_data.graph_info.tab_names.extend(tab_names)
                to_draw.extend([info_gpu.cpu().detach().numpy()[None, ...] for info_gpu in pertinant_info])
            
            time_stamp_values = TimeStampData("data", current_time, to_draw)
            self.passback_queue.put(PassbackData(time_stamp_values, self.tertiary_data))
            return True
        return False