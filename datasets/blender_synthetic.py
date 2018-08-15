# MIT License
# 
# Copyright (c) 2018 Tom Runia
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to conditions.
#
# Author: Tom Runia
# Date Created: 2018-08-14

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import glob

import numpy as np
import h5py

import torch
from torch.utils.data import Dataset


class BlenderSyntheticDataset(Dataset):

    def __init__(self, root_path, spatial_size, temporal_size, spatial_transform=None, temporal_transform=None, target_transform=None):

        # work in progress
        assert temporal_transform is None

        self._root_path = root_path
        self._spatial_size = spatial_size
        self._temporal_size = temporal_size

        self._spatial_transform = spatial_transform
        self._temporal_transform = temporal_transform
        self._target_transform = target_transform

        self._make_dataset()


    def _make_dataset(self):

        self._data_files = glob.glob(os.path.join(self._root_path, '*.h5'))
        self._data_files.sort()

        with h5py.File(self._data_files[0]) as hf:
            self._num_examples_per_file = len(hf['labels'])
            self._num_examples = len(self._data_files)*self._num_examples_per_file

        self._unique_targets = set()
        for i, path in enumerate(self._data_files):
            with h5py.File(path) as hf:
                self._unique_targets = self._unique_targets.union(set(list(hf['labels'].value)))

        self._target_offset = min(self._unique_targets)

        print('  Number of HDF5 files found: {}'.format(len(self._data_files)))
        print('  Number of examples found:   {}'.format(self._num_examples))
        print('  Number of targets found:    {}'.format(len(self._unique_targets)))

    def __len__(self):
        return self._num_examples

    def __getitem__(self, idx):

        container_idx = idx // self._num_examples_per_file
        example_idx = (idx-(container_idx*self._num_examples_per_file))

        with h5py.File(self._data_files[container_idx], 'r') as hf:
            clip   = hf['videos'][example_idx]
            target = hf['labels'][example_idx]

        #shape = (self._temporal_size,self._spatial_size,self._spatial_size,3)
        #clip = np.random.uniform(0, 255, shape).astype(np.uint8)

        # Apply temporal transformations (i.e. temporal cropping, looping)
        #if self._temporal_transform is not None:
        #    frame_indices = self._temporal_transform(frame_indices)

        # Apply spatial transformations (i.e. spatial cropping, flipping, normalization)
        if self._spatial_transform is not None:
            self._spatial_transform.randomize_parameters()
            clip = [self._spatial_transform(frame) for frame in clip]

        clip   = torch.stack(clip, dim=1).type(torch.FloatTensor)
        target = torch.from_numpy(np.asarray(target-self._target_offset, np.int64))
        target = torch.unsqueeze(target, -1)

        return clip, target