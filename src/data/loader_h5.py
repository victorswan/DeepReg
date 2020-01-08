import random

import h5py
import numpy as np
import tensorflow as tf

import src.data.augmentation as aug

SKIPPED_KEYS = ["num_important", "num_labels"]  # keys in label h5 file


class H5DataLoader:
    def __init__(self, moving_image_filename, fixed_image_filename, moving_label_filename, fixed_label_filename):
        # load keys
        moving_key_dict = get_image_label_key_dict(image_filename=moving_image_filename,
                                                   label_filename=moving_label_filename)
        fixed_key_dict = get_image_label_key_dict(image_filename=fixed_image_filename,
                                                  label_filename=fixed_label_filename)

        # sanity check
        # two key dicts is the same
        for k in moving_key_dict:
            assert moving_key_dict[k] == fixed_key_dict[k]

        moving_image_shape = get_image_shape(moving_image_filename)
        fixed_image_shape = get_image_shape(fixed_image_filename)
        moving_label_shape = get_image_shape(moving_label_filename)
        fixed_label_shape = get_image_shape(fixed_label_filename)

        # sanity check
        # image and label have same shape
        if moving_image_shape != moving_label_shape:
            raise ValueError("moving image and label shape don't match")
        if fixed_image_shape != fixed_label_shape:
            raise ValueError("fixed image and label shape don't match")

        # save variables
        self.moving_image_filename = moving_image_filename
        self.fixed_image_filename = fixed_image_filename
        self.moving_label_filename = moving_label_filename
        self.fixed_label_filename = fixed_label_filename

        self.key_dict = moving_key_dict
        self.moving_image_shape = moving_image_shape
        self.fixed_image_shape = fixed_image_shape

    def get_generator(self):
        """
        For both moving and fixed, the image is always provided, but the label might not be provided,
        if the label is not provided, it only generates (moving_image, fixed_image) pairs,
        otherwise, generates (moving_image, fixed_image, moving_label), fixed_label pairs.
        """
        sorted_image_keys = sorted(self.key_dict)
        with h5py.File(self.moving_image_filename, "r") as hf_moving_image:
            with h5py.File(self.moving_label_filename, "r") as hf_moving_label:
                with h5py.File(self.fixed_image_filename, "r") as hf_fixed_image:
                    with h5py.File(self.fixed_label_filename, "r") as hf_fixed_label:
                        for image_index, image_key in enumerate(sorted_image_keys):
                            # sample a label
                            sorted_label_keys = sorted(self.key_dict[image_key])
                            label_index = random.randrange(len(sorted_label_keys))
                            label_key = sorted_label_keys[label_index]

                            # get data
                            moving_image = hf_moving_image.get(image_key)[()]
                            moving_label = hf_moving_label.get(label_key)[()]
                            fixed_image = hf_fixed_image.get(image_key)[()]
                            fixed_label = hf_fixed_label.get(label_key)[()]

                            indices = np.asarray([image_index, label_index], dtype=np.float32)
                            yield ((moving_image, fixed_image, moving_label), fixed_label, indices)

    def _get_dataset(self):
        dataset = tf.data.Dataset.from_generator(generator=self.get_generator,
                                                 output_types=(
                                                     (tf.float32, tf.float32, tf.float32), tf.float32, tf.float32),
                                                 output_shapes=((self.moving_image_shape,
                                                                 self.fixed_image_shape,
                                                                 self.moving_image_shape),
                                                                self.fixed_image_shape,
                                                                2,
                                                                ))

        return dataset

    def get_dataset(self, batch_size, training, dataset_shuffle_buffer_size):
        dataset = self._get_dataset()
        if training:
            dataset = dataset.shuffle(buffer_size=dataset_shuffle_buffer_size)
        dataset = dataset.batch(batch_size, drop_remainder=training)
        if training:
            # TODO add cropping, but crop first or rotation first?
            affine_transform = aug.AffineTransformation3D(moving_image_size=self.moving_image_shape,
                                                          fixed_image_size=self.fixed_image_shape,
                                                          batch_size=batch_size)
            dataset = dataset.map(affine_transform.transform)
        return dataset


def get_sorted_keys(filename):
    with h5py.File(filename, "r") as hf:
        return sorted(hf.keys())


def get_image_label_key_dict(image_filename, label_filename):
    """
    for images, the keys of h5 are like ["case000000", "case000001",  ...]
    for labels, the keys of h5 are like ["case000000_bin000", "case000000_bin001", ...,
                                         "case000001_bin000", "case000001_bin001", ...,
                                         ...,
                                         "num_important", "num_labels"]

    :param image_filename:
    :param label_filename:
    :return:
    """

    # load keys
    image_keys = get_sorted_keys(filename=image_filename)
    label_keys = get_sorted_keys(filename=label_filename)

    # build dictionary
    key_dict = dict()  # map image key to label key
    for label_key in label_keys:
        image_key = label_key.split("_bin")[0]
        if image_key not in SKIPPED_KEYS:
            assert image_key in image_keys
            if image_key not in key_dict.keys():
                key_dict[image_key] = []
            key_dict[image_key].append(label_key)  # no need to sort afterwards as label_keys are sorted

    # sanity check
    # all samples have labels
    assert sorted(key_dict.keys()) == image_keys

    return key_dict


def get_image_shape(filename):
    with h5py.File(filename, "r") as hf:
        keys = sorted([k for k in hf.keys() if k not in SKIPPED_KEYS])
        sh = list(hf.get(keys[0]).shape)

        # sanity check
        # all samples have same 3d shape
        assert len(sh) == 3
        for k in keys:
            assert sh == list(hf.get(k).shape)
    return sh