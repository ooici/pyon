
__author__ = 'sphenrie'

from time import time
from pyon.public import Container
#from pyon.ion.endpoint import ProcessRPCClient
from pyon.util.context import LocalContextMixin

from interface.services.examples.hello.ihello_service  import HelloServiceProcessClient

class FakeProcess(LocalContextMixin):
    name = ''
    id = ''

def hello_client(container, actor_id='anonymous', org_id='no-ooi', text='mytext 123'):

   # client = ProcessRPCClient(node=container.node, name="hello", iface=IHelloService,  process=FakeProcess())
    start = time()
    print 'Start client at:', start
    try:
        client = HelloServiceProcessClient(node=container.node, process=FakeProcess())

        ret = client.hello(text, headers={'ion-actor-id': actor_id, 'ion-org-id': org_id})

        print "Returned: " + str(ret)
    except Exception, e:
        print "client.hello() failed: " + e.message
    finally:
        executed = time() - start
        print 'Execited in', executed


import cProfile

def wrapper(cc):
    command = 'hello_client(cc)'
    cProfile.runctx( command, globals(), locals())



def hello_noop(container, actor_id='anonymous', org_id='no-ooi', text='mytext 123'):


    try:
        client = HelloServiceProcessClient(node=container.node, process=FakeProcess())

        ret = client.noop(text, headers={'ion-actor-id': actor_id, 'ion-org-id': org_id})

    except Exception ,e:
        print "client.hello() failed: " + e.message


if __name__ == '__main__':
    container = Container()
    container.start() # :(
    hello_client(container, actor_id='shenrie',org_id='ooi')
    container.stop()
