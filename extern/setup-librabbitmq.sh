#!/bin/bash

hg clone http://hg.rabbitmq.com/rabbitmq-codegen/
hg clone http://hg.rabbitmq.com/rabbitmq-c/
cd rabbitmq-c
autoreconf -i
./configure
make
make install