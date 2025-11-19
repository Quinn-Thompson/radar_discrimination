"""This file is used for arbitrary code execution. The method names are taken and run based on a QComboBox selection.

The methods without _'s at the beginning will be added to the method list to run.

These methods will be passed a list of every frame (one for each chirp sequence) and a list of objects 
containing the start and end frequencies and durations of every chirp and their respective sequence

This MUST be a shape list(np.array(shape=(X, Y, Z)))
"""
import numpy as np
from numpy.typing import NDArray
from scipy import signal
from gui_backend.helpers import CreateLine
from typing import List

def _recreate_chirp(chirp_list: List[CreateLine], allowed_size: int):
    total_duration = 0
    for chirp in chirp_list:
        total_duration += chirp.duration
    
    return np.concatenate([chirp.enact_movement(allowed_size, total_duration) for chirp in chirp_list])

def _get_chirp_waveforms(chirp_list: List[CreateLine], allowed_size: List[int]) -> List[NDArray[np.float64]]:
    seen_chirps = []
    unique_chirps = []
    for chirp_index in range(len(chirp_list)):
        if chirp_list[chirp_index].chirp_sequence not in seen_chirps:
            total_duration = chirp_list[chirp_index].duration + chirp_list[chirp_index+1].duration
            first_section = chirp_list[chirp_index].enact_movement(allowed_size[chirp_list[chirp_index].chirp_sequence], total_duration)
            section_section = chirp_list[chirp_index+1].enact_movement(allowed_size[chirp_list[chirp_index].chirp_sequence], total_duration)
            unique_chirps.append(np.concatenate((first_section, section_section)))
            seen_chirps.append(chirp_list[chirp_index].chirp_sequence)
    return unique_chirps

def apply_fft(frame_list: List[NDArray[np.float64]], chirp_list: List[CreateLine]):
    fft_outputs = []
    for frame in frame_list:
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
        fft_outputs.append(fft_output)
    return fft_outputs

def chirp_fft(frame_list: List[NDArray[np.float64]], chirp_list: List[CreateLine]):
    frame_chirp_ffts = []
    for frame in frame_list:
        frame_chirp_ffts.append(np.fft.fft(frame, axis=2))
    return frame_chirp_ffts

def fft(frame_list: List[NDArray[np.float64]], chirp_list: List[CreateLine]):
    frame_ffts = []
    for frame in frame_list:
        frame_ffts.append(np.fft.fft(frame, axis=1))
    return frame_ffts

def cir(frame_list: List[NDArray[np.float64]], chirp_list: List[CreateLine]):
    sample_durations = [len(frame[0][0]) for frame in frame_list]
    reconstructed_chirp_list = _get_chirp_waveforms(chirp_list, sample_durations)
    
    frame_cirs = []

    for frame, chirp in zip(frame_list, reconstructed_chirp_list):
        chirp_time = np.fft.ifft(chirp).conj()[::-1]
        match_filter = chirp_time / np.max(chirp_time)
        cir = np.zeros_like(frame, dtype=np.complex128)
        for receiver in range(frame.shape[0]):
            for chirp in range(frame.shape[1]):
                cir[receiver, chirp, :] = np.convolve(frame[receiver, chirp, :], match_filter, mode="same")
        frame_cirs.append(cir)
    return frame_cirs

# def averaged_receiver()