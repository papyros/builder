#! /bin/bash

BUILDBOT_MASTER=~/master

git pull
cp master.cfg $BUILDBOT_MASTER/
buildbot restart $BUILDBOT_MASTER