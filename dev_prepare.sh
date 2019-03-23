#!/bin/bash
./autogen.sh
./configure --enable-debug
make -j4
