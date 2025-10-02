#!/bin/sh
set -e

# update nvram and program for >= v25001
make clean
make eepatch
make upload
make clean
