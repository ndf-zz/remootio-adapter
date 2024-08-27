#!/bin/sh
set -e

# module "burn-in" first time programm
make clean
make erase
make fuse
make randbook
make upload
make clean
