from pyon.util.int_test import IonIntegrationTestCase
from interface.services.examples.hello.ihello_service import HelloServiceClient

class TestHelloService(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()
        self.container.start_rel_from_url('res/deploy/examples/hello.yml')
        self.hsc = HelloServiceClient()

    def test_hello(self):

        ret = self.hsc.hello("emm")
        self.assertEquals(ret, "BACK:emm")



