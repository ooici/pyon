
__author__ = 'sphenrie'


from pyon.public import Container, ImmediateProcess
#from pyon.ion.endpoint import ProcessRPCClient
from pyon.util.context import LocalContextMixin
from pyon.core.governance import get_actor_header

from interface.services.examples.hello.ihello_service  import HelloServiceProcessClient
from interface.services.icontainer_agent import ContainerAgentProcessClient

class FakeProcess(LocalContextMixin):
    name = 'hello_client'
    id = ''

class HelloClientProcess(ImmediateProcess):
    """
    bin/pycc -x examples.hello_client.HelloClientProcess
    """
    def on_init(self):
        pass

    def on_start(self):

        text = self.CFG.get("text", 'mytext 123')
        actor_id = self.CFG.get("actor_id", 'anonymous')
        container_name = self.CFG.get("kill_container", None)

        hello_client(self.container, actor_id, text )

        if container_name:
            cc_client = ContainerAgentProcessClient(node=self.container.node, process=self, name=container_name)
            cc_client.stop()


    def on_quit(self):
        pass

def hello_client(container, actor_id='anonymous', text='mytext 123'):

    try:
        client = HelloServiceProcessClient(node=container.node, process=FakeProcess())

        actor_headers = get_actor_header(actor_id)
        ret = client.hello(text, headers=actor_headers)
        print "Returned: " + str(ret)

        ret = client.hello('second message text', headers=actor_headers)
        print "Returned: " + str(ret)

        ret = client.noop(text='third message text', headers=actor_headers)
        print "Returned"

    except Exception, e:
        print "client.hello() failed: " + e.message

def hello_noop(container, actor_id='anonymous', text='mytext 123'):


    try:
        client = HelloServiceProcessClient(node=container.node, process=FakeProcess())

        actor_headers = get_actor_header(actor_id)
        ret = client.noop(text, headers=actor_headers)

    except Exception ,e:
        print "client.hello() failed: " + e.message


if __name__ == '__main__':

    container = Container()
    container.start() # :(
    hello_client(container, actor_id='shenrie')
    container.stop()
