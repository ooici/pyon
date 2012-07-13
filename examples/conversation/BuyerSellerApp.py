from gevent import spawn
from gevent import queue as gqueue
from pyon.net.transport import NameTrio
from pyon.net import channel
from pyon.net import messaging
from pyon.net import conversation
from pyon.net.conversation import Conversation, Principal,InitiatorPrincipal, GuestPrincipal

node, ioloop_process = messaging.make_node()
def buyer_app(queue_name):
    #principal initialisation
    customer = InitiatorPrincipal(node, NameTrio('buyer', 'buyer_queue'))

    # conversation bootstrapping
    c = customer.start_conversation(protocol = 'buyer_seller', role ='buyer')
    c.invite(to_role = 'seller', to_role_addr = NameTrio('seller', queue_name))

    #interactions
    c.send('seller', 'I will send you a request shortly. Please wait for me.')
    c.send('seller', 'How expensive is War and Piece?')
    msg, header = c.recv('seller')
    print 'Msg received: %s' % (msg)

    #cleaning
    customer.stop_conversation()

def seller_app(queue_name):
    #principal initialisation
    stock_provider = GuestPrincipal(node, NameTrio('seller', queue_name))
    stock_provider.start_listening()

    #joining a conversation (bootstrapping)
    conv, msg, header  = stock_provider.get_invitation()
    c = stock_provider.accept_invitation(conv, msg, header, auto_reply = 'True')

    #interactions
    msg, header = c.recv('buyer')
    print 'Msg received: %s' %(msg)
    msg, header = c.recv('buyer')
    print 'Msg received: %s' %(msg)
    c.send('buyer', '3000 pounds')

    stock_provider.stop_listening()
