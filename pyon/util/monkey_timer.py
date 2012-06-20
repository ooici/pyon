""" timer to wrap specific methods and calculate how long they take to execute.

    general usage:

        t = MonkeyTimer()
        ... patch functions or classes ...
        ... do some work ...
        print t.results()

    to patch a top-level function:

        import module  # NOT: from module import function
        module.function = t.patch_function(module.function, 'fun stats')

    to patch a function in a class:

        import module  # NOT: from module import SomeClass
        module.SomeClass = t.patch_class_one(module.SomeClass, module.SomeClass.some_function, 'some stats')

    to patch all functions in a class (or subset matching regex):

        import module  # NOT: from module import SomeClass
        module.SomeClass = t.patch_class_all(module.SomeClass, 'stats.')

    patches with the same name string are combined.  for example, these three functions will all be reported as 'http stats':

        module.get = t.patch_function(module.get, 'http stats')
        module.put = t.patch_function(module.put, 'http stats')
        module.head = t.patch_function(module.head, 'http stats')

    the results() shows cumulative time spent in function, # calls to function and average time per call.

    the job is complicated by the gevent model -- any blocking call could allow control to switch to a different thread,
    so the sum of the times of overlapping methods could exceed total clock time of the program.

    to address this, the results() output also includes "fractional" time.  if two or calls are made to traced functions
    (the same function from two threads or different traced functions) and the call times overlap, then a fraction of the
    overlapping time is attributed to each function.  for example, if two functions overlap for a 2sec period, then each
    function adds 1sec of execution time to its tally.  the total fractional time shown across all functions will not
    exceed the elapsed execution time, but the relative proportion of time taken by the traced functions gives each
    call equal weight.
"""

from time import time
from types import MethodType
from inspect import getmembers, ismethod
from re import match
from threading import Lock
from traceback import extract_stack

from pyon.util import log
class _Wrapper(object):
    """ replacement for function to be timed """
    def __init__(self, timer, function, name, logger):
        self._original = function
        self._timer = timer
        self._name = name
        self._simultaneous = 0
        self._log = logger
    def proxy(self, *a, **b):
        if self._log:
            for frame in reversed(extract_stack()):
                file = frame[0]
                if not file.endswith('monkey_timer.py'):
                    line = frame[1]
                    self._log.info(self._name + ' called by ' + file + ':' + str(line))
                    break
            tuple = extract_stack()[-2]
#            log.error(tuple[0] + ':' + str(tuple[1]))

        self._simultaneous+=1
        start = self._timer._start_timing()
        try:
            return self._original(*a, **b)
        finally:
            self._timer._stop_timing(self, start)
            self._simultaneous-=1
    def __str__(self):
        return self._name

class _Call(object):
    """ track one in-flight call of a wrapped function """
    def __init__(self, index):
        self.proportional_time = 0
        self._index = index
    def add_time(self, elapsed):
        self.proportional_time += elapsed
    def start(self, time):
        self._start_time = time
    def stop(self, time):
        self.clock_time = time - self._start_time
    def __str__(self):
        return 'call %d'%self._index
    def __repr__(self):
        return self.__str__()

class MonkeyTimer(object):
    """ utility to wrap methods and track time used by calls made to them """
    def __init__(self, nooverlap=False):
        # map by wrapper
        self._proportional_time = {}
        self._clock_time = {}
        self._total_count = {}

        self._lock = Lock()
        self._last_tick = None
        self._currently_running = []
        self._max_simultaneous = 0
        self._call_index = 1
        self.logger = None

    def set_logger(self, logger):
        """ if set, will log caller of each wrapped function """
        self.logger = logger

    def _add_time(self, elapsed):
        # add fraction of elapsed time to each overlapping call
        running_count = len(self._currently_running)
        if running_count:
            self._max_simultaneous = max(self._max_simultaneous,running_count)
            delta = elapsed/running_count
            for call in self._currently_running:
                call.add_time(delta)

    def _start_timing(self):
        # called by wrapper when method call starts: track start time
        self._lock.acquire()
        this_tick = time()
        new_call = _Call(self._call_index)
        self._call_index+=1
        new_call.start(this_tick)
        if self._last_tick:
            self._add_time(this_tick - self._last_tick)
        self._last_tick = this_tick
        self._currently_running.append(new_call)
        self._lock.release()
        return new_call

    def _stop_timing(self, wrapper, call):
        # called by wrapper when method call completes: add time to running calls
        self._lock.acquire()
        this_tick = time()
        call.stop(this_tick)
        self._add_time(this_tick - self._last_tick)
        self._last_tick = this_tick
        self._currently_running.remove(call)
        self._lock.release()

        # update call type with total time
        key = str(wrapper)
        if key not in self._proportional_time:
            self._proportional_time[key] = 0
            self._clock_time[key] = 0
            self._total_count[key] = 0
        self._proportional_time[key] += call.proportional_time
        self._clock_time[key] += call.clock_time
        self._total_count[key] += 1

    def patch_function(self, function, name, logger=None):
        """ return wrapped version of function """
        wrapper_log = logger if logger else self.logger
        wrapper = _Wrapper(self, function, name, wrapper_log)
        return wrapper.proxy

    def patch_class_one(self, clazz, function, name):
        """ return replacement class with one function wrapped """
        if hasattr(clazz, '_monkey_timer_patched'):
            raise Exception('can only patch once with patch_class')
        timer = self
        class _ProxyClass(clazz):
            def __init__(self, *a, **b):
                orig = clazz.__dict__[function.__name__]
                self.__dict__[function.__name__] = MethodType(timer.patch_function(orig, name), self, _ProxyClass)
                clazz.__init__(self, *a, **b)
        _ProxyClass._monkey_timer_patched = True
        return _ProxyClass

    def patch_class_all(self, clazz, prefix, regex='^[^_]'):
        """ return replacement class with all functions wrapped that match regex """
        if hasattr(clazz, '_monkey_timer_patched'):
           raise Exception('can only patch once with patch_class')
        timer = self
        class _ProxyClass(clazz):
            def __init__(self, *a, **b):
                for name, function in getmembers(clazz, predicate=ismethod):
                    if not regex or match(regex, name):
                        self.__dict__[name] = MethodType(timer.patch_function(function, prefix + name), self, _ProxyClass)
                clazz.__init__(self, *a, **b)
        _ProxyClass._monkey_timer_patched = True
        return _ProxyClass

    def results(self):
        """ return a string describing times of calls to all wrapped functions """
        lines = ["function\tfractional time\tcumulative time"]
        self._lock.acquire()
        for key in self._proportional_time.keys():
            time = self._proportional_time[key]
            clocktime = self._clock_time[key]
            count = self._total_count[key]
            lines.append("%s:\t%.3e / %d = %.3e\t%.3e / %d = %.3e" % (key, time, count, time/count, clocktime, count, clocktime/count))
        self._lock.release()
        return "\n".join(lines) + ("\n%d simultaneous"%self._max_simultaneous)

    def reset(self):
        """ reset all timing results (does not apply to in-flight calls """
        self._lock.acquire()
        self._proportional_time = {}
        self._clock_time = {}
        self._total_count = {}
        self._lock.release()
