# See https://github.com/nimbusproject/kazoo/blob/master/kazoo/sync/util.py

_realthread = None

def get_realthread():
    """Get the real Python thread module, regardless of any monkeypatching
    """
    global _realthread
    if _realthread:
        return _realthread

    import imp
    fp, pathname, description = imp.find_module('thread')
    try:
        _realthread =  imp.load_module('realthread', fp, pathname, description)
        return _realthread
    finally:
        if fp:
            fp.close()

_realtime = None

def get_realtime():
    """Get the real Python time module, regardless of any monkeypatching
    """
    global _realtime
    if _realtime:
        return _realtime

    import imp
    fp, pathname, description = imp.find_module('time')
    try:
        _realtime =  imp.load_module('realtime', fp, pathname, description)
        return _realtime
    finally:
        if fp:
            fp.close()
