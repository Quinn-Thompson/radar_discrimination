"""This file is used for arbitrary code execution. The method names are taken and run based on a QComboBox selection."""
import numpy as np
from numpy.typing import NDArray
from scipy import signal

def apply_fft(frame: NDArray[np.float64]):
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

def log10(frame: NDArray[np.float64]):
    return 10 * np.log10(np.abs(frame)) 