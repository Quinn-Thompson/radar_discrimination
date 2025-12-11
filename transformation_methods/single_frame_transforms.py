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
from gui_backend.helpers import CreateLine, TertiaryData, Label, PerSubPlot
from typing import List
from scipy.signal import butter, sosfilt, filtfilt
from gui_backend.sub_backend.networks import AutoEncoderSmall, Classifier
import torch
from scipy.fft import ifft
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

def t_view_same_plot(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    tertiary_data.fundamentals["color_map"] = {
        "Receiver 0": (255, 0, 0),
        "Receiver 1": (0, 255, 0),
        "Receiver 2": (0, 0, 255),
    }
    tertiary_data.fundamentals["color_list"] = [color for color in tertiary_data.fundamentals["color_map"].values()]
    sub_plot_info = PerSubPlot()
    sub_plot_info.sub_plot_name = "Signal Return per Receiver"
    tertiary_data.graph_info.per_subplot_info = [sub_plot_info]

    averaged = [np.mean(frame, axis=1) for frame in frame_list]
    return averaged, tertiary_data

def t_view_difference_same_plot(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    same_plot, new_teriary_data = t_view_same_plot(frame_list, tertiary_data)
    to_subtract_data = np.load("./transformed_data/receiver_data/5860Up-0-Nothing/2025_11_23_21_29_10_922989_0_0.npy")[:, 0]
    to_send_data = same_plot - to_subtract_data
    new_teriary_data.graph_info.per_subplot_info[0].sub_plot_name += " w/ Background Removed"
    return to_send_data, new_teriary_data

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


def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    sos  = butter(order, [low, high], btype='band', output="sos")
    return sos 

def apply_bandpass(signal, lowcut, highcut, fs, order=5):
    sos  = butter_bandpass(lowcut, highcut, fs, order=order)
    return sosfilt(sos, signal)

speed_of_light = 3e8
tgt_rng = 1
delay = (2 * tgt_rng)/speed_of_light #6.67 ns
fs = 4e6
sim_rate = 132e9
beta = .625e9
duration = 67.1125e-6
adc_delay = 3.1125e-6
n_samples = 256 #int(np.ceil((tx_duration-adc_delay)sim_rate))

f0_list = np.arange(58,63,.625)*1e9+beta/duration * adc_delay

def mini_chirp(f0, fs=fs, n_samples=n_samples, beta=beta, duration=duration, delay=delay):
    t = np.arange(0,n_samples)/fs
    phase = (2*np.pi*beta*delay/duration)*t+2*np.pi*f0-(np.pi*beta/duration)*delay**2
    return np.cos(phase)

def t_test(chirp_info_list: List[CreateLine], tertiary_data: TertiaryData):
    a = np.zeros((4*n_samples),np.float32)
    for i in range(4):
        a[i*n_samples:(i+1)*n_samples] = mini_chirp(f0_list[i])
        

    return [a[None]], tertiary_data

def simulate_fmcw_return(tx_chirp, sample_rate, target_range):
    up_sample_qoutient = 1000
    upsample = np.linspace(np.min(tx_chirp), np.max(tx_chirp), up_sample_qoutient)
    new_sample_rate = up_sample_qoutient * sample_rate
    speed_of_light = 3e8
    delay_time = (2 * target_range) / speed_of_light
    delay_samples = int(round(delay_time * new_sample_rate))
    phase = 2 * np.pi * np.cumsum(upsample) / new_sample_rate
    tx_time = np.exp(1j * phase)
    rx_time = np.zeros_like(upsample, dtype=complex)
    lambda_ = speed_of_light / upsample
    attenuation = 3.0e11 * (lambda_ / (4 * np.pi * target_range))**4 * 1
        
    noise = np.random.normal(0, 0.002, up_sample_qoutient - delay_samples)

    if delay_samples < len(upsample):
        rx_time[delay_samples:] = tx_time[:-delay_samples] * np.sqrt(attenuation[:-delay_samples]) + noise
    
    mixed = tx_time * np.conj(rx_time)
    
    bandpassed_signal = apply_bandpass(mixed.real, 20e3 * up_sample_qoutient, 500e3 * up_sample_qoutient, new_sample_rate, order=6)
    downsample_indices = np.linspace(0, up_sample_qoutient-1, len(tx_chirp), dtype=int)
    return_signal = bandpassed_signal[downsample_indices]
    return return_signal

def t_simulated_return(chirp_info_list: List[CreateLine], tertiary_data: TertiaryData):
    sample_durations = [chirp.num_samples for chirp in chirp_info_list]
    radius_to_target = 3.43
    chirp_recreator = RecreateChirp(chirp_info_list, max(sample_durations))
    simulated = []
    
    for tx_chirp in chirp_recreator.recreate_single_chirp():
        out = simulate_fmcw_return(tx_chirp, chirp_info_list[0].sampling_rate, radius_to_target)
        simulated.append(out[None])
    return simulated, tertiary_data

def t_simulated_through_auto(chirp_info_list: List[CreateLine], tertiary_data: TertiaryData):
    tertiary_data.fundamentals["color_map"] = {
        "Reconstructed": (255, 0, 0),
        "Original": (0, 0, 255),
    }
    tertiary_data.fundamentals["color_list"] = [color for color in tertiary_data.fundamentals["color_map"].values()]
    
    
    sim_return, tertiary_data = t_test(chirp_info_list, tertiary_data)
    fresh_model = AutoEncoderSmall().cuda()
    fresh_model.load_state_dict(torch.load("./models/coolsmall_autoencoder.pth"))
    fresh_model.eval()
    output = np.empty(((2, ) + (sim_return[0].shape[-1], )))
    output[0] = fresh_model(torch.from_numpy(sim_return[0][0] + 0.5).float().cuda(non_blocking=True)).cpu().detach().numpy()
    output[1] = sim_return[0] + 0.5
    tertiary_data.graph_info.per_subplot_info = [PerSubPlot()]
    tertiary_data.graph_info.per_subplot_info[0].sub_plot_name = "Reconstructed Beam Form"
    return [output], tertiary_data

def t_simulated_through_class(chirp_info_list: List[CreateLine], tertiary_data: TertiaryData):
    tertiary_data.fundamentals["color_map"] = {
        "Reconstructed": (255, 0, 0),
        "Original": (0, 0, 255),
    }
    tertiary_data.fundamentals["color_list"] = [color for color in tertiary_data.fundamentals["color_map"].values()]
    
    
    sim_return, tertiary_data = t_test(chirp_info_list, tertiary_data)
    fresh_model = Classifier().cuda()
    fresh_model.load_state_dict(torch.load("./models/classifier.pth"))
    fresh_model.eval()
    output = fresh_model(torch.from_numpy(sim_return[0][0] + 0.5).float().cuda(non_blocking=True)).cpu().detach().numpy()
    tertiary_data.graph_info.per_subplot_info = [PerSubPlot()]
    tertiary_data.graph_info.per_subplot_info[0].sub_plot_name = "Reconstructed Beam Form"
    return [output], tertiary_data

def t_go_thru_network(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    tertiary_data.fundamentals["color_map"] = {
        "Reconstructed": (255, 0, 0),
        "Original": (0, 0, 255),
    }
    tertiary_data.fundamentals["color_list"] = [color for color in tertiary_data.fundamentals["color_map"].values()]
    
    collapsed_data = t_beam_form(frame_list)
    to_subtract_data = np.load("./transformed_data/none/5860Up-0-Nothing/2025_11_23_21_29_10_922989_0_0.npy")
    to_send_data = ((collapsed_data[0] + 1) / 2) - ((to_subtract_data + 1) /2)
    fresh_model = AutoEncoderSmall().cuda()
    fresh_model.load_state_dict(torch.load("./models/coolsmall_autoencoder.pth"))
    fresh_model.eval()
    output = np.empty(((2, ) + (collapsed_data[0].shape[-1], )))
    output[0] = fresh_model(torch.from_numpy(to_send_data[0][0] + 0.5).float().cuda(non_blocking=True)).cpu().detach().numpy()
    output[1] = to_send_data[:, 0] + 0.5
    tertiary_data.graph_info.per_subplot_info = [PerSubPlot()]
    tertiary_data.graph_info.per_subplot_info[0].sub_plot_name = "Reconstructed Beam Form"
    return [output], tertiary_data

def t_subbed(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    collapsed_data = t_beam_form([np.concatenate([frame for frame in frame_list], axis=2)])
    to_subtract_data = np.load("./transformed_data/none/5860Up-0-Nothing/2025_11_23_21_29_10_922989_0_0.npy")
    to_send_data = ((collapsed_data[0] + 1) / 2) - ((to_subtract_data + 1) /2) + 0.5
    return [to_send_data[0][:16]]

def t_difference_encoder(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    tertiary_data.fundamentals["boundaries"] = (0.0, 1.0)
    return [t_go_thru_network(frame_list, tertiary_data)[0] - t_subbed(frame_list, tertiary_data)[0]], tertiary_data

def t_reduced_output(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    collapsed_data = t_beam_form([np.concatenate([frame for frame in frame_list], axis=2)])
    to_subtract_data = np.load("./transformed_data/none/5860Up-0-Nothing/2025_11_23_21_29_10_922989_0_0.npy")
    to_send_data = ((collapsed_data[0] + 1) / 2) - ((to_subtract_data + 1) /2)
    fresh_model = AutoEncoderSmall().cuda()
    fresh_model.load_state_dict(torch.load("./models/large_autoencoder.pth"))
    fresh_model.eval()
    output = []
    
    fresh_model.reduce_latent_space = -1
    zero_output = fresh_model(torch.from_numpy(to_send_data[0][:16] + 0.5).float().cuda(non_blocking=True))
    
    for dimension in range(16):
        fresh_model.reduce_latent_space = dimension
        model_output = fresh_model(torch.from_numpy(to_send_data[0][:16] + 0.5).float().cuda(non_blocking=True)) - zero_output
        output.append(model_output.cpu().detach().numpy()[None])
    tertiary_data.fundamentals["boundaries"] = (0.0, 1.0)
    return output, tertiary_data

def t_reduced_dim(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    collapsed_data = t_beam_form([np.concatenate([frame for frame in frame_list], axis=2)])
    to_subtract_data = np.load("./transformed_data/none/5860Up-0-Nothing/2025_11_23_21_29_10_922989_0_0.npy")
    to_send_data = ((collapsed_data[0] + 1) / 2) - ((to_subtract_data + 1) /2)
    fresh_model = AutoEncoderSmall().cuda()
    fresh_model.load_state_dict(torch.load("./models/large_autoencoder.pth"))
    fresh_model.eval()
    _ = fresh_model(torch.from_numpy(to_send_data[0][:128] + 0.5).float().cuda(non_blocking=True))
    
    return [fresh_model.latent_space.cpu().detach().numpy()[None]]

def t_accuracy(frame_list: List[NDArray[np.float64]], tertiary_data: TertiaryData):
    tertiary_data.fundamentals["color_map"] = {
        "Training": (255, 0, 0),
        "Validation": (0, 0, 255),
    }
    tertiary_data.fundamentals["color_list"] = [color for color in tertiary_data.fundamentals["color_map"].values()]
    tertiary_data.graph_info.per_subplot_info = [PerSubPlot()]
    tertiary_data.graph_info.per_subplot_info[0].sub_plot_name = "Accuracy Per Epoch"
    tertiary_data.graph_info.per_subplot_info[0].x_axis_label = Label(name="Epoch(s)", units=None)
    tertiary_data.graph_info.y_axis_label = None
    tertiary_data.graph_info.z_axis_label = Label(name="Accuracy", units=None)
    tertiary_data.graph_info.tab_names = ["Accuracy"]
    accuracy = np.mean(np.argmax(frame_list[1], axis=-1) == np.argmax(frame_list[2], axis=-1), axis=1)
    return [accuracy], tertiary_data