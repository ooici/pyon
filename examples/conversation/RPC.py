from gevent import spawn
from gevent import queue as gqueue
from pyon.net.transport import NameTrio
from pyon.net import channel
from pyon.net import messaging
from pyon.net import conversation
from pyon.net.conversation import ConversationOriginator, Conversation, Principal, RPCServer, RPCClient

node, ioloop_process = messaging.make_node()

def start_server(queue_name):
    server  = RPCServer(node, NameTrio('seller', queue_name), 'buy_bonds')
    server.listen()

def run_client(queue_name):
    client = RPCClient(node, NameTrio('buyer'), NameTrio('seller', queue_name))
    client.buy_bonds('Ihu from buy_bonds')

