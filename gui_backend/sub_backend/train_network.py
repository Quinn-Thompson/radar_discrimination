"""Window to allow for capturing and saving data."""
from gui.sub_widgets.train_network import TrainNetwork
from gui_backend.helpers import TimeStampData, TertiaryData, PerSubPlot, Label
from gui_backend.sub_backend.view_transforms import ViewTransformsBackend, _ALLOWED_LENGTH
from gui.main_window import MainWindow
from gui.helpers import Models
import numpy as np
import torch
from numpy.typing import NDArray
from matplotlib.axes import Axes
from typing import List, Optional
from PyQt6 import QtCore, QtWidgets
from pathlib import Path
import os
from typing import Callable
from random import sample
from torch.autograd import Variable
from gui_backend.sub_backend.networks import AutoEncoder
import time
import multiprocessing as mp
from dataclasses import dataclass
from enum import Enum
from queue import Empty


model_lookup = {
    Models.AUTOENCODER.name: AutoEncoder
}

@dataclass
class PassbackData:
    timestamp_data: TimeStampData
    tertiary_data: TertiaryData

class DataEventsToHandle(Enum):
    RUN_MODEL = "RUN_MODEL"
    STOP_MODEL = "STOP_MODEL"

class Dataset(torch.utils.data.Dataset):
    """
    initialization of the labels 
    """
    def __init__(self, data_path: Path, label_path: Path, file_list: List[str], num_labels):
        self._data_path = data_path
        self._label_path = label_path
        self._file_list = file_list
        # self._num_labels = num_labels

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
        # load the input_data
        with open(f"{self._data_path}/{file}", "rb") as fd:
            input_data = (np.load(fd) + 1) / 2
        # load the label
        with open(f"{self._label_path}/{file}", "rb") as fd:
            label_data = (np.load(fd) + 1) / 2

        output_label = torch.tensor(label_data)
        return input_data, output_label

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
        
    def check_for_nn_data(self):
        try:
            passback_data: PassbackData = self.passback_queue.get_nowait()
            
            self.transforms_backend.iterate_through_each_view_tab(passback_data.timestamp_data, passback_data.tertiary_data)
        except Empty:
            pass
        
    def start_nn(self):

        data_path = self.sub_window.network_info.widgets.data_location.getInnerText()
        label_path = self.sub_window.network_info.widgets.label_location.getInnerText()
        train_val_split = int(self.sub_window.network_info.widgets.train_val_split.getInnerText())
        model = self.sub_window.network_info.widgets.model_selection.getInnerText()
        learning_rate = float(self.sub_window.network_info.widgets.learning_rate.getInnerText())
        batch_size = int(self.sub_window.network_info.widgets.batch_count.getInnerText())
        time_between_draws = float(self.sub_window.network_info.widgets.time_between_draws.getInnerText())
        epoch_count = int(self.sub_window.network_info.widgets.epoch_count.getInnerText())
        pass_in_data = PassInData(
            data_path, label_path, train_val_split, batch_size, learning_rate, model, time_between_draws, epoch_count
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
    train_val_split: int
    batch_size: int
    learning_rate: float
    model: str
    time_between_draws: float
    epoch_count: int

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

        for dirpath, dirnames, filenames in os.walk(self.pass_in_data.data_path):
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
            self.pass_in_data.data_path, self.pass_in_data.label_path, training_files, len(training_files)
        )
        dataset_val = Dataset(
            self.pass_in_data.data_path, self.pass_in_data.label_path, validation_files, len(validation_files)
        )

        dataloader_train = torch.utils.data.DataLoader(dataset_train, batch_size=self.pass_in_data.batch_size, shuffle=True, num_workers=4, pin_memory=True)
        dataloader_validation = torch.utils.data.DataLoader(dataset_val, batch_size=self.pass_in_data.batch_size, shuffle=True,  num_workers=4, pin_memory=True)

        model = model_lookup[self.pass_in_data.model]()
        model_c = model.cuda()
        
        # adam optimizer, default beta 1 and beta 2, only learning rate set
        parameters = list(model_c.parameters())
        optimizer = torch.optim.Adam(parameters, lr=self.pass_in_data.learning_rate)
        # create graph
        # test_batch, _ = next(iter(dataloader_train))
        # yhat = model_c(test_batch.float().cuda())
        # make_dot(yhat, params=dict(model_c.named_parameters())).render("rnn_torchviz", format="png")
        self.epoch_iteration(model_c, dataloader_train, dataloader_validation, optimizer)

    @staticmethod
    def operate_nn(input_image_batch, output_label_batch, model, loss_func):
        # convert image inputs to gpu
        cinput_image_batch = input_image_batch.cuda(non_blocking=True)
        coutput_label_batch = output_label_batch.cuda(non_blocking=True)
        # encode the image, get max pool indeces and skip connections
        nn_output_batch = model(cinput_image_batch)
        # calculate loss using MSE
        loss = loss_func(nn_output_batch, coutput_label_batch)

        return loss, nn_output_batch
        

    def epoch_iteration( 
        self,
        model_cuda, 
        dataloader_train: Dataset, 
        dataloader_val: Dataset,
        optimizer: torch.optim.Optimizer,
    ):
        # mean squared error loss calculation
        loss_function = torch.nn.MSELoss()

        for epoch in range(self.pass_in_data.epoch_count):
            self.current_epoch = epoch
            ####################
            # BEGIN TRAINING   #
            ####################
            model_cuda.train()
            self.train_network(dataloader_train, model_cuda, loss_function, optimizer=optimizer)
        
            # enact validation
            model_cuda.eval()
            # no gradiant activation
            with torch.no_grad():
                self.train_network(dataloader_val, model_cuda, loss_function)
            
            #cv2.imwrite('output_per_epoch/network_input_and_output_at_epoch_' + str(i+1) + '.jpeg', display_info(image_valc[0], image_n_valc[0], output[0], validation=True)*255)
            # if this is the new lowest validation loss
            # if self._graph_info['val_loss_decay'][-1] < lowest_val_loss:
            #     lowest_val_loss = self._graph_info['val_loss_decay'][-1]
            #     print(f'new minimum at epoch {i}, saved')
            #     # save the network to hard drive
            #     torch.save([model_c],'./database/model/' + file_name + '.pkl')
            # print info to user
            # append list for usage in printing graph

            # for measurement, value in measure_figure.items():
            #     value.set_data(self._graph_info['!epoch'], self._graph_info[measurement])

        
    def train_network(self, dataloader: Dataset, model_c, loss_func: Callable, optimizer = None):
        validation = False
        if optimizer is None:
            validation = True
        
        previous_draw = time.time()
        # run through each batch
        for data_index, (input_data_batch, output_label_batch) in enumerate(dataloader):
            # soemtimes loads in batch size of 16
            if input_data_batch.size()[0] == self.pass_in_data.batch_size:                
                # if there is an optimizer, IE we are training
                if not validation:
                    optimizer.zero_grad()

                loss, nn_output_batch = self.operate_nn(input_data_batch.float(), output_label_batch.float(), model_c, loss_func)
                if not validation:
                    # backwards propogation based on loss
                    loss.backward()
                    optimizer.step()

                current_time = time.time()

                if current_time - previous_draw > self.pass_in_data.time_between_draws:
                    self.draw_index += 1
                    # re dimensionalize for drawing
                    input_values = input_data_batch[:16].cpu().detach().numpy()[None, ...]
                    known_values = output_label_batch[:16].cpu().detach().numpy()[None, ...]
                    guessed_values = nn_output_batch[:16].cpu().detach().numpy()[None, ...]
                    if f"epoch {self.current_epoch}" not in self.tertiary_data.notable_events:
                        self.tertiary_data.notable_events[f"epoch {self.current_epoch}"] = self.draw_index
                    time_stamp_values = TimeStampData("data", current_time, [input_values, guessed_values, known_values])
                    self.passback_queue.put(PassbackData(time_stamp_values, self.tertiary_data))
                    previous_draw = time.time()


                # self.magnitude_difference = np.sum(self.known_values - self.guessed_values, axis=0) / np.shape(self.known_values)[0]
                # # throw data to the output in the gui
                # running_loss = self.running_exp_avg(running_loss, loss.item())
                # # track Mean squared error for each iteration
                # running_mse = self.running_exp_avg(running_mse, np.sum((self.magnitude_difference) ** 2, axis=0))
                # if we are on the nth epoch to update