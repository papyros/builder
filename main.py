#! /usr/bin/env python3

from builder import *
from archbuilder import *

channel = Channel('papyros/testing')

build = channel.build('0.0.1')
build.execute()