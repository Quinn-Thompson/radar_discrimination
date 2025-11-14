"""This file is used for arbitrary code execution. The method names are taken and run based on a QComboBox selection."""
import numpy as np
from numpy.typing import NDArray
from scipy import signal
from typing import Dict, Any
from ifxradarsdk.fmcw.types import FmcwElementType
from gui_backend.helpers import ElementSequence

def calculate_time(current_sequence: ElementSequence, total_time: float = 0):
    if current_sequence.type == FmcwElementType.IFX_SEQ_LOOP:
        for _ in range(max(current_sequence.loop.num_repetitions, 1)):
            # if we have no next element, we want to keep track of how long we are chirping
            # otherwise, if there is, we just add the length of the loop
            if current_sequence.next_element is None:
                total_time += reconstruct_waveform(current_sequence.loop.sub_sequence, total_time)
            else:
                total_time += current_sequence.loop.repetitizon_time_s
    if current_sequence.type == FmcwElementType.IFX_SEQ_DELAY:
        total_time += current_sequence.delay.time_s
    if current_sequence.next_element is not None:
        total_time += calculate_time(current_sequence, total_time)
        
    return total_time

def reconstruct_waveform(current_sequence: ElementSequence, size: int, total_time: float, current_index: int = 0):
    if current_sequence.type == FmcwElementType.IFX_SEQ_LOOP:
        for _ in range(max(current_sequence.loop.num_repetitions, 1)):
            reconstruct_waveform(current_sequence.loop.sub_sequence, size, current_index)
            current_index += (current_sequence.loop.repetition_time_s / total_time) * size

    if current_sequence.type == FmcwElementType.IFX_SEQ_DELAY:
        current_index += (current_sequence.delay.time_s / total_time) * size

    if current_sequence.next_element is not None:
        current_index = calculate_time(current_sequence, total_time)
        
    return current_index
        

def apply_fft(frame: NDArray[np.float64], current_sequence: ElementSequence):
    num_rx_antennas, num_chirps_per_frame, num_samples_per_chirp = np.shape(frame)
    fft_output = frame.copy()
    for receiver in range(fft_output.shape[0]):
        avgs = np.average(fft_output[receiver],1).reshape(num_chirps_per_frame,1)
        fft_output[receiver] = fft_output[receiver] - avgs
        fft_output[receiver] = np.multiply(fft_output[receiver],signal.windows.blackmanharris(num_samples_per_chirp).reshape(1,num_samples_per_chirp))
        zp1 = np.pad(fft_output[receiver],((0,0),(0,num_samples_per_chirp)),'constant')
        range_fft = np.fft.fft(zp1)/num_samples_per_chirp
        range_fft = 2*range_fft[:,range(int(num_samples_per_chirp))]
        fft_output[receiver] = range_fft
    return fft_output

def log10(frame: NDArray[np.float64], current_sequence: ElementSequence):
    return 10 * np.log10(np.abs(frame)) 

def ghost(frame: NDArray[np.float64], current_sequence: ElementSequence):
    
    return frame[:, 0, :]