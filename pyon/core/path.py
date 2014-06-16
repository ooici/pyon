#!/usr/bin/env python

__author__ = 'Adam R. Smith'


import fnmatch
import os
from pkg_resources import resource_filename


def resolve(filename):
    """
    @brief Compensates for different current directories in tests and production
    """
    if not filename:
        return None

    resolved_file = filename

    if not '/' in filename:  # Looking for a package
        pass
    else:
        if not os.path.isabs(filename):
            # First try relative to the local directory
            relative_path = filename
            if os.getcwd().endswith("_temp"):
                relative_path = os.path.join('..', relative_path)
            if os.path.exists(relative_path):
                resolved_file = relative_path

            # Next try a file in the package (this does not need to know about the trial dir)
            if resolved_file is None:
                resolved_file = resource_filename('pyon', os.path.join('..', filename))

            if not os.path.isabs(resolved_file):
                resolved_file = os.path.abspath(resolved_file)

    return resolved_file


def list_files_recursive(file_dir, pattern, do_first=[], exclude_dirs=[]):
    """
    Recursively find all files matching pattern under file_dir and return a list.
    """
    all_files = [os.path.join(file_dir, file) for file in do_first]
    skip_me = set(all_files)
    exclude_dirs = set([os.path.join(file_dir, path) for path in exclude_dirs])

    new_files = []
    for root, dirs, files in os.walk(file_dir):
        if root in exclude_dirs:
            continue
        for file in fnmatch.filter(files, pattern):
            path = os.path.join(root, file)
            if not path in skip_me:
                new_files.append(path)

    # Make imports more predictable by sorting by filename
    all_files.extend(sorted(new_files))
    return all_files
