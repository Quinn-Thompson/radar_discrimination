import numpy as np
from numpy.typing import NDArray
from scipy import signal
from gui_backend.helpers import CreateLine, TertiaryData, Label, PerSubPlot
from typing import List
from sklearn.decomposition  import PCA
import umap
import colorsys
from scipy.spatial.distance import cdist

_NUM_BINS = 300
_RATIO = 0.618



def t_maintain(frame_history: List[List[NDArray[np.float64]]], tertiary_data: List[TertiaryData]) -> List[NDArray[np.float64]]:
    last_tertiary = tertiary_data[-1]
    history_length = len(frame_history)
    new_output = []
    for first_frames in frame_history[0]:
        new_output.append(np.empty((first_frames.shape + (history_length, ))))
    for chirp in range(len(new_output)):
        for frame_index, frame in enumerate(frame_history):
            new_output[chirp][..., frame_index] = frame[chirp]

    
    for tab_index, tab_name in enumerate(last_tertiary.graph_info.tab_names):
        last_tertiary.graph_info.tab_names[tab_index] = tab_name + "History"
    return new_output, last_tertiary

def concatenate_second_axis(frame_history: List[List[NDArray[np.float64]]]) -> List[NDArray[np.float64]]:
    concatenated_data = [np.empty((chirp_sequence_frame.shape[0], len(frame_history) * chirp_sequence_frame.shape[1], chirp_sequence_frame.shape[2])) for chirp_sequence_frame in frame_history[0]]
    for transformed_frame_index, transformed_frame_list in enumerate(frame_history):
        # for each chirp sequence
        for chirp_sequence_frame_index, chirp_sequence_frame in enumerate(transformed_frame_list):
            starting_index = transformed_frame_index * chirp_sequence_frame.shape[1]
            ending_index = (transformed_frame_index + 1) * chirp_sequence_frame.shape[1]
            concatenated_data[chirp_sequence_frame_index][:, starting_index:ending_index, :] = chirp_sequence_frame
    return concatenated_data


def t_embeddings(frame_history: List[List[NDArray[np.float64]]], tertiary_data: List[TertiaryData]) -> List[NDArray[np.float64]]:
    last_tertiary = tertiary_data[-1]
    last_tertiary.fundamentals["color_map"] = {}
    color_index = 1
    color_list = []
    concatenated_data = concatenate_second_axis(frame_history)
    chirp_reduced_dim = []
    
    for concatenated_chirp in concatenated_data:
        embeddings = np.empty((concatenated_chirp.shape[0], concatenated_chirp.shape[1], concatenated_chirp.shape[1]))
        for receiver_index, concatenated_receiver in enumerate(concatenated_chirp):
            embeddings[receiver_index] = cdist(concatenated_receiver, concatenated_receiver)
        chirp_reduced_dim.append(embeddings)
  
    
    for tab_index, tab_name in enumerate(last_tertiary.graph_info.tab_names):
        last_tertiary.graph_info.tab_names[tab_index] = tab_name + "History"
    return chirp_reduced_dim, last_tertiary

pca = PCA(n_components=2)   # reduce to 2 dimensions

color_map = {
    "5860Up-0-CornerBlanket": (255, 0, 0),
    "5860Up-0-FlatBlanket": (170, 0, 0),
    "5860Up-0-CornerCard": (0, 255, 0),
    "5860Up-0-FlatCard": (0, 170, 0),
    "5860Up-0-CornerFoil": (0, 0, 255),
    "5860Up-0-FlatFoil": (0, 0, 170),
    "5860Up-0-CornerWood": (0, 255, 255),
    "5860Up-0-FlatWood": (0, 170, 170),
    # "5860Up-0-Disk": (0, 0, 140),
    # "5860Up-0-Grill": (0, 0, 200),
    # "5860Up-0-Oscope": (0, 0, 100),
    # "5860Up-0-Foam": (255, 0, 255),
    # "5860Up-0-Nothing": (255, 255, 255),   
}

def t_pca_scatter(frame_history: List[List[NDArray[np.float64]]], tertiary_data: List[TertiaryData]) -> List[NDArray[np.float64]]:
    last_tertiary = tertiary_data[-1]
    last_tertiary.fundamentals["color_map"] = {}
    color_index = 1
    color_list = []
    concatenated_data = concatenate_second_axis(frame_history)
    chirp_reduced_dim = []
    
    for concatenated_chirp in concatenated_data:
        reduced_dimensionality = np.empty((concatenated_chirp.shape[:-1] + (2, )))
        for receiver_index, concatenated_receiver in enumerate(concatenated_chirp):
            reduced_dimensionality[receiver_index] = pca.fit_transform(concatenated_receiver)
        chirp_reduced_dim.append(reduced_dimensionality)
  
    for tertiary in tertiary_data:
        if tertiary.fundamentals["label"] not in last_tertiary.fundamentals["color_map"]:
            red, green, blue = colorsys.hsv_to_rgb((color_index * _RATIO) % 1, 1, 1)
            color_index += 1
            last_tertiary.fundamentals["color_map"][tertiary.fundamentals["label"]] = (int(red*255), int(green*255), int(blue*255))
        color_list.append(last_tertiary.fundamentals["color_map"][tertiary.fundamentals["label"]])
    last_tertiary.fundamentals["color_list"] = color_list
    
    for tab_index, tab_name in enumerate(last_tertiary.graph_info.tab_names):
        last_tertiary.graph_info.tab_names[tab_index] = tab_name + "History"
    return chirp_reduced_dim, last_tertiary

def t_pca_scatter_forced(frame_history: List[List[NDArray[np.float64]]], tertiary_data: List[TertiaryData]) -> List[NDArray[np.float64]]:
    last_tertiary = tertiary_data[-1]
    last_tertiary.fundamentals["color_map"] = color_map
    color_index = 1
    color_list = []
    concatenated_data = concatenate_second_axis(frame_history)
    chirp_reduced_dim = []
    
    for concatenated_chirp in concatenated_data:
        reduced_dimensionality = np.empty((concatenated_chirp.shape[:-1] + (2, )))
        for receiver_index, concatenated_receiver in enumerate(concatenated_chirp):
            reduced_dimensionality[receiver_index] = pca.fit_transform(concatenated_receiver)
        chirp_reduced_dim.append(reduced_dimensionality)
  
    for tertiary in tertiary_data:
        color_list.append(last_tertiary.fundamentals["color_map"][tertiary.fundamentals["label"]])
    last_tertiary.fundamentals["color_list"] = color_list
    last_tertiary.graph_info.per_subplot_info = [PerSubPlot()]
    last_tertiary.graph_info.per_subplot_info[0].sub_plot_name = "Latent Space Scatter Plot"
    last_tertiary.graph_info.per_subplot_info[0].x_axis_label = Label("First Principal Component", None)
    last_tertiary.graph_info.y_axis_label = Label("Second Principal Component", None)
    for tab_index, tab_name in enumerate(last_tertiary.graph_info.tab_names):
        last_tertiary.graph_info.tab_names[tab_index] = tab_name + "History"
    return chirp_reduced_dim, last_tertiary



def t_average_removed(frame_history: List[List[NDArray[np.float64]]], tertiary_data: TertiaryData) -> List[NDArray[np.float64]]:
    averaged_outputs = [np.zeros_like(frame_history[0][chirp]) for chirp in len(frame_history[0])]
    for frame in frame_history:
        for averaged_output in averaged_outputs:
            averaged_output += frame
    
    for averaged_output in averaged_outputs:
        averaged_output /= len(frame_history)
        
        
    return averaged_outputs, tertiary_data


def t_cluster(frame_history: List[List[NDArray[np.float64]]]) -> List[NDArray[np.float64]]:
    # create a list (for each different chirp sequence) for 
    concatenated_data = [np.empty((chirp_sequence_frame.shape[0], len(frame_history) * chirp_sequence_frame.shape[1], 2)) for chirp_sequence_frame in frame_history[0]]
    # scalar = StandardScaler()
    # clusters = hdbscan.HDBSCAN(min_cluster_size=2)
    # scalar = StandardScaler()
    # for each data point
    for transformed_frame_list_index, transformed_frame_list in enumerate(frame_history):
        # for each chirp sequence
        for chirp_sequence_frame_index, chirp_sequence_frame in enumerate(transformed_frame_list):
            
            to_label = np.empty((2, chirp_sequence_frame.shape[0], chirp_sequence_frame.shape[1]))
            rms = np.sqrt(np.mean(chirp_sequence_frame**2, axis=2))
            pam = np.mean(chirp_sequence_frame, axis=2) / np.std(chirp_sequence_frame, axis=2)
            
            to_label[0] = rms
            to_label[1] = pam
            to_label = np.moveaxis(to_label, 0, 2)
            start_point = transformed_frame_list_index * chirp_sequence_frame.shape[1]
            end_point = (transformed_frame_list_index + 1) * chirp_sequence_frame.shape[1]
            concatenated_data[chirp_sequence_frame_index][:, start_point:end_point, :] = to_label
    
    # cluster_info = [np.empty((chirp_sequence_frame.shape[0], chirp_sequence_frame.shape[1])) for chirp_sequence_frame in concatenated_data]
    histograms = [np.empty((chirp_sequence_frame.shape[0], _NUM_BINS, _NUM_BINS)) for chirp_sequence_frame in concatenated_data]
    for chirp_sequence_frame_index, chirp_sequence_frame in enumerate(concatenated_data):
        for receiver_index, receiver in enumerate(chirp_sequence_frame):
            # cluster_info[chirp_sequence_frame_index][receiver_index] = clusters.fit_predict(scalar.fit_transform(receiver))
            histogram, _, _ = np.histogram2d(receiver[:, 0], receiver[:, 1], bins=_NUM_BINS)
            histograms[chirp_sequence_frame_index][receiver_index] = histogram
    
    
    return histograms
            
        