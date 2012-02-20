"""
@author Luke Campbell
@file pyon/util/file_sys.py
@description Utility for manageing relative file system paths
"""


import StringIO
import os
import re
import time
import hashlib
from pyon.core.exception import NotFound, BadRequest
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

        # Limit 64 chars
        return ret[:64]

    @staticmethod
    def get_url(fs, filename, ext=''):
        """
        @param fs The file system enumeration for the resource where this file belongs. 'TEMP', 'LIBRARY' etc.
        @param file The filename to be used
        @param ext Optional: guarantees the file will have the extension specified
        @return The full path to the desired resource on the file system
        """
        return os.path.join(FS_DIRECTORY[fs], '%s%s' % (FileSystem._parse_filename(filename), ext))

    @staticmethod
    def mktemp(filename='', ext=''):
        """
        @description Creates a temporary file that is safe to use
        @param filename Desired filename to use, if empty a random name is generated
        @param ext the optional file extension to use
        @return an open file to the desired temporary file
        """
        if filename:
            return open(FileSystem.get_url(fs=FS.TEMP,filename=filename,ext=ext),'w')
        else:
            rand_str = hashlib.sha1(time.ctime()).hexdigest()[:24]
            return open(FileSystem.get_url(fs=FS.TEMP,filename=rand_str), 'w')

    @staticmethod
    def unlink(filepath):
        """
        @description Removes a specified file or symlink
        @param filepath The absolute path to the file.
        @throws NotFound, BadRequest
        """
        if os.path.split(filepath)[0] not in FileSystem.FS_DIRECTORY.values():
            raise NotFound('Specified is not in an acceptable path.')
        try:
            os.unlink(filepath)
        except OSError:
            raise BadRequest('The specified could not be removed.')

    @staticmethod
    def memory_file():
        """
        Very fast file IO, great for temporary files and fast mechanisms, avoid arbitrarily large strings, will cause thrashing!
        """
        return StringIO.StringIO()

    @staticmethod
    def secure_file():
        """
        A method for secure file I/O, the file is immediately unlinked after creation
        """
        f = FileSystem.mktemp()
        FileSystem.unlink(f.name)
        return f

    @staticmethod
    def atomic_file(filename):
        """
        @description Create an atomic filename
        @param filename The desired (destination) file
        @return An AtomicFile
        """
        return AtomicFile(fname=filename)


class AtomicFile(object):
    """
    A write-only atomic file. Writing is performed to a temporary file and on close,
    the file is moved to the desired destination.

    This is an atomic action.

    This is ideal for threads, concurrency, crashes and saving state.

    """
    def __init__(self,fname):
        self.filename = fname
        self.file = FileSystem.mktemp()

    def write(self, text):
        self.file.write(text)

    def close(self):
        tmp_filename = self.file.name
        self.file.close()
        os.rename(tmp_filename, self.filename)


# Clients should either import this directory
#
FS_DIRECTORY = FileSystem.FS_DIRECTORY
FS = FileSystem.FS
