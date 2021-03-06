#!/usr/bin/env python

__author__ = 'Adam R. Smith,Luke'

import gevent
import os
import fcntl
from gevent.event import Event
from collections import Iterable
from functools import wraps
import time
from pyon.util.threading import Queue, get_pythread, get_pytime


spawn = gevent.spawn

def spawnf(f):
    """ Decorator to spawn this function in a greenlet. """
    @wraps(f)
    def wrapper(*args, **kwargs):
        return gevent.spawn(f, *args, **kwargs)
    return wrapper

def asyncf(f):
    """ Decorator to spawn this function in a greenlet and return the result inline. """
    @wraps(f)
    def wrapper(*args, **kwargs):
        g = gevent.spawn(f, *args, **kwargs)
        return g.get()
    return wrapper

def switch():
    """ Shortcut to give control from the current greenlet back to the gevent hub. """
    gevent.getcurrent().switch()

def join(green_stuff):
    """ Universal way to join on either a single greenlet or a list of them. """
    if isinstance(green_stuff, Iterable):
        return gevent.joinall(green_stuff)
    return gevent.join(green_stuff)

def wait(green_stuff):
    """ Universal way to join on either a single greenlet or a list of them and get return value inline. """
    if isinstance(green_stuff, Iterable):
        gevent.joinall(green_stuff)
        return [g.get() for g in green_stuff]
    return green_stuff.get()

def blocking_cb(func, cb_arg, *args, **kwargs):
    """
    Wrap a function that takes a callback as a named parameter, to block and return its arguments as the result.
    Really handy for working with callback-based APIs. Do not use in really frequently-called code.
    If keyword args are supplied, they come through in a single dictionary to avoid out-of-order issues.
    """
    ev = Event()
    ret_vals = []
    def cb(*args, **kwargs):
        ret_vals.extend(args)
        if len(kwargs): ret_vals.append(kwargs)
        ev.set()
    kwargs[cb_arg] = cb
    func(*args, **kwargs)
    ev.wait(timeout=10)
    if len(ret_vals) == 0:
        return None
    elif len(ret_vals) == 1:
        return ret_vals[0]
    return tuple(ret_vals)

#--------------------------------------------------------------------------------

def nonblock_pipe():
    r, w = os.pipe()
    fcntl.fcntl(r, fcntl.F_SETFD, os.O_NONBLOCK)
    fcntl.fcntl(w, fcntl.F_SETFD, os.O_NONBLOCK)
    return r,w 

_async_pipe_read, _async_pipe_write = nonblock_pipe()

def _async_pipe_read_callback(event, evtype):
    '''
    libevent callback to read from the pipe
    '''
    try:
        os.read(event.fd, 1)
    except EnvironmentError:
        pass # EAGAIN

# create a libevent callback to read from the pipe
gevent.core.event(gevent.core.EV_READ | gevent.core.EV_PERSIST,
                  _async_pipe_read,
                  _async_pipe_read_callback).add() 
                  

class AsyncResult(gevent.event.AsyncResult):
    def __init__(self):
        gevent.event.AsyncResult.__init__(self)

    def get(self, *args, **kwargs):
        return gevent.event.AsyncResult.get(self, *args, **kwargs)

    def set_exception(self, exception):
        gevent.event.AsyncResult.set_exception(self, exception)
        os.write(_async_pipe_write, '\0')

    def set(self, value):
        gevent.event.AsyncResult.set(self, value)
        os.write(_async_pipe_write, '\0')


class AsyncEvent(gevent.event.Event):
    '''
    A gevent-friendly event to be signaled by a posix thread and respected by 
    the gevent context manager.


    Essentially the posix thread signals gevent through a nonblocking pipe
    '''

    def __init__(self):
        gevent.event.Event.__init__(self)
        self._r, self._w = self._pipe() # non blocking pipe

        # Create a new gevent core object that will observe the
        # nonblocking pipe file descriptor for a value
        self._core_event = gevent.core.event(
                gevent.core.EV_READ | gevent.core.EV_PERSIST,
                self._r,
                self._pipe_read)
        self._core_event.add()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._close()

    def _pipe(self):
        return nonblock_pipe()

    def _pipe_read(self, event, eventtype):
        '''
        Non-blocking gevent friendly core event callback
        http://www.gevent.org/gevent.core.html#events
        '''
        try:
            os.read(event.fd, 1)
        except EnvironmentError:
            # file descriptors set with O_NONBLOCK return -1 and set errno to
            # EAGAIN, we just want to ignore it and try again later
            pass
        

    def set(self):
        '''
        Sets the event value and writes a value to the pipe to
        trigger the gevent core event
        '''

        gevent.event.Event.set(self)
        os.write(self._w, '\0') # Empty C-string '\0'

    def _close(self):
        '''
        Closes the core event, the read and write file descriptors
        '''
        if getattr(self, '_core_event', None):
            try:
                self._core_event.cancel()
            except:
                pass
        if getattr(self, '_r', None):
            try:
                os.close(self._r)
            except:
                pass
        if getattr(self, '_w', None):
            try:
                os.close(self._w)
            except:
                pass

class AsyncTask(object):
    '''
    A structure to represent the elements of a threadable task
    '''
    def __init__(self, callback, *args, **kwargs):
        self.ar = AsyncResult()
        self.callback = callback
        self.args = args
        self.kwargs = kwargs


class ThreadExit(Exception):
    def __init__(self):
        self.ar = AsyncResult()

class ThreadJob(object):
    '''
    A thread pool worker
    '''
    def __init__(self, queue):
        self.queue = queue

    def sleep(self, n):
        '''
        Sleeps n seconds using the un-patched time module
        '''
        pytime = get_pytime()
        pytime.sleep(n)

    def run(self):
        '''
        Runs a loop, listening for tasks
        '''
        while True:
            entry = self.queue.get(block=True)
            try:
                # If the entry is a ThreadExit, break the loop and exit from the thread
                if isinstance(entry, ThreadExit):
                    entry.ar.set(True)
                    break

                # An unrecognized task
                elif not isinstance(entry, AsyncTask):
                    raise Exception("Invalid task")

                ar = entry.ar
                callback = entry.callback
                args = entry.args
                kwargs = entry.kwargs
                # If a task raises or fails then just print the stack trace and
                # continue processing
                try:
                    retval = callback(*args, **kwargs)
                    ar.set(retval)
                except Exception as e:
                    from traceback import print_exc
                    print_exc()
                    # Note: the AR has an exception set so clients can observe task status
                    ar.set_exception(e)
            finally:
                self.queue.task_done()



'''
Thread Pool Limitations:
    - Any thread task that imports a gevent monkey-patched module will probably
      raise an exception if gevent tries to context switch while in the child
      thread.
    - When closing threads, it is VERY prudent to synchronize the threads,
      otherwise the threads will be dangling.
    - Currently, there is no way to force a thread to quit, especially since
      most of these threads probably won't be running in the python
      interpreter. We could use the pthread library to forcefully quit a
      thread, but the memory could leak and it could cause some serious issues
      in the interpreter.
    - If a timeout is placed on synchronizing closing threads, a SystemError is
      raised, the intent with this is to fast fail a container. If threads
      aren't synchronized in time and a timeout is applied, then there is a
      bigger problem. 
      - If only a subset of threads are closed, but the alive ones are still
        listening on the queue, you wind up with an inconsistent thread pool,
        and reliably executing tasks on the pool and managing what the pool
        believes to be the correct number of threads, becomes a stochastic
        system.

Advisements:
    - Keep the thread tasks as small as possible.
    - Try to limit the uses to only the code that absolutely blocks gevent.
    - If a thread blocks too long, it may be advisable to increase the threadpool temporarily.

Based on the concepts presented by the gevent-playground module:
https://bitbucket.org/denis/gevent-playground/src/61bb12c9b4e41b58a763a7ef53fbe9a89cea1e04/geventutil/threadpool.py?at=default
'''



class ThreadPool(object):
    '''
    A pool of threads that can be used to run gevent-blocking code
    
    pool = ThreadPool(10)
    '''
    def __init__(self, poolsize=5):
        self.poolsize = poolsize
        self.queue = Queue()
        self.pythread = get_pythread()
        self.active = False
        # sets active to True
        self._spawn_threads(self.poolsize)

    def _spawn_threads(self, num):
        for i in xrange(num):
            job_worker = ThreadJob(self.queue)
            self.pythread.start_new_thread(job_worker.run, tuple())
        self.active = True

    def _check_exit(self, n, sync=False, timeout=None):
        exits = []
        for i in xrange(n):
            exit = ThreadExit()
            exits.append(exit)
            self.queue.put(exit)

        if not sync:
            return # No synchronization probably not good...

        self._inner_check(exits, timeout)


    def _inner_check(self, exits, timeout=None):
        if timeout is not None:
            t0 = time.time()
        i = len(exits)
        while i > 0:
            if timeout is not None and time.time() > (t0 + timeout):
                raise SystemError("Failed to close and synchronize threads. Thread pool is now inconsistent")
            for exit in exits:
                if exit.ar.ready():
                    i-=1


    def resize(self, newsize, sync=False, timeout=None):
        '''
        Resizes the available pool

        If `sync` is set and the thread pool is reduced, the method will
        synchronize with each exiting thread to ensure an exit was successful.
        If `timeout` is set with the `sync` a SystemError will be raised if the
        timeout is exceeded.
        '''
        assert newsize > 0, "Must have a positive number of threads"
        if newsize > self.poolsize:
            n = newsize - self.poolsize
            self._spawn_threads(n)
        else:
            n = self.poolsize - newsize
            self._check_exit(n, sync, timeout)

        self.poolsize = newsize


    def apply_async(self, func, *args, **kwargs):
        '''Run func, using the given args and kwargs in the thread pool.
        Returns :class:`AsyncResult`
        '''

        assert self.active, "Thread pool is deactivated"

        task = AsyncTask(func, *args, **kwargs)
        self.queue.put(task)
        return task.ar

    def apply(self, func, *args, **kwargs):
        '''Run func, using the given args and kwargs in the thread pool,
        but block the current greenlet until the result is ready.
        Returns the value from func after execution'''

        assert self.active, "Thread pool is deactivated"

        task = AsyncTask(func, *args, **kwargs)
        self.queue.put(task)
        retval = task.ar.get()
        return retval

    def close(self, sync=False, timeout=None):
        '''
        Sends each thread an Exit exception and deactivates the thread pool. If
        `sync` is set to True, the ThreadPool with synchronize with each thread
        before close returns. If `timeout` is set to a postive number and
        `sync` is set, then a SystemError will be raised if the timeout is
        exceeded before the threads have exited.
        
        Raises SystemError if timeout is exceeded before all the threads have exited.
        '''
        self._check_exit(self.poolsize, sync, timeout)
        self.active = False

    def map(self, func, arg_list):
        '''
        Takes a function and an iterable argument list.
        Runs func against each argument list in the iterable and returns a list
        of results, the results list will block the current greenlet in a
        gevent-safe way.
        '''
        jobs = self.map_async(func, arg_list)
        gevent.event.waitall(jobs)
        return jobs

    def map_async(self, func, arg_list):
        '''
        Takes a function and an iterable argument list.
        Runs func using each argument list in the iterable and returns a list
        of AsyncResult objects.
        '''
        async_jobs = [self.apply_async(func, *i) for i in arg_list]
        return async_jobs


class AsyncDispatcher(object):
    '''
    Used to synchronize a result obtained in a pythread to a gevent thread
    To use:

    with AsyncDispatcher(callback, arg1, arg2, keyword=argument) as dispatcher:
        v = dispatcher.wait(10)

    The concurrency is NOT thread safe, do not attempt to modify shared regions inside the
    dispatcher's context, it is solely meant to allow os threads to operate concurently
    with greenlets.
    '''
    _value     = None
    _exception = None
    _set       = None
    event      = None

    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args     = args
        self.kwargs   = kwargs

    def __enter__(self):
        self.event = AsyncEvent()
        self.event.__enter__()
        pythread = get_pythread()
        self._thread = pythread.start_new_thread(self.dispatch, (self.callback,) + self.args, self.kwargs)
        return self

    def __exit__(self, type, value, traceback):
        self.event.__exit__(type, value, traceback)

    def dispatch(self, callback, *args, **kwargs):
        '''
        Runs a callback, either sets an asynchronous value or an exception
        When the os thread completes, the event is set to signal gevent that it's complete
        '''
        try:
            retval = callback(*args, **kwargs)
            self._value = retval
        except Exception as e:
            self._exception = e
        self.event.set()

    def wait(self, timeout=None):
        '''
        Blocks the current gevent greenlet until a value is set or the timeout expires.
        If the timeout expires a Timeout is raised.
        If the callback raised an exception in the os thread, an exception is raised here.
        '''
        if self.event.wait(timeout):
            if self._exception:
                raise self._exception
            else:
                return self._value
        else:
            raise gevent.timeout.Timeout(timeout)


