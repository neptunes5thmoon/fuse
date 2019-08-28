import numpy as np

from gunpowder import BatchFilter
from collections import Iterable

class IntensityAugment(BatchFilter):
    '''Randomly scale and shift the values of an intensity array.

    Args:

        arrays (:class:`ArrayKey` or list of :class:`ArrayKey`s):

            The intensity arrays to modify, applying the same random transformation to each.

        scale_min (``float``):
        scale_max (``float``):
        shift_min (``float``):
        shift_max (``float``):

            The min and max of the uniformly randomly drawn scaling and
            shifting values for the intensity augmentation. Intensities are
            changed as::

                a = a.mean() + (a-a.mean())*scale + shift

        z_section_wise (``bool``):

            Perform the augmentation z-section wise. Requires 3D arrays and
            assumes that z is the first dimension.
    '''

    def __init__(self, arrays, scale_min, scale_max, shift_min, shift_max, z_section_wise=False):
        if not isinstance(arrays, Iterable):
            arrays = [arrays,]
        self.arrays = arrays
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.shift_min = shift_min
        self.shift_max = shift_max
        self.z_section_wise = z_section_wise

    def process(self, batch, request):

        assert not (self.z_section_wise and len(self.arrays) > 0), "Intensity augment with z_section for different " \
                                                                   "resolutions not implemented"
        scale = np.random.uniform(low=self.scale_min, high=self.scale_max)
        shift = np.random.uniform(low=self.shift_min, high=self.shift_max)
        for array in self.arrays:
            raw = batch.arrays[array]

            assert not self.z_section_wise or raw.spec.roi.dims() == 3, "If you specify 'z_section_wise', I expect 3D data."
            assert raw.data.dtype == np.float32 or raw.data.dtype == np.float64, "Intensity augmentation requires float types for the raw array (not " + str(raw.data.dtype) + "). Consider using Normalize before."
            assert raw.data.min() >= 0 and raw.data.max() <= 1, "Intensity augmentation expects raw values in [0,1]. Consider using Normalize before."

            if self.z_section_wise:
                for z in range((raw.spec.roi/self.spec[self.array].voxel_size).get_shape()[0]):
                    raw.data[z] = self.__augment(
                            raw.data[z],
                            np.random.uniform(low=self.scale_min, high=self.scale_max),
                            np.random.uniform(low=self.shift_min, high=self.shift_max)
                    )
            else:
                raw.data = self.__augment(raw.data, scale, shift)

            # clip values, we might have pushed them out of [0,1]
            raw.data[raw.data>1] = 1
            raw.data[raw.data<0] = 0

    def __augment(self, a, scale, shift):

        return a.mean() + (a-a.mean())*scale + shift