"""
Module for IO of files in relation to
data loading.
"""
import glob
import os
import random

import h5py


def get_h5_sorted_keys(filename):
    """
    Function to get sorted keys from filename
    :param filename: h5 file.
    :return: sorted keys of h5 file.
    """
    with h5py.File(filename, "r") as h5_file:
        return sorted(h5_file.keys())


def mkdir_if_not_exists(path):
    """
    Function to make a new directory at path
    if directory does not exist
    :param path: path to dir
    """
    if not os.path.exists(path):
        os.makedirs(path)


def get_sorted_file_paths_in_dir_with_suffix(
    dir_paths: (str, list), suffix: (str, list)
):
    """
    Return the path of all files under the given directory.

    :param dir_paths: path(s) of the directory, can be string or list of strings
    :param suffix: suffix of file names like h5, nii.gz, nii, should not start with .
    :return: list of file paths, the paths includes dir_path
    """
    if isinstance(dir_paths, str):
        dir_paths = [dir_paths]
    if isinstance(suffix, str):
        suffix = [suffix]

    paths = []
    for p in dir_paths:
        for s in suffix:
            paths += glob.glob(os.path.join(p, "**", "*." + s), recursive=True)
    return sorted(paths)


def check_difference_between_two_lists(list1: list, list2: list):
    """
    Raise error if two lists are not identical
    :param list1: list
    :param list2: list
    :return: error message if lists are not equal
    """

    list1_unique = sorted(set(list1) - set(list2))
    list2_unique = sorted(set(list2) - set(list1))
    if len(list2_unique) != 0 or len(list1_unique) != 0:
        raise ValueError(
            "two lists are not identical\n"
            "list1 has unique elements {}\n"
            "list2 has unique elements {}\n".format(list1_unique, list2_unique)
        )


def get_label_indices(num_labels: int, sample_label: str) -> list:
    """
    Function to get sample label indices for a given number
    of labels and a sampling policy
    :param num_labels: int number of labels
    :param sample_label: method for sampling the labels
    :return: list of labels defined by the sampling method.
    """
    if sample_label == "sample":  # sample a random label
        return [random.randrange(num_labels)]
    elif sample_label == "first":  # use the first label
        return [0]
    elif sample_label == "all":  # use all labels
        return list(range(num_labels))
    else:
        raise ValueError("Unknown label sampling policy %s" % sample_label)
