__author__ = 'sphenrie'

from scripts.pycc import entry
from pydev import pydevd

def start_debugging():
    pydevd.settrace('localhost', port=8585, stdoutToServer=True, stderrToServer=True, suspend=False)
    entry()
   
if __name__ == '__main__':
    start_debugging()

