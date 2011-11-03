#!/usr/bin/env python

import pika
import time
import base64
import os
import argparse
from gevent import monkey; monkey.patch_all()

connection = None
channel = None

pika.log.setup(pika.log.INFO, color=True)

parser = argparse.ArgumentParser()
#parser.add_argument('-d', '--datasize', type=int, help='Size of data in bytes')
parser.add_argument('-m', '--monkey', action="store_true")
opts = parser.parse_args()

if opts.monkey:
    from gevent import monkey; monkey.patch_all()

def on_connected(connection):
    global channel
    pika.log.info("demo_receive: Connected to RabbitMQ")
    connection.channel(on_channel_open)


def on_channel_open(channel_):
    global channel
    channel = channel_
    pika.log.info("demo_receive: Received our Channel")
    channel.exchange_declare(exchange='hoopty',
                             type='topic',
                             auto_delete=True,
                             callback=on_exchange_declared)

def on_exchange_declared(ex_):
    pika.log.info("demo_receive: Exchange Declared")
    channel.queue_declare(queue="test",
                          exclusive=False,
                          auto_delete=False,
                          durable=True,
                          callback=on_queue_declared)


def on_queue_declared(frame):
    pika.log.info("demo_receive: Queue Declared")
    channel.queue_bind(queue="test",
                       exchange="hoopty",
                       routing_key="test",
                       callback=on_bind)

def on_bind(*args):
    pika.log.info("demo_receive: Bound")
    channel.basic_consume(handle_delivery, queue='test')


def handle_delivery(channel, method_frame, header_frame, body):
    #pika.log.info("Basic.Deliver %s delivery-tag %i: %s",
    #              header_frame.content_type,
    #              method_frame.delivery_tag,
    #              body)

    #print "GOT MSG, PONGING"
    channel.basic_publish(exchange='hoopty',
                          routing_key='pong',
                          body='noop',
                          properties=pika.BasicProperties(
                              content_type="text/plain",
                              delivery_mode=1))

    channel.basic_ack(delivery_tag=method_frame.delivery_tag)


if __name__ == '__main__':
    parameters = pika.ConnectionParameters('localhost')
    connection = pika.adapters.SelectConnection(parameters, on_connected)
    try:
        connection.ioloop.start()
    except KeyboardInterrupt:
        connection.close()
        connection.ioloop.start()

