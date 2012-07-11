from gevent import spawn
from gevent import queue as gqueue
from pyon.net.transport import NameTrio
from pyon.net import channel
from pyon.net import messaging
from pyon.net import conversation
from pyon.net.conversation import ConversationOriginator, Conversation, Principal

node, ioloop_process = messaging.make_node()
def buyer_app(queue_name):
    #principal initialisation
    originator = ConversationOriginator(node, NameTrio('buyer', 'buyer_queue'))

    # conversation bootstrapping
    c = originator.start_conversation('buyer_seller', 'buyer')
    c.invite('seller', NameTrio('seller', queue_name))

    #interactions
    c.send('seller', 'Hello1')
    c.send('seller', 'Hello2')
    msg, header = c.recv('seller')
    print 'Msg received: %s' % (msg)

    #cleaning
    c.close()
    originator.stop_listening()

def seller_app(queue_name):
    #principal initialisation
    local = Principal(node, NameTrio('seller', queue_name))
    local.spawn_listener()

    #joining a conversation (bootstrapping)
    conv, msg, header  = local.get_invitation()
    c = local.accept_invitation(conv, msg, header, auto_reply = 'True')

    #interactions
    msg, header = c.recv('buyer')
    print 'Msg received: %s' %(msg)
    msg, header = c.recv('buyer')
    print 'Msg received: %s' %(msg)
    c.send('buyer', 'Hello3')

    #cleaning
    c.close()
    local.stop_listening()
