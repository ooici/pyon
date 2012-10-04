#!/usr/bin/env python

"""
AMQP messaging with Pika.
Uses Pika SelectConnection (using monkey patched select module).
"""

from pyon.util.log import log


class Node(object):
    """
    Main messaging interface that goes active when AMQP client connects.
    Integrates messaging and processing

    The life cycle of this depends on the underlying AMQP connection.

    This thing (or a subordinate but coupled/controlled object) mediates
    Messaging Channels that are used to send messages or that dispatch
    received messages to receiver/consumer protocol things.
    """

    client = None
    running = 0

    def on_connection_open(self, client):
        """
        AMQP Connection Open event handler.
        TODO: Should this be in another class?
        """
        log.debug("In Node.on_connection_open")
        log.debug("client: %s" % str(client))
        client.add_on_close_callback(self.on_connection_close)
        self.client = client
        self.start_node()

    def on_connection_close(self, *a):
        """
        AMQP Connection Close event handler.
        TODO: Should this be in another class?
        """
        log.debug("In Node.on_connection_close")

    def start_node(self):
        """
        This should only be called by on_connection_opened.
        so, maybe we don't need a start_node/stop_node interface
        TODO: Does this mean only one connection is supported?
        """
        log.debug("In Node.start_node")
        self.running = 1

    def stop_node(self):
        """
        """
        log.debug("In Node.stop_node")

    def channel(self, ch_type):
        """
        Create a channel on current node.
        Implement this in subclass
        name shouldn't be a parameter here
        """
        log.debug("In Node.channel")

if __name__ == '__main__':
    test()
