#!/usr/bin/env python

__author__ = 'Adam R. Smith, Dave Foster <dfoster@asascience.com>'


from pyon.util.log import log

class IDPool(object):
    """
    Create a pool of IDs to allow reuse.
    The "new_id" function generates the next valid ID from the previous one. If not given, defaults to
    incrementing an integer.
    """

    def __init__(self, new_id=None):
        if new_id is None: new_id = lambda x: x + 1

        self._ids_in_use = set()
        self._ids_free = set()
        self._new_id = new_id
        self._last_id = 0

    def get_id(self):
#        log.debug("IDPool.get_id\n\tisfree: %s\n\tidsinuse: %s", self._ids_free, self._ids_in_use)
        if len(self._ids_free) > 0:
            id = self._ids_free.pop()
            self._ids_in_use.add(id)
#            log.debug("id: %s" % str(id))
            return id

        self._last_id = id_ = self._new_id(self._last_id)
        self._ids_in_use.add(id_)
#        log.debug("id: %s" % str(id_))
        return id_

    def release_id(self, the_id):
#        log.debug("IDPool.release_id(%s)", the_id)

        if the_id in self._ids_in_use:
            self._ids_in_use.remove(the_id)
            self._ids_free.add(the_id)