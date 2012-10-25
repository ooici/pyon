
__author__ = 'sphenrie'


from pyon.public import Container, ImmediateProcess
#from pyon.ion.endpoint import ProcessRPCClient
from pyon.util.context import LocalContextMixin

from interface.services.examples.hello.ihello_service  import HelloServiceProcessClient
from interface.services.icontainer_agent import ContainerAgentProcessClient

class FakeProcess(LocalContextMixin):
    name = ''
    id = ''

class HelloClientProcess(ImmediateProcess):
    """
    bin/pycc -x ion.processes.bootstrap.load_system_policy.LoadSystemPolicy op=load
    """
    def on_init(self):
        pass

    def on_start(self):

        text = self.CFG.get("text", 'mytext 123')
        actor_id = self.CFG.get("actor_id", 'anonymous')
        container_name = self.CFG.get("kill_container", None)

        try:
            client = HelloServiceProcessClient(node=self.container.node, process=self)

            ret = client.hello(text, headers={'ion-actor-id': actor_id})

            print "Returned: " + str(ret)

            if container_name:
                cc_client = ContainerAgentProcessClient(node=self.container.node, process=self, name=container_name)
                cc_client.stop()

        except Exception, e:
            print "client.hello() failed: " + e.message


    def on_quit(self):
        pass

def hello_client(container, actor_id='anonymous', org_id='no-ooi', text='mytext 123'):

   # client = ProcessRPCClient(node=container.node, name="hello", iface=IHelloService,  process=FakeProcess())

    try:
        client = HelloServiceProcessClient(node=container.node, process=FakeProcess())

        ret = client.hello(text, headers={'ion-actor-id': actor_id, 'ion-org-id': org_id})

        print "Returned: " + str(ret)
    except Exception, e:
        print "client.hello() failed: " + e.message

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
