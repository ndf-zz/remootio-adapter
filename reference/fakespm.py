#!/usr/bin/python3

# fake SPM controller for testing

import logging
from spmtool import Spm
from time import sleep

PORT = '/dev/ttyUSB1'

logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger('fakespm')

s = Spm(PORT)
s.load('spm24121_factory.bin')
s._open()
while True:
    rv = s._readraw()
    if rv is not None:
        hdr = rv[0]
        blen = rv[1]
        body = rv[2]

        if hdr == 0x11:
            s._sendmsg(0x11, b'\x04\x05\x01')
        elif hdr == 0xf1:
            s._sendmsg(0xf1)
        elif hdr == 0xf2:
            offset = body[2]
            rlen = body[3]
            _log.debug('Sending offset=%02x, rlen=%02x', offset, rlen)
            s._sendmsg(0xf2, s._config[offset:offset + rlen])
        elif hdr == 0xf3:
            s._sendmsg(0xf3)
        elif hdr == 0xf4:
            s._sendmsg(0xf4)
        else:
            _log.debug('Unknown message - ignored')
