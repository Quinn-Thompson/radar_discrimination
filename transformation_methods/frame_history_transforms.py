import numpy as np
from numpy.typing import NDArray
from scipy import signal
from gui_backend.helpers import CreateLine, TertiaryData, Label
from typing import List
import hdbscan
from scipy.signal import find_peaks
from sklearn.preprocessing import StandardScaler

_NUM_BINS = 300

def t_maintain(frame_history: List[List[NDArray[np.float64]]], tertiary_data: TertiaryData) -> List[NDArray[np.float64]]:
    history_length = len(frame_history)
    new_output = []
    for first_frames in frame_history[0]:
        new_output.append(np.empty((first_frames.shape[:-1] + (first_frames.shape[-1] * history_length, ))))
    for chirp in range(len(new_output)):
        for frame_index, frame in enumerate(frame_history):
            new_output[chirp][..., frame_index*first_frames.shape[-1]:(frame_index+1)*first_frames.shape[-1]] = frame[chirp][..., :]
    for tab_index, tab_name in enumerate(tertiary_data.graph_info.tab_names):
        tertiary_data.graph_info.tab_names[tab_index] = tab_name + "History"
    return new_output, tertiary_data

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
            
        