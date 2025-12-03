import torch
import torch.nn as nn
from numpy.typing import NDArray
import numpy as np

class PerceptronLayer(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.linear_layer = nn.Linear(in_channels, out_channels)
        self.activate_layer = nn.ReLU()

    def forward(self, x, secondary_input=None):
        x = self.linear_layer(x)
        output = self.activate_layer(x)
        return output


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


class ParentNetwork(nn.Module):
    def __init__(self, num_labels):
        super(ParentNetwork, self).__init__()

    def forward(self, network_input: NDArray[np.float64]):
        return self.network(network_input)


class AutoEncoder(ParentNetwork):
    def __init__(self):
        super(ParentNetwork,self).__init__()
        self.network = nn.Sequential(
            PerceptronLayer(4096, 512),
            PerceptronLayer(512, 256),
            PerceptronLayer(256, 32),
            PerceptronLayer(32, 256),
            PerceptronLayer(256, 512),
            nn.Linear(512, 4096)
        )