import torch
import torch.nn as nn
from numpy.typing import NDArray
import numpy as np
from typing import List, Tuple, Optional
from abc import abstractmethod

class PerceptronLayer(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.linear_layer = nn.Linear(in_channels, out_channels)
        # self.batch_norm = nn.BatchNorm1d(out_channels)
        self.activate_layer = nn.LeakyReLU()
        # self.drop_out = nn.Dropout(0.2)
        
        self.output = None

    def forward(self, x, secondary_input=None):
        x = self.linear_layer(x)
        # x = self.batch_norm(x)
        x = self.activate_layer(x)
        # x = self.drop_out(x)
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
        self.network: nn.Sequential = None
        
    @abstractmethod
    def __str__(self) -> str:
        return "Base Network"

    def forward(self, network_input: torch.Tensor):
        return self.network(network_input)

    @abstractmethod
    def return_pertinent_information(self) -> Tuple[List[str], torch.Tensor]:
        raise NotImplementedError


class Encoder(Network):
    def __init__(self, middle_layer: int):
        super().__init__()
        self.reduced_dimensions = nn.Linear(256, middle_layer)
        
        self.network = nn.Sequential(
            PerceptronLayer(4096, 512),
            PerceptronLayer(512, 256),
            self.reduced_dimensions,
        )

class Decoder(Network):
    def __init__(self, middle_layer: int):
        super().__init__()
        
        self.network = nn.Sequential(
            PerceptronLayer(middle_layer, 256),
            PerceptronLayer(256, 512),
            nn.Linear(512, 4096)
        )
        
class EncoderSmall(Network):
    def __init__(self, middle_layer: int):
        super().__init__()

        self.network = nn.Sequential(
            PerceptronLayer(1024, 256),
            PerceptronLayer(256, 128),
            nn.Linear(128, middle_layer),
            nn.LeakyReLU()
        )

class DecoderSmall(Network):
    def __init__(self, middle_layer: int):
        super().__init__()
        
        self.network = nn.Sequential(
            PerceptronLayer(middle_layer, 128),
            PerceptronLayer(128, 256),
            nn.Linear(256, 1024),
        )


class AutoEncoder(Network):
    def __init__(self, reduce_latent_space: Optional[List[int]] = None):
        super().__init__()
        self.reduce_latent_space = reduce_latent_space
        self.encoder = Encoder(32)
        self.decoder = Decoder(32)
        self.latent_space = None
        
    def __str__(self) -> str:
        return "large_autoencoder"
        
    def forward(self, network_input: torch.Tensor):
        self.latent_space = self.encoder(network_input)
        
        if self.reduce_latent_space is not None:
            self.latent_space[self.reduce_latent_space] = 0
        
        output = self.encoder(self.latent_space)
        return output
        
    def return_pertinent_information(self) -> Tuple[List[str], torch.Tensor]:
        return ["Reduced Dimensions"], [self.latent_space]
    
class AutoEncoderSmall(Network):
    def __init__(self, reduce_latent_space: Optional[int] = None):
        super().__init__()
        self.reduce_latent_space = reduce_latent_space
        self.encoder = EncoderSmall(16)
        self.decoder = DecoderSmall(16)
        self.latent_space = None
        
    def __str__(self) -> str:
        return "small_autoencoder"
        
    def forward(self, network_input: torch.Tensor):
        self.latent_space = self.encoder(network_input)
        
        if self.reduce_latent_space is not None:
            mask = torch.zeros_like(self.latent_space)
            if self.reduce_latent_space != -1:
                mask[:, self.reduce_latent_space] = 1.0
            self.latent_space = self.latent_space * mask
        
        output = self.decoder(self.latent_space)
        return output
        
    def return_pertinent_information(self) -> Tuple[List[str], torch.Tensor]:
        return ["Reduced Dimensions"], [self.latent_space]
    
    
class Classifier(Network):
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(
            PerceptronLayer(1024, 256),
            PerceptronLayer(256, 128),
            PerceptronLayer(128, 64),
            PerceptronLayer(64, 6),
        )
        
    def __str__(self) -> str:
        return "classifier"
        
    def return_pertinent_information(self) -> Tuple[List[str], torch.Tensor]:
        return None, None