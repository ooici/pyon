
__author__ = 'sphenrie'


from pyon.public import Container
from pyon.net.endpoint import ProcessRPCClient
from pyon.util.context import LocalContextMixin

from interface.services.examples.hello.ihello_service  import HelloServiceProcessClient

class FakeProcess(LocalContextMixin):
    name = ''

def hello_client(container, user_id='anonymous', org_id='no-ooi'):

   # client = ProcessRPCClient(node=container.node, name="hello", iface=IHelloService,  process=FakeProcess())

    try:
        client = HelloServiceProcessClient(node=container.node, process=FakeProcess())

        ret = client.hello(" initial text sent is 123 ", headers={'ion-user-id': user_id, 'ion-org-id': org_id})

        print "Returned: " + str(ret)
    except Exception, e:
        print "client.hello() failed: " + e.message



if __name__ == '__main__':

    container = Container()
    container.start() # :(
    hello_client(container, user_id='shenrie',org_id='ooi')
    container.stop()
