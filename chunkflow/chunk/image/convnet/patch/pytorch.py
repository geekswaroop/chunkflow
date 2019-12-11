# from .inference_engine import InferenceEngine
# import imp
from typing import Union
import torch
import numpy as np
from .base import PatchInferencerBase
from chunkflow.lib import load_source


class PyTorch(PatchInferencerBase):
    """perform inference for an image patch using pytorch.
    Parameters
    ----------
    patch_size: size of input/output patch size. We assume that 
        the input and output patch size is the same. 
    patch_overlap: overlap of neighboring patches.
    model_file_name: file name of model
    weight_file_name: file name of trained weight.
    use_batch_norm: use batch normalization or not.
    is_static_batch_norm: whether the batch norm is static or instance level?
    num_output_channels: number of output channels.
    mask: the weight mask applied to output patch.
    
    You can make some customized processing in your model file. 
    You can define `load_model` function to customize your way of 
    loading model. This is useful for loading some models trained using
    old version pytorch (<=0.4.0). You can also define `pre_process` 
    and `post_process` function to insert your own customized processing.
    """
    def __init__(self, convnet_model: str, convnet_weight_path: str,
                 input_patch_size: tuple, output_patch_overlap: tuple,
                 output_patch_size: tuple = None, 
                 use_batch_norm: bool = True,
                 is_static_batch_norm: bool = False,
                 num_output_channels: int = 1, bump: str='wu'):
        assert bump == 'wu'
        super().__init__(input_patch_size, output_patch_size, 
                         output_patch_overlap, num_output_channels)

        self.num_output_channels = num_output_channels
        if torch.cuda.is_available():
            self.is_gpu = True
            # put mask to gpu
            self.mask = torch.from_numpy(self.mask).cuda()
        else:
            self.is_gpu = False

        net_source = load_source(convnet_model)

        if hasattr(net_source, "load_model"):
            self.net = net_source.load_model(convnet_weight_path)
        else:
            self.net = net_source.InstantiatedModel
            chkpt = torch.load(convnet_weight_path)
            state_dict = chkpt['state_dict'] if 'state_dict' in chkpt else chkpt
            self.net.load_state_dict(state_dict)

        if self.is_gpu:
            self.net = self.net.cuda()
            # data parallel do not work with old emvision net
            #self.net = torch.nn.DataParallel(
            #    self.net, device_ids=range(torch.cuda.device_count()))

        # Print model's state_dict
        #print("Model's state_dict:")
        #for param_tensor in self.net.state_dict():
        #    print(param_tensor, "\t", self.net.state_dict()[param_tensor].size())

        if use_batch_norm and is_static_batch_norm:
            self.net.eval()

        if hasattr(net_source, "pre_process"):
            self.pre_process = net_source.pre_process
        else:
            self.pre_process = self._pre_process

        if hasattr(net_source, "post_process"):
            self.post_process = net_source.post_process
        else:
            self.post_process = self._identity

    def _pre_process(self, input_patch):
        if self.is_gpu:
            input_patch = torch.from_numpy(input_patch).cuda()
        return input_patch
    
    def _identity(self, patch):
        return patch

    def __call__(self, input_patch):
        # make sure that the patch is 5d ndarray
        input_patch = self._reshape_patch(input_patch)

        with torch.no_grad():
            net_input = self.pre_process(input_patch)
            # the network input and output should be dict
            net_output = self.net(net_input)

            # get the required output patch from network 
            # The processing depends on network model and application
            output_patch = self.post_process(net_output)

            # save patch for debug
            #import h5py
            #with h5py.File('/tmp/patch.h5', "w") as f:
            #    f['main'] = output_patch[0,:,:,:,:].data.cpu().numpy()

            # mask in gpu/cpu
            output_patch *= self.output_patch_mask
            output_patch = self._crop_output_patch(output_patch)

            if self.is_gpu:
                # transfer to cpu
                output_patch = output_patch.data.cpu()
            output_patch = output_patch.numpy()
            return output_patch