import glob
import logging
import os
import time

import numpy as np

import gpn.util
import jnius_config
from gpn.simple_augment import SimpleAugment
from gunpowder import Hdf5Source, Roi, Coordinate, ArrayKey

logging.basicConfig(level = logging.DEBUG)

RAW       = gpn.util.RAW
GT_LABELS = gpn.util.GT_LABELS


def add_to_viewer(batch, keys, name=lambda key: key.identifier, is_label=lambda key, array: array.data.dtype == np.uint64):
    states = {}
    for key in keys:
        if not key in batch:
            continue

        data       = batch[key]
        data_img   = imglyb.to_imglib(data.data)
        voxel_size = data.spec.voxel_size[::-1]
        offset     = data.spec.roi.get_begin()[::-1]

        if is_label(key, data):
            state = pbv.addSingleScaleLabelSource(
                data_img,
                voxel_size,
                offset,
                np.max(data.data) + 1,
                name(key))
        else:
            state = pbv.addSingleScaleRawSource(
                data_img,
                voxel_size,
                offset,
                np.min(data.data),
                np.max(data.data),
                name(key))
        states[key] = state

    return states


import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--max-heap-size", default="16g")
args = parser.parse_args()

data_providers = []
data_dir = '/groups/saalfeld/home/hanslovskyp/experiments/quasi-isotropic/data'
file_pattern = 'sample_A_padded_20160501-2-additional-sections-fixed-offset.h5'



for data in glob.glob(os.path.join(data_dir, file_pattern)):
    h5_source = Hdf5Source(
        data,
        datasets={
            RAW: 'volumes/raw',
            GT_LABELS: 'volumes/labels/neuron_ids-downsampled',
        }
    )
    data_providers.append(h5_source)

input_resolution  = (360, 36, 36)
output_resolution = (120, 108, 108)
offset = (13640, 10932, 10932)

roi = Roi(offset=(13640, 32796 + 36, 32796 + 36), shape=Coordinate((120, 100, 100)) * output_resolution)

augmentations = (
    SimpleAugment(transpose_only=[1,2], apply_to=(RAW, GT_LABELS)),
)

batch = gpn.util.run_augmentations(
    data_providers=data_providers,
    roi=lambda key: roi.copy(),
    augmentations=augmentations,
    keys=(RAW, GT_LABELS))

jnius_config.add_options('-Xmx{}'.format(args.max_heap_size))

import payntera.jfx
import imglyb
from jnius import autoclass
payntera.jfx.init_platform()

PainteraBaseView = autoclass('org.janelia.saalfeldlab.paintera.PainteraBaseView')
viewer = PainteraBaseView.defaultView()
pbv = viewer.baseView
scene, stage = payntera.jfx.start_stage(viewer.paneWithStatus.getPane())
payntera.jfx.invoke_on_jfx_application_thread(lambda: pbv.orthogonalViews().setScreenScales([0.3, 0.1, 0.03]))

keys_to_show = (
    RAW,
    GT_LABELS,
    ArrayKey('RAW-original'),
    ArrayKey('GT_LABELS-original'))
states = add_to_viewer(batch, keys=keys_to_show)

viewer.keyTracker.installInto(scene)
scene.addEventFilter(autoclass('javafx.scene.input.MouseEvent').ANY, viewer.mouseTracker)

while stage.isShowing():
    time.sleep(0.1)
