from gevent import spawn
from gevent import queue as gqueue
from pyon.net.transport import NameTrio
from pyon.net import channel
from pyon.net import messaging
from pyon.net import conversation
from pyon.net.conversation import ConversationOriginator, Conversation, Principal

node, ioloop_process = messaging.make_node()
def buyer_app(queue_name):
    originator = ConversationOriginator(node, NameTrio('buyer', 'buyer_queue46'))
    c = originator.start_conversation('protocol', 'buyer')
    c.invite('seller', NameTrio('seller', queue_name))
    c.send('seller', 'Hello1')
    c.send('seller', 'Hello%s' %2)
    msg, header = c.recv('seller')
    print 'Msg received: %s' %(msg)
    c.close()
    originator.stop_listening()

def seller_app(queue_name):
    local = Principal(node, NameTrio('seller', queue_name))
    local.spawn_listener()
    conv, msg, header  = local.get_invitation()
    c = local.accept_invitation(conv, msg, header, auto_reply = 'True')
    msg, header = c.recv('buyer')
    print 'Msg received: %s' %(msg)
    msg, header = c.recv('buyer')
    print 'Msg received: %s' %(msg)
    c.send('buyer', 'Hello%s' %3)
    c.close() # should do some cleaning
    local.stop_listening()


# -------------------- Tests on greenlets-----------------------------

def put_test():
    print 'IN PUT'
    for i in range(1, 10):
        print 'Ihu, befrore putting something'
        my_queue.put(i)
        my_list.append(i)
        print 'Ihu, after putting something'
        print 'Ihu, Before getting smth'
        s = your_queue.get()
        print 'Ihu, After getting smth'
    for k in my_list:
        print '%s' %k

def get_test():
    spawn(put_test)
    print 'IN GET'
    while True:
        s = my_queue.get()
        my_list.append(s+10)
        your_queue.put(s)
        print 'I print: %s' %s
        print 'Now I continue'
def test_queue():
    s = {}
    s.setdefault('ihu', gqueue.Queue())

my_list = []
my_queue = gqueue.Queue()
your_queue = gqueue.Queue()