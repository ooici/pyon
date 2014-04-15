
# https://github.com/surfly/gevent/blob/b515eb5c803a1217cdff67f9c953a49c77d7bbc1/gevent/_threading.py
_pythread = None

def get_pythread():
    '''
    Loads the 'thread' module, free of monkey patching.
    '''
    global _pythread
    if _pythread:
        return _pythread # Cache the module so we don't have to use imp every time

    import imp
    fp, path, desc = imp.find_module('thread')
    try:
        _pythread = imp.load_module('pythread', fp, path, desc)
    finally:
        if fp:
            fp.close() # Close the file
    return _pythread

# thread imports
start_new_thread = get_pythread().start_new_thread
Lock = get_pythread().allocate_lock
get_ident = get_pythread().get_ident
local = get_pythread()._local
stack_size = get_pythread().stack_size


class RLock(object):
    def __init__(self):
        self.__block = Lock()
        self.__owner = None
        self.__count = 0

    def __repr__(self):
        owner = self.__owner
        return "<%s owner=%r count=%d>" % (self.__class__.__name__, owner, self.__count)

    def acquire(self, blocking=1):
        me = get_ident()
        if self.__owner == me:
            self.__count = self.__count + 1
            return 1
        rc = self.__block.acquire(blocking)
        if rc:
            self.__owner = me
            self.__count = 1
        return rc

    __enter__ = acquire

    def release(self):
        if self.__owner != get_ident():
            raise RuntimeError("cannot release un-acquired lock")
        self.__count = count = self.__count - 1
        if not count:
            self.__owner = None
            self.__block.release()

    def __exit__(self, type, value, traceback):
        self.release()

    def _acquire_restore(self, count_owner):
        count, owner = count_owner
        self.__block.acquire()
        self.__count = count
        self.__owner = owner

    def _release_save(self):
        count = self._count
        self.__count = 0
        owner = self.__owner
        self.__owner = None
        self.__block.release()
        return count, owner

    def _is_owned(self):
        return self.__owner == get_ident()

class Condition(object):
    def __init__(self, lock=None):
        if lock is None:
            lock = RLock()

        self.__lock = lock
        # Export th elock's acquire() and release() methods
        self.acquire = lock.acquire
        self.release = lock.release

        try:
            self._release_save = lock._release_save
        except AttributeError:
            pass

        try:
            self._acquire_restore = lock._acquire_restore
        except AttributeError:
            pass

        try:
            self._is_owned = lock._is_owned
        except AttributeError:
            pass

        self.__waiters = []

    def __enter__(self):
        return self.__lock.__enter__()

    def __exit__(self, type, value, traceback):
        return self.__lock.__exit__(type, value, traceback)

    def __repr__(self):
        return "<Condition(%s, %d)>" % (self.__lock, len(self.__waiters))

    def _release_save(self):
        self.__lock.release()

    def _acquire_restore(self, x):
        self.__lock.acquire()

    def _is_owned(self):
        if self.__lock.acquire(0):
            self.__lock.release()
            return False
        else:
            return True

    def wait(self, timeout=None):
        if not self._is_owned():
            raise RuntimeError("cannot wait on un-acquired lock")
        waiter = Lock()
        waiter.acquire()

        self.__waiters.append(waiter)
        saved_state = self._release_save()
        try: # restore state no matter what (e.g., KeyboardInterrupt)
            if timeout is None:
                waiter.acquire()
            else:
                # Balancing act: We can't afford a pure busy loop, so we have
                # to sleep; but if we sleep the whole timeout time, we'll be
                # unresponsive. The scheme her sleeps very little at first,
                # longer as time goes on, but never longer than 20 times per
                # second (or the timeout time remaining).
                endtime = _time() + timeout
                delay = 0.0005 

                while True:
                    gotit = waiter.acquire(0)
                    if gotit:
                        break
                    remaining = endtime - _time()
                    if remaining <= 0:
                        break

                    # The delay is the least between 2x the delay, the time remaining and/or .05
                    delay = min(delay * 2, remaining, 0.05)

                    _sleep(delay)

                if not gotit:
                    try:
                        self.__waiters.remove(waiter)
                    except ValueError:
                        pass
        finally:
            self._acquire_restore(saved_state)

    def notify(self, n=1):
        if not self._is_owned():
            raise RuntimeError("cannot notify on an un-acquired lock")
        __waiters = self.__waiters
        waiters = __waiters[:n]
        if not waiters:
            return
        for waiter in waiters:
            waiter.release()
            try:
                __waiters.remove(waiter)
            except ValueError:
                pass

    def notify_all(self):
        self.notify(len(self.__waiters))


class Semaphore(object):
    def __init__(self, value=1):
        if value < 0:
            raise ValueError("semaphore initial value must be >= 0")
        self.__cond = Condition(Lock())
        self.__value = value

    def acquire(self, blocking=1):
        rc = False
        self.__cond.acquire()

        while self.__value == 0:
            if not blocking:
                break
            self.__cond.wait()
        else:
            self.__value = self.__value - 1
            rc = True
        self.__cond.release()
        return rc

    __enter__ = acquire

    def release(self):
        self.__cond.acquire()
        self.__value = self.__value + 1
        self.__cond.notify()
        self.__cond.release()

    def __exit__(self, type, value, traceback):
        self.release()

class BoundedSemaphore(Semaphore):
    def __init__(self, value=1):
        Semaphore.__init__(self, value)
        self._initial_value = value

    def release(self):
        if self.Semaphore__value >= self._initial_value:
            raise ValueError("Semaphore released too many times")
        return Semaphore.release(self)

class Event(object):

    def __init__(self):
        self.__cond = Condition(Lock())
        self.__flag = False

    def _reset_internal_locks(self):
        self.__cond.__init__()

    def is_set(self):
        return self.__flag

    def set(self):
        self.__cond.acquire()
        try:
            self.__flag = True
            self.__cond.notify_all()
        finally:
            self.__cond.release()

    def clear(self):
        self.__cond.acquire()
        try:
            self.__flag = False
        finally:
            self.__cond.release()

    def wait(self, timeout=None):
        self.__cond.acquire()
        try:
            if not self.__flag:
                self.__cond.wait(timeout)
            return self.__flag
        finally:
            self.__cond.release()

class Queue:
    pass
