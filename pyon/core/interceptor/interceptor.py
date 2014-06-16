#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>, Thomas R. Lennan'



class Invocation(object):
    """
    Container object for parameters of events/messages passed to internal
    capability container processes
    """

    # Event outbound processing path
    PATH_OUT = 'outgoing'

    # Event inbound processing path
    PATH_IN = 'incoming'

    def __init__(self, **kwargs):
        self.args = kwargs
        self.path = kwargs.get('path')
        self.message = kwargs.get('message')
        self.headers = kwargs.get('headers') or {}  # ensure dict

        self.message_annotations = {}

    def get_invocation_process_type(self):
        process = self.get_arg_value('process')

        if not process:
            return 'simple'

        return getattr(process, 'process_type', 'simple')

    def get_message_sender(self):

        sender_type = self.get_header_value('sender-type', 'Unknown')
        if sender_type == 'service':
            sender_header = self.get_header_value('sender-service', 'Unknown')
            sender = self.get_service_name(sender_header)
        else:
            sender = self.get_header_value('sender', 'Unknown')

        return sender, sender_type

    def get_message_sender_queue(self):
        sender_queue = self.get_header_value('reply-to', 'todo')
        if (sender_queue == 'todo'):
            return None

        index = sender_queue.find('amq')
        if (index != -1): sender_queue = sender_queue[index:]
        return sender_queue

    def get_message_receiver(self):

        process = self.get_arg_value('process')
        if not process:
            return 'Unknown'

        process_type = self.get_invocation_process_type()
        if process_type == 'service':
            receiver_header = self.get_header_value('receiver', 'Unknown')
            receiver = self.get_service_name(receiver_header)
            return receiver

        elif process_type == 'agent':
            if process.resource_type is None:
                return process.name
            else:
                return process.resource_type

        else:
            return process.name

    #Returns the value of of the specified arg or the specified default value
    def get_arg_value(self, arg_name, default_value=None):
        value = self.args[arg_name] if self.args.has_key(arg_name) and self.args[arg_name] != '' else default_value
        return value

    #Returns the value of of the specified header or the specified default value
    def get_header_value(self, header_name, default_value=None):
        value = self.headers[header_name] if self.headers.has_key(header_name) and self.headers[header_name] != '' else default_value
        return value

    #This function is used to parse the two value tuple of sysname,servicename
    def get_service_name(self, header_value):
        value_list = [x.strip() for x in header_value.split(',')]
        value = value_list[1] if len(value_list) > 1 else value_list[0]
        return value


class Interceptor(object):
    """
    Basic interceptor model.
    """
    def configure(self, config):
        pass

    def outgoing(self, invocation):
        pass

    def incoming(self, invocation):
        pass


def process_interceptors(interceptors, invocation):
    for interceptor in interceptors:
        func = getattr(interceptor, invocation.path)
        invocation = func(invocation)
    return invocation
