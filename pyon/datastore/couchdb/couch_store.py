""" WORK IN PROGRESS:  eventual goal is to have this class perform all couchdb operations and be completely unaware of Ion-specific objects or container-specific settings

    responsible for:
    - operations accept single or list of objects or ids as appropriate
    - return types are generally tuple or list of tuple: (success, id, object)

"""

from couchdb import Server
from couchdb.http import ResourceConflict, ResourceNotFound
from pyon.core.exception import BadRequest, Conflict, NotFound, ServerError
from pyon.util.log import log


class CouchStore(object):
    """ represents one couch DB instance """
    def __init__(self, instance, server='localhost', port=5984, username=None, password=None, can_create=False, must_create=False, max_retry=2):
        self._url = 'http://%s:%s@%s:%d' % (username, password, server, port) \
                    if username else 'http://%s:%d' % (server, port)
        self._db_name = instance
        self._server_name = server
        self._max_retry = max_retry

        self._server = Server(self._url)
        if can_create or must_create:
            try:
                log.debug('creating %s on %s', instance, self._url)
                self._db = self._server.create(self._db_name)
            except Exception, e:
                if must_create:
                    raise self._wrap_error('initialize', self._db_name, e)
        else:
            log.debug('connecting to %s on %s', instance, server)
            self._db = self._server[self._db_name]

    def drop(self):
        log.debug('deleting %s from %s', self._db_name, self._server_name)
        self._server.delete(self._db_name)
        self._db = None

    def _is_list(self, op, target):
        # check that argument is string, dictionary or list of ONE of them
        if isinstance(target, str) or isinstance(target, dict):
            return False
        elif all(isinstance(t, str) for t in target) or all(isinstance(t, dict) for t in target):
            return True
        else:
            BadRequest('CouchDB ' + op + ' takes string, dictionary or list of one of them')

    # check that arg, or if list all items in arg, have _rev attribute (expected=True) or do not have (expected=False)
    def _check_attr(self, arg, name, expected):
        if isinstance(arg, dict):
            return (name in arg.keys()) == expected
        items = [name in item.keys() for item in arg]
        if expected:
            return reduce(lambda a, b: a and b, items)
        else:
            return not reduce(lambda a, b: a or b, items)

    def _wrap_error(self, op, id, ex):
        return ServerError('CouchDB %s of object %s failed with error %s(%s)' % (op, id, type(ex).__name__, str(ex)))

    def insert(self, target):
        """ insert one or many entries.  must have _id and must not have _rev

            if target is a list, docs are updated with _rev, but not if target is dict
            (side effect of underlying library)

            returns tuple (success, _id, Exception) when target is a dictionary
            returns list of tuples when target is a list

        """
        if not self._check_attr(target, '_rev', False):
            raise Conflict('cannot insert document with revision')
        if not self._check_attr(target, '_id', True):
            raise BadRequest('inserted documents must have _id')

        if isinstance(target, list):
            return self._db.update(target)
        else:
            id = target['_id']
            try:
                self._db.create(target)
                return True, id, None
            except ResourceConflict, e:
                return False, id, BadRequest('Object with id %s already exists' % id)
            except Exception, e:
                return False, id, self._wrap_error('insert', id, e)

    # TODO: repository can raise exception if don't read all docs
    def read(self, target):
        """ read one or many entries """
        if isinstance(target, list):
            ids = [t['_id'] if isinstance(t, dict) else t for t in target]
            rows = self._db.view('_all_docs', keys=ids, include_docs=True)
            return [(row.doc is not None, row.id, row.doc) for row in rows]

        # else target is an id
        id = target['_id'] if isinstance(target, dict) else target
        try:
            doc = self._db[id]
            return doc is not None, id, doc
        except ResourceNotFound:
            return False, id, NotFound('Object %s does not exist' % id)
        except Exception, e:
            return False, id, self._wrap_error('read', id, e)

    def update(self, target, force=False, _depth=0):
        """ update one or many entries

            if force is False and _rev is missing or not the latest, the update will fail.
            if force is True and _rev is missing or not the latest, will find the latest _rev and attempt to update.
            since others may be updating at the same time, this may still not be the latest!
            update will repeat up to max_retry times before giving up.

            return value for a single item update is a tuple (success, id, exception)
            return value when target is a list is a list of tuples indicating the outcome of each item updated.

            NOTE: updates may not made to DB in order.
        """
        if not isinstance(target, list):
            result = self.update([target], force=force)
            return result[0]

        # update the ones that already have revisions
        have_revisions = filter(lambda d: '_rev' in d.keys(), target)
        results = self._db.update(have_revisions) if len(have_revisions) else None

        # if missing or old _rev, retry update
        log.debug('update results: %s', repr(results))
        some_attempted = len(have_revisions) > 0
        some_failed = some_attempted and not reduce(lambda a, b: a and b, [r[0] for r in results])
        some_not_updated = len(have_revisions) < len(target) or some_failed
        can_retry = force and _depth < self._max_retry
        if can_retry and some_not_updated:
            # start with elements that did not have _rev
            retry_target = filter(lambda d: '_rev' not in d.keys(), target)
            # now add elements that failed due to wrong _rev
            successful_results = []
            if results:
                doc_with_result = zip(have_revisions, results)
                failed_subset_with_result = filter(lambda t: not t[1][0], doc_with_result)  # TODO: also check t[1][2] is correct exception type for bad _rev
                retry_target += [t[0] for t in failed_subset_with_result]
                successful_results = [t[1] for t in filter(lambda t: t[1][0], doc_with_result)]
            # search db and update these _rev values
            log.debug(' before %s', repr(retry_target))
            self._update_revision(retry_target)
            log.debug('  after %s', repr(retry_target))
            # some just aren't in the DB any more
            not_found_docs = filter(lambda t: '_rev' not in t, retry_target)
            not_found_results = [(False, t['_id'], Exception('not found in DB')) for t in not_found_docs]  # TODO: use application exception
            # for otehrs, try again with udpated _rev
            found_rev = filter(lambda t: '_rev' in t, retry_target)
            retry_results = self.update(found_rev, force=True, _depth=_depth + 1)

            results = not_found_results + retry_results + successful_results

        # only need to sort once on final exit from recursive retry
        if _depth > 1:
            return results

        # sort results into original order of arguments
        out = []
        for d in target:
            id = d['_id']
            result = None
            if results:
                for t in results:
                    if t[1] == id:
                        result = t
                        break
            if not result:   # no revision?
                if force:    # force: would have read latest from DB -- so _id was not found
                    result = (False, id, Exception("udpate failed: _id was not found"))
                else:        # no force: then cannot update
                    result = (False, id, Exception("update failed without _rev or force"))
            out.append(result)
        return out

    def _update_revision(self, target):
        # update dictionaries to have the latest _rev from the DB
        ids = [d['_id'] for d in target]
        results = self._db.view('_all_docs', keys=ids)
        for result in results:
            id = result.id
            for d in target:
                if d['_id'] == id:
                    d['_rev'] = result.value['rev']
                    break

    def delete(self, target, force=False):
        """ delete one more multiple entries """
        is_list = self._is_list('delete', target)
        is_ids = isinstance(target[0], str) if is_list else isinstance(target, str)

        # convert arg into list of dictionaries with _id, _delete=True and optionally _rev
        if is_ids:
            if is_list:
                # list of ids
                dicts = [{'_id':t, '_deleted': True} for t in target]
            else:
                # single id
                dicts = {'_id': target, '_deleted': True}
        else:
            # TODO: smaller delete if only pass _id, _rev and _deleted (drop other entries in dict)
            dicts = target
            if is_list:
                # list of dictionaries
                for t in target:
                    t['_deleted'] = True
            else:
                # single dictionary
                dicts['_deleted'] = True

        return self.update(dicts, force=force or is_ids)

    def create_view(self):
        pass

    def query_view(self):
        pass
