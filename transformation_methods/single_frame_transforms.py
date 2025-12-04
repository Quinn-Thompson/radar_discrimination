"""This file is used for arbitrary code execution. The method names are taken and run based on a QComboBox selection.

The methods without t_ at teh beginning will not be seen

These methods will be passed a list of every frame (one for each chirp sequence) and a list of objects 
containing the start and end frequencies and durations of every chirp and their respective sequence.

The arguments are passed in as either kwargs or args, if args because of distinct method argument names, it is the frames first then the chirp list.
otherwise it will just be assigned to frame_list and chirp_info_list.

The return MUST be of type list(np.array(X)), otherwise a popup will appear.

Currently line plots can handle 3 axis, 2 axis and 1 axis data.
color meshes should be able to handle 3 axis and 2 axis data.
"""
import numpy as np
from numpy.typing import NDArray
from scipy import signal
from gui_backend.helpers import CreateLine, TertiaryData, Label
from typing import List
from scipy.signal import butter, lfilter
from gui_backend.sub_backend.networks import SmallAutoEncoder
import torch
from sklearn.manifold import TSNE

class RecreateChirp():
    def __init__(self, chirp_info_list: List[CreateLine], allowed_size: int):
        """Initialize the chirp recreation methods.

        Args:
            chirp_info_list: The list of information to recreate a chirp.
            allowed_size: The size the chirp is allowed to be.
        """
        self.chirp_info_list = chirp_info_list
        self.allowed_size = allowed_size
    
    def recreate_whole_chirp(self):
        
        total_duration = 0
        for chirp in self.chirp_info_list:
            total_duration += chirp.duration
        
        return np.concatenate(
            [chirp.enact_movement(self.allowed_size, total_duration) for chirp in self.chirp_info_list]
        )

    def recreate_single_chirp(self) -> List[NDArray[np.float64]]:
        longest_chirp = 0
        for chirp_index in range(0, len(self.chirp_info_list), 2):
            current_chirp_duration = self.chirp_info_list[chirp_index].duration + self.chirp_info_list[chirp_index+1].duration
            if current_chirp_duration > longest_chirp:
                longest_chirp = current_chirp_duration
        
        
        seen_chirps = []
        unique_chirps = []
        for chirp_index in range(0, len(self.chirp_info_list), 2):
            if self.chirp_info_list[chirp_index].chirp_sequence not in seen_chirps:
                adc_section = self.chirp_info_list[chirp_index].enact_movement(
                    self.allowed_size, longest_chirp
                )
                chirp_section = self.chirp_info_list[chirp_index+1].enact_movement(
                    self.allowed_size, longest_chirp, end_point=True
                )
                unique_chirps.append(np.concatenate((adc_section, chirp_section)))
                seen_chirps.append(self.chirp_info_list[chirp_index].chirp_sequence)
        return unique_chirps

def t_apply_fft(frame_list: List[NDArray[np.float64]]):
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

def t_chirp_fft(frame_list: List[NDArray[np.float64]]):
    frame_chirp_ffts = []
    for frame in frame_list:
        frame_chirp_ffts.append(np.fft.fft(frame, axis=2))
    return frame_chirp_ffts

def t_fft(frame_list: List[NDArray[np.float64]]):
    frame_ffts = []
    for frame in frame_list:
        frame_ffts.append(np.fft.fft(frame, axis=1))
    return frame_ffts

def t_cir(frame_list: List[NDArray[np.float64]], chirp_info_list: List[CreateLine]):
    sample_durations = [len(frame[0][0]) for frame in frame_list]
    chirp_recreator = RecreateChirp(chirp_info_list, max(sample_durations))
    reconstructed_chirp_info_list = chirp_recreator.recreate_single_chirp()
    
    frame_cirs = []

    for frame, chirp in zip(frame_list, reconstructed_chirp_info_list):
        chirp_time = np.fft.ifft(chirp).conj()[::-1]
        match_filter = chirp_time / np.max(chirp_time)
        cir = np.zeros_like(frame, dtype=np.complex128)
        for receiver in range(frame.shape[0]):
            for chirp in range(frame.shape[1]):
                cir[receiver, chirp, :] = np.convolve(frame[receiver, chirp, :], match_filter, mode="same")
        frame_cirs.append(cir)
    return frame_cirs

def t_collapse_list(frame_list: List[NDArray[np.float64]]):
    return [np.concatenate([chirp for chirp in frame_list])]

def t_view_sent_signal(chirp_info_list: List[CreateLine]):
    chirp_recreator = RecreateChirp(chirp_info_list, 60)
    return chirp_recreator.recreate_single_chirp()

def t_beam_form(frame_list: List[NDArray[np.float64]]):
    averaged = [np.mean(frame, axis=0,keepdims=True) for frame in frame_list]
    return averaged

def t_view_text(chirp_info_list: List[CreateLine]):
    my_text = [["test11", "test12"], ["test21", "test22"]]
    return [np.array(my_text)]

def t_difference(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    z_axis_label = "Differential"
    tertiary_data.graph_info.y_axis_label = None
    tertiary_data.graph_info.z_axis_label = Label(z_axis_label, tertiary_data.graph_info.z_axis_label.units)
    tertiary_data.graph_info.tab_names = ["Differential Average"]
    differential = frame_list[1] - frame_list[2]
    return [differential], tertiary_data


def t_avg_difference(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):

    z_axis_label = f"Averaged {tertiary_data.graph_info.z_axis_label.name} Along {tertiary_data.graph_info.y_axis_label.name}"
    tertiary_data.graph_info.y_axis_label = None
    tertiary_data.graph_info.z_axis_label = Label(z_axis_label, tertiary_data.graph_info.z_axis_label.units)
    tertiary_data.graph_info.tab_names = ["Differential Average"]
    differential = np.array(np.average(frame_list[1] - frame_list[2]))[None]
    return [differential], tertiary_data

def t_sqrt_avg_difference(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):

    average_differential, tertiary_data = t_avg_difference(frame_list, tertiary_data)

    tertiary_data.graph_info.tab_names = ["Sqrt Differential Average"]
    return [np.sqrt(np.abs(frame)) for frame in average_differential], tertiary_data


def butter_lowpass(cutoff, fs, order=5):
    b, a = butter(order, cutoff / (0.5 * fs), btype='low')
    return b, a

def apply_lowpass(signal, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order)
    return lfilter(b, a, signal)



def simulate_fmcw_return(tx_chirp, fs, target_range, attenuation=0.8):
    c = 3e8
    tau = 2 * target_range / c          # round-trip delay
    delay_samples = int(round(tau * fs))  # sample delay
    
    # 1. Create delayed copy
    rx = np.zeros_like(tx_chirp)
    if delay_samples < len(tx_chirp):
        rx[delay_samples:] = tx_chirp[:-delay_samples] * attenuation

    # 2. Mixing (TX × RX)
    mixed = tx_chirp * rx

    # 3. LPF 500 kHz
    mixed = apply_lowpass(mixed, 500e3, fs, order=6)

    # 4. LPF 20 kHz
    baseband = apply_lowpass(mixed, 20e3, fs, order=6)

    return baseband


def t_simulated_return(chirp_info_list: List[CreateLine]):
    sample_durations = [len(chirp.num_samples) for chirp in chirp_info_list]
    radius_to_target = 7
    speed_of_light = 3.0e8
    chirp_recreator = RecreateChirp(chirp_info_list, max(sample_durations))
    fs = chirp_info_list[0].sampling_rate

    simulated = []
    for tx_chirp in chirp_recreator.recreate_single_chirp():
        out = simulate_fmcw_return(tx_chirp, fs, radius_to_target)
        simulated.append(out)
    return simulated
# for chirp in chirp_recreator:
#     if_signal = 2 * 

def t_go_thru_network(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    collapsed_data = t_beam_form(frame_list)
     
    fresh_model = SmallAutoEncoder().cuda()
    fresh_model.load_state_dict(torch.load("./models/best_small_autoencoder_2.pth"))
    fresh_model.eval()
    output = fresh_model(torch.from_numpy((collapsed_data[0][0][:16]+ 1) / 2).float().cuda(non_blocking=True))
    
    return [output.cpu().detach().numpy()]

def t_reduced_dim(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    collapsed_data = t_beam_form([np.concatenate([frame for frame in frame_list], axis=2)])
    
    fresh_model = SmallAutoEncoder().cuda()
    fresh_model.load_state_dict(torch.load("./models/best_small_autoencoder_2.pth"))
    fresh_model.eval()
    _ = fresh_model(torch.from_numpy((collapsed_data[0][0][:16]+ 1) / 2).float().cuda(non_blocking=True))
    
    return [fresh_model.reduced_dimensions.output.cpu().detach().numpy()]

tsne = TSNE(n_components=2, verbose=1, perplexity=30, n_iter=300)
 
def t_sne_reduced_dim(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    reduced_dim = t_reduced_dim(frame_list, tertiary_data)
    tsne_results = tsne.fit_transform(reduced_dim[0])
    return [tsne_results]