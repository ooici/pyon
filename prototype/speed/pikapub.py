#!/usr/bin/env python

import pika
import time
import base64
import os
import argparse
import msgpack

# Import all adapters for easier experimentation
from pika.adapters import *
pika.log.setup(pika.log.INFO, color=True)

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--datasize', type=int, help='Size of data in bytes')
parser.add_argument('-m', '--monkey', action="store_true")
parser.add_argument('-p', '--msgpack', action="store_true")
#parser.add_argument('-p', '--parallel', type=int, help='Number of parallel requests to run')
parser.set_defaults(datasize=1024, parallel=1)
opts = parser.parse_args()

if opts.monkey:
    from gevent import monkey; monkey.patch_all()

# make data (bytes)
DATA_SIZE = opts.datasize
data = base64.urlsafe_b64encode(os.urandom(DATA_SIZE))[:DATA_SIZE]
if opts.msgpack:
    data = msgpack.dumps(data)

pika.log.info("DATA SIZE: %d" % len(data))

connection = None
channel = None
counter = 0
st = 0
et = 0

def on_connected(connection):
    pika.log.info("demo_send: Connected to RabbitMQ")
    connection.channel(on_channel_open)


def on_channel_open(channel_):
    global channel
    channel = channel_
    pika.log.info("demo_send: Received our Channel")
    channel.exchange_declare(exchange='hoopty',
                             type='topic',
                             auto_delete=True,
                             callback=on_exchange_declared)

def on_exchange_declared(ex_):
    # make our pong listener
    channel.queue_declare(queue="pong", durable=False,
                          exclusive=False, auto_delete=True,
                          callback=on_queue_declared)


def on_queue_declared(frame):
    pika.log.info("demo_send: Queue Declared")
    channel.queue_bind(queue="pong",
                       exchange="hoopty",
                       routing_key="pong",
                       callback=on_bind)

def on_bind(*args):
    pika.log.info("PARTY STARTER")
    channel.basic_consume(handle_delivery, queue='pong')
    global st
    st = time.time()
    sendit()

def stats(update=True):
    global et
    if update:
        et = time.time()
    dt = et - st
    rps = counter / dt
    pika.log.info("Num: %5d\tr/s: %8f" % (counter, rps))

def handle_delivery(channel, method_frame, header_frame, body):
    global counter
    counter += 1

    if counter % 100 == 0:
        stats() 

    channel.basic_ack(delivery_tag=method_frame.delivery_tag)
    sendit()

def sendit():
    channel.basic_publish(exchange='hoopty',
                          routing_key='test',
                          body=data,
                          properties=pika.BasicProperties(
                              content_type='text/plain',
                              delivery_mode=1))

if __name__ == '__main__':
    parameters = pika.ConnectionParameters('localhost')
    connection = SelectConnection(parameters, on_connected)
    try:
        connection.ioloop.start()
    except KeyboardInterrupt:
        stats()
        connection.close()
        connection.ioloop.start()

