import torch
import torch.nn as nn
from numpy.typing import NDArray
import numpy as np
from typing import List, Tuple
from abc import abstractmethod

class PerceptronLayer(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.linear_layer = nn.Linear(in_channels, out_channels)
        self.activate_layer = nn.ReLU()
        self.output = None

    def forward(self, x, secondary_input=None):
        x = self.linear_layer(x)
        x = self.activate_layer(x)
        self.output = x
        return x


class ConvLayer(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, kernel_size = (3, 3), stride = 1, padding=(1, 1)):
        super().__init__()
        self.conv_layer = nn.Conv2d(in_channels,out_channels,kernel_size, stride, padding)
        self.batch_layer = nn.BatchNorm2d(out_channels)
        self.activate_layer = nn.LeakyReLU()

    def forward(self, x, secondary_input=None):
        x = self.conv_layer(x)
        x = self.batch_layer(x)
        output = self.activate_layer(x)
        return output


class ResConvLayer(nn.Module):
    def __init__(self, in_channels, kernel_size = (3, 3), stride = 1, padding=(1, 1)) -> None:
        super().__init__()
        self.conv_obj_1 = ConvLayer(in_channels, in_channels, kernel_size, stride, padding)
        self.conv_obj_2 = ConvLayer(in_channels, in_channels, kernel_size, stride, padding)

    
    def forward(self, x, secondary_input=None):
        x2 = self.conv_obj_1(x)
        x2 = self.conv_obj_2(x2)
        output = x + x2
        return output


class ResConvBottleneckLayer(nn.Module):
    def __init__(self, in_channels, kernel_size = (3, 3), stride = 1, padding=(1, 1)) -> None:
        super().__init__()
        self.conv_obj_bottleneck = ConvLayer(in_channels, in_channels//4, kernel_size, stride, padding)
        self.conv_obj = ConvLayer(in_channels//4, in_channels//4, kernel_size, stride, padding)
        self.conv_obj_expansion = ConvLayer(in_channels//4, in_channels, kernel_size, stride, padding)
    
    def forward(self, x, secondary_input=None):
        x2 = self.conv_obj_bottleneck(x)
        x2 = self.conv_obj(x2)
        x2 = self.conv_obj_expansion(x2)
        output = x + x2
        return output


class Network(nn.Module):
    def __init__(self):
        super().__init__()
        
    @abstractmethod
    def __str__(self) -> str:
        return "Base Network"

    def forward(self, network_input: torch.Tensor):
        return self.network(network_input)

    @abstractmethod
    def return_pertinent_information(self) -> Tuple[List[str], torch.Tensor]:
        raise NotImplementedError

class AutoEncoder(Network):
    def __init__(self):
        super().__init__()
        self.reduced_dimensions = PerceptronLayer(256, 32)
        
        self.network = nn.Sequential(
            PerceptronLayer(4096, 512),
            PerceptronLayer(512, 256),
            self.reduced_dimensions,
            PerceptronLayer(32, 256),
            PerceptronLayer(256, 512),
            nn.Linear(512, 4096)
        )
        
    def __str__(self) -> str:
        return "large_autoencoder"
        
    def return_pertinent_information(self) -> Tuple[List[str], torch.Tensor]:
        return ["Reduced Dimensions"], [self.reduced_dimensions.output]
    
class SmallAutoEncoder(Network):
    def __init__(self):
        super().__init__()
        self.reduced_dimensions = PerceptronLayer(128, 8)
        
        self.network = nn.Sequential(
            PerceptronLayer(1024, 256),
            PerceptronLayer(256, 128),
            self.reduced_dimensions,
            PerceptronLayer(8, 128),
            PerceptronLayer(128, 256),
            nn.Linear(256, 1024)
        )
        
    def __str__(self) -> str:
        return "small_autoencoder"
        
    def return_pertinent_information(self) -> Tuple[List[str], torch.Tensor]:
        return ["Reduced Dimensions"], [self.reduced_dimensions.output]