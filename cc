#!/bin/bash

ARGS=$@
if [ -z "$ARGS" ]; then
    ARGS=""
fi
python scripts/cc.py $ARGS
