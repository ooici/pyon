
from pyon.core.exception import *

from nose.plugins.attrib import attr
from unittest import TestCase


from pyon.core import log as log_config
from pyon.util.log import log

@attr('UNIT')
class TestExceptionUtils(TestCase):
    def setUp(self):
        log_config.configure_logging( [ 'res/config/logging.yml', 'res/config/logging.local.yml'] )

    def throw_caused(self):
        try:
            raise Unauthorized('inner')
        except:
            raise BadRequest('outer')

    def test_stacks(self):
        try:
            self.throw_caused()
        except:
            log.exception('ion caused by python')