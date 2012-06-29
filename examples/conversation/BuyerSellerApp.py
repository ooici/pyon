from gevent import spawn
from gevent import queue as gqueue
from pyon.net.transport import NameTrio
from pyon.net import channel
from pyon.net import messaging
from pyon.net import conversation
from pyon.net.conversation import ConversationOriginator, Conversation, Principal

def buyer_app():
    node, ioloop_process = messaging.make_node()
    originator = ConversationOriginator(node, NameTrio('buyer', 'buyer_queue25'))
    print 'Create originator'
    c = originator.start_conversation('protocol', 'buyer')
    print 'Start conversation'
    c.invite('seller', NameTrio('seller', 'seller_queue65'))
    print 'invite'
    c.send('seller', 'Hello1')
    print 'It is send'
    #msg, header =  c.recv('seller')
    #print 'Msg received: %s' %(msg)
    print 'Now I will send'
    #for i in range(0, 10):
    c.send('seller', 'Hello%s' %1)
    print 'Done with sending'
    #for i in range(0, 10):
    msg, header = c.recv('seller')
    print 'Msg received: %s' %(msg)
    c.close()
    originator.stop_listening()

def seller_app():
    node, ioloop_process = messaging.make_node()
    local = Principal(node, NameTrio('seller', 'seller_queue65'))
    print 'Create principal'
    local.spawn_listener()
    print 'Start listen'
    c  = local.get_invitation(auto_reply= True)
    print 'get Invitation'
    msg, header = c.recv('buyer')
    print 'Msg received: %s' %(msg)
    #c.send('buyer', 'I am joining')
    print 'Msg received: %s' %(msg)
    #for i in range(0, 10):
    msg, header = c.recv('buyer')
    print 'Msg received: %s' %(msg)
    #for i in range(0, 10):
    c.send('buyer', 'Hello%s' %2)
    c.close()
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