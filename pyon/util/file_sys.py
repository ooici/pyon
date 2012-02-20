"""
@author Luke Campbell
@file pyon/util/file_sys.py
@description Utility for manageing relative file system paths
"""


import os
import re
from pyon.util.containers import DotDict
from pyon.core.bootstrap import CFG


class FileSystem(object):
    # These are static, and shared throughout the container, do not operate on a per-instance basis.
    FS_DIRECTORY_LIST = ['RESOURCE','TEMP','LIBRARY','CACHE','RUN','USERS','LOG']
    FS_DIRECTORY = DotDict(zip(FS_DIRECTORY_LIST,FS_DIRECTORY_LIST))
    FS = DotDict(zip(FS_DIRECTORY_LIST, FS_DIRECTORY_LIST))
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FileSystem, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):

        for k,v in FileSystem.FS_DIRECTORY.iteritems():
            s = v.lower() # Lower case string
            conf = CFG.get_safe('system.filesystem.%s' % s, None)
            if conf:
                FileSystem.FS_DIRECTORY[k] = conf
            else:
                FileSystem.FS_DIRECTORY[k] = os.path.join('/tmp',s)

            if not os.path.exists(self.FS_DIRECTORY[k]):
                #@todo: Warning potential security problem if we use 777 for perms all the time
                os.mkdir(FileSystem.FS_DIRECTORY[k], 0777)
    @staticmethod
    def _parse_filename(file):
        # Remove whitespace
        ret = re.sub(r'\s', '_', file)

        # Remove non alphanumeric
        ret = re.sub(r'[~!@#$%^&*()-+,/\'\";:`<>?\\\]\[\}\{=]+', '', ret)

        return ret[:64]

    @staticmethod
    def get_url(fs, file, ext=''):
        """
        @param fs The file system enumeration for the resource where this file belongs. 'TEMP', 'LIBRARY' etc.
        @param file The filename to be used
        @param ext Optional: guarantees the file will have the extension specified
        @return The full path to the desired resource on the file system
        """
        return os.path.join(FS_DIRECTORY[fs], '%s.%s' % (FileSystem._parse_filename(file), ext))



# Clients should either import this directory
#
FS_DIRECTORY = FileSystem.FS_DIRECTORY
FS = FileSystem.FS