#!/bin/bash

LIBYAML=yaml-0.1.4
LIBYAMLTGZ=$LIBYAML.tar.gz

wget http://pyyaml.org/download/libyaml/$LIBYAMLTGZ
tar xfz $LIBYAMLTGZ
cd $LIBYAML
./configure
make
make install
cd ..
rm -rf $LIBYAML
rm -f $LIBYAMLTGZ
