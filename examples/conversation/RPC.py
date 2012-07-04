from gevent import spawn
from gevent import queue as gqueue
from pyon.net.transport import NameTrio
from pyon.net import channel
from pyon.net import messaging
from pyon.net import conversation
from pyon.net.conversation import ConversationOriginator, Conversation, Principal, RPCServer, RPCClient

def start_server():
    node, ioloop_process = messaging.make_node()
    server  = RPCServer(node, NameTrio('seller', 'seller_queue82'), 'buy_bonds')
    server.listen()
    server.close() # Is that correct

def run_client():
    node, ioloop_process = messaging.make_node()
    client = RPCClient(node, NameTrio('buyer', 'buyer_queue42'), NameTrio('seller', 'seller_queue82'))
    client.buy_bonds('Ihu from buy_bonds')
    client.close() # Is that correct

