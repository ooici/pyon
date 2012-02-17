"""
@author Luke Campbell
@file pyon/util/file_sys.py
@description Utility for manageing relative file system paths
"""


import os
from pyon.util.containers import DotDict
from pyon.core.bootstrap import CFG


class FileSystem(object):
    FS_DIRECTORY_LIST = ['RESOURCE','TEMP','LIBRARY','CACHE','RUN','USERS','LOG']
    FS_DIRECTORY = DotDict(zip(FS_DIRECTORY_LIST,FS_DIRECTORY_LIST))
    def __init__(self):
        for k,v in self.FS_DIRECTORY.iteritems():
            s = v.lower() # Lower case string
            conf = CFG.get_safe('system.filesystem.%s' % s, None)
            if conf:
                self.FS_DIRECTORY[k] = conf
            else:
                self.FS_DIRECTORY[k] = os.path.join('/tmp',s)

            if not os.path.exists(self.FS_DIRECTORY[k]):
                #@todo: Warning potential security problem if we use 777 for perms all the time
                os.mkdir(self.FS_DIRECTORY[k], 0777)
    def get_url(self, directory=''):
        return self.FS_DIRECTORY.get_safe(directory)

FS_DIRECTORY = FileSystem.FS_DIRECTORY
