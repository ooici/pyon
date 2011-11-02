__author__ = 'sphenrie'

from scripts.pycc import entry
from pydev import pydevd

if __name__ == '__main__':
    pydevd.settrace('localhost', port=8585, stdoutToServer=True, stderrToServer=True, suspend=False)
    entry()
