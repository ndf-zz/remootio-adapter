#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""hhconfig

Crude TK Graphical front-end for Hay Hoist console

"""

import os
import re
import sys
import json
import bluetooth  # Classic interface ~ SPP
from socket import SHUT_RDWR
from serial import Serial
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
import threading
import queue
import logging
from time import sleep

_log = logging.getLogger('hhconfig')
_log.setLevel(logging.WARNING)

# Constants
_VERSION = '1.1.0'
_CFGFILE = '.hh.cfg'
_HELP_PIN = 'PIN: Hoist serial console access PIN'
_HELP_HP1 = 'H-P1: Time in seconds hoist requires to move \
down from home to position P1 (feed)'

_HELP_P1P2 = 'P1-P2: Time in seconds hoist requires to move \
down from position P1 (feed) to P2 (ground)'

_HELP_MAN = 'Man: Manual override adjustment time in seconds'
_HELP_HOME = 'Home: Maximum time in seconds hoist will raise \
toward home position before flagging error condition'

_HELP_HOMERETRY = 'Home-Retry: Retry return home after this many seconds'

_HELP_FEED = 'Feed: Return hoist automatically from P1 (feed) to \
home position after this many minutes (0 = disabled)'

_HELP_FEEDWEEK = 'Feeds/week: Schedule this many randomly spaced \
feeds per week (0 = disabled)'

_HELP_DOWN = 'Send down command to connected hoist'
_HELP_UP = 'Send up command to connected hoist'
_HELP_LOAD = 'Load configuration values from file and update connected hoist'
_HELP_SAVE = 'Save current configuration values to file'
_HELP_TOOL = 'Hyspec Hay Hoist config tool, MIT License.\n\
Source: https://pypi.org/project/hhconfig/\nSupport: https://hyspec.com.au/'

_HELP_PORT = 'Hoist device, select to re-connect'
_HELP_STAT = 'Current status of connected hoist'
_HELP_FIRMWARE = 'Firmware version of connected hoist'
_BTC_PKSZ = 20
_BTC_CONNECT_WAIT = 3  # Pause after connect
_BTC_DISCONNECT_WAIT = 8  # Pause after disconnect
_BTC_SCANTIME = 8
_BTC_DEV = '00:1D:4B'  # GBF Address prefix
_BTC_PORT = 2  # GBF SPP port no
_BTC_RFCOMM = bluetooth.RFCOMM
try:
    _BTC_RFCOMM = bluetooth.bluetooth.Protocols.RFCOMM  # pybluez2/windows
except Exception as e:
    pass
_SERPOLL = 0.2
_BTCPOLL = 0.2
_DEVPOLL = 3000
_ERRCOUNT = 2  # Tolerate two missed status before dropping connection
_DEVRETRY = 6  # If devpoll gets stuck waiting for status, restart
_BAUDRATE = 19200
_READLEN = 512
_CFG_LEN = 8  # Number of required config elements for full connection
_CFGKEYS = {
    'H-P1': '1',
    'P1-P2': '2',
    'Man': 'm',
    'H': 'h',
    'H-Retry': 'r',
    'Feed': 'f',
    'Feeds/week': 'n',
}
_TIMEKEYS = (
    'H-P1',
    'P1-P2',
    'Man',
    'H',
    'H-Retry',
)
_INTKEYS = (
    'Feed',
    'Feeds/week',
)
_KEYSUBS = {
    '1': 'H-P1',
    'P1': 'H-P1',
    'P1 time': 'H-P1',
    '2': 'P1-P2',
    'P2': 'P1-P2',
    'P2 time': 'P1-P2',
    'm': 'Man',
    'Man time': 'Man',
    'h': 'H',
    'H time': 'H',
    'f': 'Feed',
    'Feed time': 'Feed',
    'Feed min': 'Feed',
    'n': 'Feeds/week',
    'r': 'H-Retry',
    'p': 'PIN',
}

_LOGODATA = bytes.fromhex('\
89504e470d0a1a0a0000000d4948445200000190000000900403000000d4e6204b000000\
30504c5445a65623af6537e37126ba7b55c38d6ce98c53eb9b6ad1a68ff0b089d9b6a1f0\
c0a2e7cdbef5d9c4f1e1d7f0f0f0ffffff46a1595d000000097048597300000b1300000b\
1301009a9c18000007e94944415478daed9acd6b1b5710c09f58811142d616077a28a920\
90bb820e398456bae7b06090e93f10e1a38a0b2284c4b7207cd2a1d04328ba06e1822185\
1c4cab7b904190430f8922077ae92192850d4288d5ebccbcb71f5aad6d9cc4bb9b300f2c\
6ff6c39adf9befd908f9952cc1200cc2200cc2200cc2200cc2200cc2200cc2200cc2200c\
c2200cc220490179d9683c92f29f46e3b194bfe1f1b4e1ac2e9ec6f53bde68abe38743fc\
075ea0fb713d1ac399b9fbd81339738fdbd181d48530e83323a52944561e0b6759f2401f\
7d0ba2cef571ea093c8517a42cea534657caa9fb584e4edce372742020528a444ac31594\
220c0429e7eef97610042fc70e724c2299a8171b0e0be12020bc0792590181cbb183e097\
0e17f8a524aa750ec8ba0f448c57400af1839cc1d77549c8e18cb6361c64cd0fb2bb0292\
8d1f04a5dfc50fd145a6611024552aa1bc06816c944a4a3c1764add1d821ced841d031ac\
33dae753924e398d1b0920062c2a9ee1c97fe157de03c9c35d15bc6b4a9af2996be40911\
f78db6103f8d30103a35d4200bdaf3259096a3917841409ac20939ec09891d0232f18160\
805b05c924000472e17a9f02539f222b821c1e1efee50339f183ac68646e62504390fbf0\
9c03f24cff89e84040a65c4ba4e0138fa4e3ec691fc881cf47e6cb3eb29247861a840244\
a420a0876c5da4411b2dcc072120ff994ed4b2e4a2b51cb556327b7c20f0ad998a582b8a\
b53a6d7900c415d59747da41909b490081d00b14c092ae90bb86835c92d9bb0900816498\
36d1ba8c220a740ec825b5562e012090110dd871f07793e26e28c825d5af4e88f1824855\
f5f59daf0e845fd5830c7d2037fdfd08845f1b7912107ed5be968f1d350412a202913e90\
420044a599f81322964a10ae26da82822006c667b4260429dbfaa62590d38480b4c8ee4f\
95cf869428a74a0b2a8f14957a964026090121ef204148ac158dcc3d675799b01d00a93b\
3e12330819d578e6b40fc7beb64f657693b4a0343251ea71418c52e90e4589a92fe5c4d2\
8fa81e31457d096de92a48cbcd2316f5612179642d092053e18c50301f06410c15950ada\
b4a48a6107cec8c2153e012073da51da5e190a32a5a65c83d4893708d24e02882439310a\
a764a869d9c2ab7e2934942f9c6bc50752c42f474f48878350a6e96a9033c25e06490f93\
01f2b2d1d875c6bfd237fb6de3b9877ad2dbb5d528177f3dba70f6bb1bcfec975f2b3048\
f240de9c53860c74a3338c1864e79bbbe0ad3ba552e9892e85f312dbd98a683ba5fc0dd5\
2ea5a8322b401909e17a6a0a63a88bfbb69ebd520550c4f352be16e25ea420ef55af5454\
62b820961f0405c70c32c4cf3505820f7c1f02d25255b4ed9c8f72d22852630592f34072\
4b202955eeb7150e82cc5423b60262ebdb274e5b10150848b281d562516c1441b00a4edc\
cb1253b90bb2b643a2569ccc6e210818dacf6080f038d824d66836cde5bbd0bdfca21493\
aeab0c1bd9fb1103200af0b37b063b59a1b128562d5d17240f45d52e55560502c99d526e\
cfc1e6b7e742f8add480c220037fab0c3fd654880841264a280441a13c90b20f04cfda22\
8da6022006825480eace7db90452a1a9f03a68038db36b5f737b157c8788ef3fb31ec8bd\
c32181647c2070117c2083c521168d2fe87e4baad98a9a9ca8c19205d57101eec911c435\
7bbb0834ba796838329e69b95d870b927d8995fb99c8a1cd2348498338b395a1dba18d49\
537d919de3b1e936bf11814c20a416c5dd0a39bb024999a2b81cb54e44d94ce1fd903f00\
c414d6eb52c9f2831ca0c62af038f88906b1e20071c32f69a4eea481033d94eb0bab0822\
f7c50dca2b20245c29f84130669046e207e9821c77b1f616e27809a48dade12e1a5b5fdc\
2490a20bd2688c9d2172576a1fc9da3198d63a580d816c3c965ed49a7a2059f207483426\
280b4a948a0229bf2e128817ff0c4a9bf9789cfdc48b5a2a826a104c1b4ed46a61072954\
ce0790f708a276beec03a95322c7f08b3f2afc76a3cc2319278f2c83b43c90befb9e2787\
2033a1734f4b581e88ad5e31e2bd154ab0d60ccd2b3290a930463ab32b1028517e409089\
07724a03b854e90e982056bf26809c08e39949991d4a94b60abed0db421d267ec59227f2\
12c5d6559f0b42fbae5e7e3a20e02fe3538038a391760184d4ff6523a51565e9513610c4\
563492e8865c05916e1ec9635175ac2a5e029938657c761584065fb194f138dff9310ce4\
c05f3496d181d17b1164468d15bdff0982b4f1b5bbd3587d176d87f867e9bec4d1ce5523\
ccfc30bc24b4f5f93751bfb1e2e103833008833008833008833008833008833008833008\
83300883300883300883300883300883300883300883c406b218f45e3d6f369bfbef920b\
62bfedf57a1d94b2d97c5aa5b5d5dceb0d17781e2fd4aad55bbeb5b5dde91d8d130872eb\
e3d6ed6ab55623fa66a7d34b00dac7828490d59aa0ab2f1fc40502c3ecec83550e3c7f1a\
7d180cc85297d6e0aa0ef7f615193aad1a9affb5825c79a150609fbd0bb01680f0a0bafa\
e8d6ded1c859f183f899b6619f7b8e7d2e408baf3acf9f3ed80c57fdf61f23df4a14882f\
9254372fbce1a7bdbf47cb2b9120176b6d6fff68b4babe1c90db5bdbe849a3739648903d\
6de9c454ab516c72fda6b9b7df1b8c2e59e21aa351706d9e1fb642ade54a4b5c871577ce\
152b984e8e06a3cfb444b3f960f3f3416c6defbf1bc5b284faf5b6735eb8bea56aaa1a1a\
3064ec819673d0eb6096ddf42be2d3ede3d341464be2294fab62a4bb4cf51fb4adc4c910\
02f2052f06611006611006611006f99a40fe0745a166751c8047c20000000049454e44ae\
426082\
')


def isbtcaddr(addr):
    """Return true if addr looks like a MAC address"""
    return re.match('^[\dA-Fa-f]{2}(:[\dA-Fa-f]{2}){5}$', addr) is not None


def _subkey(key):
    if key in _KEYSUBS:
        key = _KEYSUBS[key]
    return key


def _mkopt(parent,
           prompt,
           units,
           row,
           validator,
           update,
           help=None,
           helptext=''):
    prompt = ttk.Label(parent, text=prompt)
    prompt.grid(column=0, row=row, sticky=(E, ))
    svar = StringVar()
    ent = ttk.Entry(parent,
                    textvariable=svar,
                    width=6,
                    justify='right',
                    validate='key',
                    validatecommand=validator)
    ent.grid(column=1, row=row, sticky=(
        E,
        W,
    ))
    lbl = ttk.Label(parent, text=units)
    lbl.grid(column=2, row=row, sticky=(W, ), columnspan=2)
    ent.bind('<FocusOut>', update, add='+')
    if help is not None and helptext:
        prompt.bind('<Enter>',
                    lambda event, text=helptext: help(text),
                    add='+')
        ent.bind('<Enter>', lambda event, text=helptext: help(text), add='+')
        lbl.bind('<Enter>', lambda event, text=helptext: help(text), add='+')
    return svar


class BTCSerial():
    """Bluetooth Classic RFCOMM Serial (SPP) Wrapper"""

    def __init__(self, addr=None):
        """Connect to the classic device on addr: (address, port)"""
        _log.debug('Creating Bluetooth RFCOMM prot=%r', _BTC_RFCOMM)
        self._sock = bluetooth.BluetoothSocket(_BTC_RFCOMM)
        if addr is not None:
            self.open(addr)

    def isopen(self):
        return self._sock is not None

    def open(self, addr):
        try:
            self._sock.connect((addr, _BTC_PORT))
            _log.debug('Sock Connected - pause')
            sleep(_BTC_CONNECT_WAIT)
            _log.debug('Sock Connected - done')
        except Exception as e:
            _log.info('%s opening BTC device %r: %s', e.__class__.__name__,
                      addr, e)
            self.close()
        return self.isopen()

    def close(self):
        try:
            # release the previous handle
            osock = self._sock
            self._sock = None
            osock.shutdown(SHUT_RDWR)
            osock.close()
            del (osock)

            # add pause to allow bluez to clean up
            sleep(_BTC_CONNECT_WAIT)
        except Exception as e:
            _log.info('%s closing BTC device %r: %s', e.__class__.__name__,
                      addr, e)
            pass
        self._sock = None

    def read(self, count):
        """Read to a timeout"""
        ret = b''
        if self._sock is not None:
            try:
                self._sock.settimeout(_BTCPOLL)
                while True:
                    nb = self._sock.recv(count)
                    if nb:
                        ret += nb
            except Exception as e:
                if str(e) != 'timed out':
                    _log.error('%s BTC read error: %s', e.__class__.__name__,
                               e)
                    self.close()
        return ret

    def write(self, buf):
        so = 0
        if self._sock is not None:
            try:
                self._sock.settimeout(None)
                bl = len(buf)
                rem = bl
                while rem:
                    eo = min(bl, so + _BTC_PKSZ)
                    oc = self._sock.send(buf[so:eo])
                    rem -= oc
                    so += oc
            except Exception as e:
                if str(e) != 'timed out':
                    _log.error('%s BTC write error: %s', e.__class__.__name__,
                               e)
                    self.close()
        return so


class BTCScan(threading.Thread):
    """Bluetooth Classic Scanner"""

    def exit(self):
        """Request thread termination"""
        self._running = False
        self._cqueue.put_nowait(('_exit', True))

    def trigger(self):
        """Request a new BTC device scan"""
        self._cqueue.put_nowait(('_trigger', True))

    def inscan(self):
        """Return true if a scan is in progress"""
        return self._inscan

    def __init__(self):
        threading.Thread.__init__(self, daemon=True)
        self._running = False
        self._inscan = False
        self._cqueue = queue.Queue()
        self.devs = {}

    def run(self):
        """Thread main loop, called by object.start()"""
        self._running = True
        while self._running:
            try:
                c = self._cqueue.get()
                self._cqueue.task_done()
                if c[0] == '_exit':
                    self._running = False
                elif c[0] == '_trigger':
                    self._trigger()
            except queue.Empty:
                pass
            except Exception as e:
                _log.error('BTC scanner %s: %s', e.__class__.__name__, e)

    def _trigger(self):
        try:
            self._inscan = True
            _log.debug('BTC Starting discovery scan')
            for d in bluetooth.discover_devices(lookup_names=True,
                                                duration=_BTC_SCANTIME):
                if d[0].upper().startswith(_BTC_DEV):
                    devport = d[0]
                    devstr = '%s - %s' % (d[0], d[1])
                    if devport not in self.devs:
                        _log.debug('BTC discovered device %s', devstr)
                    elif self.devs[devport] != devstr:
                        _log.debug('BTC update device %s', devstr)
                    self.devs[devport] = devstr
        except Exception as e:
            _log.error('BTC Scan %s: %s', e.__class__.__name__, e)
        finally:
            self._inscan = False
        _log.debug('BTC end discovery scan')


class SerialConsole(threading.Thread):
    """Serial console command/response wrapper"""

    def get_event(self):
        """Return next available event from response queue or None"""
        m = None
        try:
            m = self._equeue.get_nowait()
            self._equeue.task_done()
        except queue.Empty:
            pass
        return m

    def connected(self):
        """Return true if device is considered connected"""
        return self._portdev is not None

    def configured(self):
        """Return true if device config has been read"""
        return self.cfg is not None and len(self.cfg) > _CFG_LEN

    def inproc(self):
        """Return true if open or close underway"""
        return self._portinproc or self._closeinproc

    def clearproc(self):
        """Clear out state to idle condition"""
        self._flush()
        self._cqueue.put_nowait(('_close', None))

    def updatepin(self, pin):
        """Update the auth pin on attached device"""
        self._cqueue.put_nowait(('_updatepin', pin))
        self._cqueue.put_nowait(('_message', 'Console PIN updated'))

    def update(self, cfg):
        """Update all keys in cfg on attached device"""
        self._cqueue.put_nowait(('_update', cfg))
        if len(cfg) > 1:
            self._cqueue.put_nowait(('_message', 'Hoist updated'))

    def down(self, data=None):
        """Request down trigger"""
        self._cqueue.put_nowait(('_down', data))

    def up(self, data=None):
        """Request up trigger"""
        self._cqueue.put_nowait(('_up', data))

    def exit(self):
        """Request thread termination"""
        self._running = False
        self._cqueue.put_nowait(('_exit', True))

    def setport(self, device=None):
        """Request new device address"""
        _log.debug('setport called with dev = %r', device)
        self._cqueue.put_nowait(('_port', device))

    def status(self, data=None):
        """Request update of device status"""
        self._sreq += 1
        self._cqueue.put_nowait(('_status', data))

    def setpin(self, pin):
        self._pin = pin

    def __init__(self):
        threading.Thread.__init__(self, daemon=True)
        self._pin = 0
        self._sreq = 0
        self._portdev = None
        self.portdev = None
        self._cqueue = queue.Queue()
        self._equeue = queue.Queue()
        self._running = False
        self._portinproc = False
        self._closeinproc = False
        self.cb = self._defcallback
        self.cfg = None

    def run(self):
        """Thread main loop, called by object.start()"""
        self._running = True
        while self._running:
            try:
                if self.connected():
                    if self._cqueue.qsize() != 0:
                        c = self._cqueue.get()
                    else:
                        self._readresponse()
                        c = self._cqueue.get_nowait()
                else:
                    c = self._cqueue.get()
                self._cqueue.task_done()
                self._proccmd(c)
            except queue.Empty:
                pass
            except Exception as e:
                _log.error('console %s: %s', e.__class__.__name__, e)
                self._close()

    def _send(self, buf):
        if self._portdev is not None:
            _log.debug('SEND: %r', buf)
            return self._portdev.write(buf)

    def _recv(self, len):
        rb = b''
        if self._portdev is not None:
            while not rb.endswith(b'\r\n'):
                nb = self._portdev.read(len)
                if nb == b'':
                    # timeout
                    break
                rb = rb + nb
            if rb:
                _log.debug('RECV: %r', rb)
                self._portinproc = False
        return rb

    def _updatepin(self, pin):
        self._pin = pin
        if self.connected() and self.configured():
            cmd = 'p' + str(pin) + '\r\n'
            self._send(cmd.encode('ascii', 'ignore'))
            self._readresponse()

    def _update(self, cfg):
        for k in cfg:
            cmd = _CFGKEYS[k] + str(cfg[k]) + '\r\n'
            self._send(cmd.encode('ascii', 'ignore'))
            self._readresponse()

    def _discard(self, data=None):
        """Send hello/escape sequence and discard any output"""
        self._send(b' ')
        rb = self._recv(_READLEN)
        _log.debug('HELLO: %r', rb)

    def _auth(self, data=None):
        """Send console PIN"""
        cmd = '\x10' + str(self._pin) + '\r\n'
        self._send(cmd.encode('ascii', 'ignore'))
        rb = self._recv(_READLEN)
        _log.debug('AUTH: %r', rb)

    def _status(self, data=None):
        self._send(b's')
        self._readresponse()
        if self._sreq > _ERRCOUNT:
            _log.debug('No response to status request, closing device')
            self._close()

    def _setvalue(self, key, value):
        if self.cfg is None:
            self.cfg = {}
        if key == 'Firmware':
            self.cfg[key] = value
            self._equeue.put(('firmware', value))
        elif key == 'PIN':
            pass
        else:
            try:
                v = int(value)
                self.cfg[key] = v
                self._equeue.put(('set', key, v))
            except Exception as e:
                pass

    def _message(self, data=None):
        if data:
            self._equeue.put(('message', data))
            self.cb()

    def _readresponse(self, data=None):
        docb = False
        wasconfigured = self.configured()
        rb = self._recv(_READLEN)
        rv = rb.decode('ascii', 'ignore').strip().split('\n')
        for line in rv:
            l = line.strip()
            if l.startswith('State:'):
                self._sreq = 0
                statmsg = l.split(': ', maxsplit=1)[1].strip()
                self._equeue.put((
                    'status',
                    statmsg,
                ))
                docb = True
            elif ':' in l:
                if l.startswith('Trigger:'):
                    self._equeue.put(('message', l))
                    docb = True
                    if 'reset' in l:
                        # re-auth required
                        self._cqueue.put_nowait(('_auth', None))
            elif '=' in l:
                lv = l.split(' = ', maxsplit=1)
                if len(lv) == 2:
                    key = _subkey(lv[0].strip())
                    if key != 'PIN':
                        self._setvalue(key, lv[1].strip())
                        docb = True
                        if self.configured() and not wasconfigured:
                            self._equeue.put((
                                'connect',
                                None,
                            ))
                    else:
                        _log.debug('PIN Updated')

                else:
                    _log.debug('Ignored unexpected response %r', l)
            elif '?' in l:
                pass
            else:
                if l:
                    self._equeue.put(('message', l))
                    docb = True
        if docb:
            self.cb()

    def _down(self, data=None):
        if self.connected():
            self._send(b'd')
            self._readresponse()

    def _up(self, data=None):
        if self.connected():
            self._send(b'u')
            self._readresponse()

    def _serialopen(self):
        if self._portdev is not None:
            _log.debug('Serial port already open')
            return True

        if self.portdev is not None:
            self._portinproc = True
            self._sreq = 0
            if isbtcaddr(self.portdev):
                _log.debug('Connecting BTC device: %r', self.portdev)
                self._portdev = BTCSerial()
                if self._portdev.open(self.portdev):
                    _log.debug('BTC Device connected OK')
                else:
                    _log.debug('BTC Device did not connect')
                    self._portdev = None
                    self.clearproc()
            else:
                _log.debug('Connecting serial device: %r', self.portdev)
                self._portdev = Serial(port=self.portdev,
                                       baudrate=_BAUDRATE,
                                       rtscts=False,
                                       timeout=_SERPOLL)
        return self._portdev is not None

    def _getvalues(self, data=None):
        self._send(b'v')
        self._readresponse()

    def _port(self, port):
        """Blocking close, followed by blocking open, then queue cmds"""
        # Empty any pending commands from the the queue
        self._flush()
        if self.connected():
            self._close()
        self.portdev = port
        if self._serialopen():
            self.cfg = {}
            self._cqueue.put_nowait(('_discard', None))
            self._cqueue.put_nowait(('_auth', None))
            self._cqueue.put_nowait(('_status', None))
            self._cqueue.put_nowait(('_getvalues', None))
            self._equeue.put((
                'connect',
                None,
            ))
            self.cb()

    def _exit(self, data=None):
        self._close()
        self._flush()
        self._running = False

    def _close(self, data=None):
        _log.debug('_close called')
        if self._portdev is not None:
            self._closeinproc = True
            self.cfg = None
            self._portdev.close()
            self._portdev = None
            self._equeue.put((
                'disconnect',
                None,
            ))
            self.cb()
        self._closeinproc = False
        self._portinproc = False

    def _flush(self):
        try:
            while True:
                c = self._cqueue.get_nowait()
                self._cqueue.task_done()
                _log.debug('Flush queued command: %r', c)
        except queue.Empty:
            pass

    def _proccmd(self, cmd):
        """Process a command tuple from the queue."""
        method = getattr(self, cmd[0], None)
        if method is not None:
            _log.debug('Serial command: %r', cmd)
            method(cmd[1])
        else:
            _log.error('Unknown serial command: %r', cmd)

    def _defcallback(self, evt=None):
        pass


class HHConfig:
    """TK configuration utility for Hay Hoist"""

    def getports(self):
        """Update the list of available ports"""
        self._ioports = []
        self._ionames = []

        self._ioports.append(None)
        self._ionames.append(' -- Bluetooth Devices -- ')

        if self.scanio.devs:
            for dev in self.scanio.devs:
                devname = self.scanio.devs[dev]
                if dev not in self.btdevs:
                    self.logvar.set('Found hoist: %s' % (devname, ))
                self.btdevs[dev] = devname
                self._ioports.append(dev)
                self._ionames.append(devname)

        # Add serial ports after BTCs
        devs = {}
        try:
            from serial.tools.list_ports import comports
            for port in comports():
                devname = str(port)
                # ignore windows auto add SPP COM ports
                if 'Serial over Bluetooth' not in devname:
                    devs[port.device] = devname
        except Exception:
            pass
        if devs:
            self._ioports.append(None)
            self._ionames.append(' -- Serial Devices -- ')
            for cp in sorted(devs):
                self._ioports.append(cp)
                self._ionames.append(devs[cp])

    def check_cent(self, newval, op):
        """Validate text entry for a time value in hundredths"""
        ret = False
        if newval:
            try:
                v = round(float(newval) * 100)
                if v >= 0 and v < 65536:
                    ret = True
            except Exception:
                pass
            if not ret:
                self.logvar.set('Invalid time entry')
        else:
            ret = True
        return ret

    def check_int(self, newval, op):
        """Verify text entry for int value"""
        ret = False
        if newval:
            try:
                v = int(newval)
                if v >= 0 and v < 65536:
                    ret = True
            except Exception:
                pass
            if not ret:
                self.logvar.set('Invalid entry')
        else:
            ret = True
        return ret

    def connect(self, data=None):
        """Handle device connection event - issued on rececption of values"""
        self.devval = {}
        if self.devio.configured():
            self.logvar.set('Hoist connected')
            for k in _CFGKEYS:
                self.devval[k] = None
                if k in self.uval and self.uval[k] is not None:
                    if k in self.devio.cfg and self.devio.cfg[k] == self.uval[
                            k]:
                        self.devval[k] = self.uval[k]
                else:
                    if k in self.devio.cfg and self.devio.cfg[k] is not None:
                        self.devval[k] = self.devio.cfg[k]
            self.dbut.state(['!disabled'])
            self.ubut.state(['!disabled'])
            self.uiupdate()
        elif self.devio.connected():
            self.logvar.set('Reading hoist configuration...')

    def disconnect(self):
        """Handle device disconnection event"""
        if not self.devio.connected():
            if self.fwval.get():
                self.logvar.set('Hoist disconnected')
            self.statvar.set('[Not Connected]')
            self.devval = {}
            for k in _CFGKEYS:
                self.devval[k] = None
            self.fwval.set('')
            self.dbut.state(['disabled'])
            self.ubut.state(['disabled'])

    def devevent(self, data=None):
        """Extract and handle any pending events from the attached device"""
        while True:
            evt = self.devio.get_event()
            if evt is None:
                break

            _log.debug('Serial event: %r', evt)
            if evt[0] == 'status':
                self.statvar.set(evt[1])
                _log.debug('Received status: %s', evt[1])
            elif evt[0] == 'set':
                key = evt[1]
                val = evt[2]
                if key in _CFGKEYS:
                    self.devval[key] = val
                    self.logvar.set('Updated option ' + key)
                else:
                    _log.debug('Ignored config key: %r', key)
            elif evt[0] == 'firmware':
                self.fwval.set(evt[1])
            elif evt[0] == 'connect':
                self.connect()
            elif evt[0] == 'disconnect':
                self.disconnect()
            elif evt[0] == 'message':
                self.logvar.set(evt[1])
            else:
                _log.warning('Unknown serial event: %r', evt)

    def devcallback(self, data=None):
        """Trigger an event in tk main loop"""
        self.window.event_generate('<<SerialDevEvent>>')

    def doreconnect(self):
        """Initiate a re-list and re-connect sequence"""
        self._devpollcnt = 0
        self.disconnect()
        oldport = None
        selid = self.portsel.current()
        if selid >= 0 and selid < len(self._ioports):
            oldport = self._ioports[selid]

        oldports = set(self._ioports)
        self.getports()
        newports = set(self._ioports)
        if oldports != newports:
            _log.info('Serial port devices updated')

        self.portsel.selection_clear()
        self.portsel['values'] = self._ionames
        if oldport is not None and oldport in self._ioports:
            newsel = self._ioports.index(oldport)
            self.portsel.current(newsel)
        else:
            if self._ionames:
                self.portsel.current(0)
            else:
                self.portsel.set('')
        self.portchange(None)

    def devpoll(self):
        """Request update from attached device / reinit connection"""
        try:
            self._devpollcnt += 1
            if self.devio.connected():
                if self.devio.configured():
                    self._devpollcnt = 0
                    self.devio.status()
                else:
                    self.logvar.set('Waiting for hoist...')
                    _log.debug('Devpoll retry %d', self._devpollcnt)
                    if self._devpollcnt > _DEVRETRY:
                        self.doreconnect()
                    elif self.devio.inproc():
                        _log.debug('Open/close in progress, ignore')
                    else:
                        _log.debug('Waiting for hoist configuration, ignore')
            else:
                self.doreconnect()

        except Exception as e:
            self.logvar.set('Error: %s' % (e.__class__.__name__, ))
            _log.error('devpoll %s: %s', e.__class__.__name__, e)
        finally:
            self.window.after(_DEVPOLL, self.devpoll)

    def xfertimeval(self, k):
        """Reformat time value for display in user interface"""
        v = None
        fv = None
        nv = self.uival[k].get()
        if nv:
            try:
                t = max(round(float(nv) * 100), 1)
                if t > 0 and t < 65536:
                    v = t
                    fv = '%0.2f' % (v / 100.0, )
            except Exception:
                pass
        else:
            if k in self.devval and self.devval[k] is not None:
                v = self.devval[k]
                fv = '%0.2f' % (v / 100.0, )

        self.uval[k] = v
        if fv is not None and fv != nv:
            self.uival[k].set(fv)

    def xferintval(self, k):
        """Reformat integer value for display in user interface"""
        v = None
        fv = None
        nv = self.uival[k].get()
        if nv:
            try:
                t = int(nv)
                if t >= 0 and t < 65536:
                    v = t
                    fv = '%d' % (v, )
            except Exception:
                pass
        else:
            if self.devval[k] is not None:
                v = self.devval[k]
                fv = '%d' % (v, )

        self.uval[k] = v
        if fv is not None and fv != nv:
            self.uival[k].set(fv)

    def _savepin(self):
        """Write the cache pin config"""
        try:
            with open(_CFGFILE, 'w') as f:
                f.write('%d\r\n' % (self.pin, ))
        except Exception as e:
            _log.error('%s saving cfg: %s', e.__class__.__name__, e)

    def xferpin(self):
        """Check for an updated console PIN"""
        newpin = self.pin
        try:
            pv = self.pinval.get()
            if pv and pv.isdigit():
                newpin = int(pv)
            else:
                newpin = 0
        except Exception as e:
            pass
        if newpin != self.pin:
            if newpin == 0:
                self.pinval.set('')
            self.pin = newpin
            self._savepin()
            self.devio.updatepin(self.pin)

    def uiupdate(self, data=None):
        """Check for required updates and send to attached device"""
        for k in _TIMEKEYS:
            self.xfertimeval(k)
        for k in _INTKEYS:
            self.xferintval(k)

        self.xferpin()

        # if connected, update device
        if self.devio.connected():
            cfg = {}
            for k in self.devval:
                if k in self.uval and self.uval[k] is not None:
                    if self.uval[k] != self.devval[k]:
                        cfg[k] = self.uval[k]
            if cfg:
                _log.debug('Sending %d updated values to hoist', len(cfg))
                self.logvar.set('Updating hoist...')
                self.devio.update(cfg)

    def portchange(self, data):
        """Handle change of selected serial port"""
        selid = self.portsel.current()
        if selid is not None:
            if self._ioports and selid >= 0 and selid < len(self._ioports):
                if self._ioports[selid] is None:
                    if self.devio.connected():
                        _log.debug('Disconnect')
                        self.devio.setport(None)
                    else:
                        if not self.scanio.inscan():
                            _log.debug('Trigger BTC scan')
                            self.scanio.trigger()
                            self.logvar.set('Scanning Bluetooth...')
                else:
                    # force reconnect to specified port
                    self._devpollcnt = 0
                    self.devio.setport(self._ioports[selid])
        self.portsel.selection_clear()

    def triggerdown(self, data=None):
        """Request down trigger"""
        self.devio.down()

    def triggerup(self, data=None):
        """Request up trigger"""
        self.devio.up()

    def loadvalues(self, cfg):
        """Update each value in cfg to device and ui"""
        doupdate = False
        _log.debug('Load from cfg')
        for key in cfg:
            k = _subkey(key)
            if k in _TIMEKEYS:
                try:
                    self.uival[k].set('%0.2f' % (cfg[key] / 100.0, ))
                    doupdate = True
                except Exception as e:
                    _log.error('%s loading time key %r: %s',
                               e.__class__.__name__, k, e)
            elif k in _INTKEYS:
                try:
                    self.uival[k].set('%d' % (cfg[key], ))
                    doupdate = True
                except Exception as e:
                    _log.error('%s loading int key %r: %s',
                               e.__class__.__name__, k, e)
            elif k == 'PIN':
                if isinstance(cfg[key], int):
                    if cfg[key] != self.pin:
                        if cfg[key]:
                            self.pinval.set('%d' % (cfg[key], ))
                        else:
                            self.pinval.set('')
                        _log.debug('Console PIN updated')
                        doupdate = True
            else:
                _log.debug('Ignored invalid config key %r', k)
        if doupdate:
            self.uiupdate()

    def flatconfig(self):
        """Return a flattened config for the current values"""
        cfg = {}
        cfg['PIN'] = self.pin
        for k in self.uval:
            if self.uval[k] is not None:
                cfg[k] = self.uval[k]
        return cfg

    def savefile(self):
        """Choose file and save current values"""
        filename = filedialog.asksaveasfilename(initialfile='hhconfig.json')
        if filename:
            try:
                cfg = self.flatconfig()
                with open(filename, 'w') as f:
                    json.dump(cfg, f, indent=1)
                self.logvar.set('Saved config to file')
            except Exception as e:
                _log.error('savefile %s: %s', e.__class__.__name__, e)
                self.logvar.set('Save config: %s' % (e.__class__.__name__, ))

    def loadfile(self):
        """Choose file and load values, update device if connected"""
        filename = filedialog.askopenfilename()
        if filename:
            try:
                cfg = None
                with open(filename) as f:
                    cfg = json.load(f)
                self.logvar.set('Load config from file')
                if cfg is not None and isinstance(cfg, dict):
                    self.loadvalues(cfg)
                else:
                    self.logvar.set('Ignored invalid config')
            except Exception as e:
                _log.error('loadfile %s: %s', e.__class__.__name__, e)
                self.logvar.set('Load config: %s' % (e.__class__.__name__, ))

    def setHelp(self, text):
        """Replace help text area contents"""
        self.help['state'] = 'normal'
        self.help.replace('1.0', 'end', text)
        self.help['state'] = 'disabled'

    def _loadpin(self):
        """Check for a cached pin config"""
        if os.path.exists(_CFGFILE):
            with open(_CFGFILE) as f:
                a = f.read().strip()
                if a and a.isdigit():
                    aval = int(a)
                    if aval > 0 and aval < 65535:
                        self.pin = aval

    def __init__(self, window=None, devio=None, scanio=None):
        self.pin = 0
        self._loadpin()
        self.scanio = scanio
        self.btdevs = {}
        self.devio = devio
        self.devio.cb = self.devcallback
        self.devio.setpin(self.pin)
        self._devpollcnt = 0
        window.title('Hay Hoist Config')
        row = 0
        frame = ttk.Frame(window, padding="0 0 0 0")
        frame.grid(column=0, row=row, sticky=(
            E,
            S,
            W,
            N,
        ))
        frame.columnconfigure(2, weight=1)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        # header block / status
        self._logo = PhotoImage(data=_LOGODATA)
        #hdr = ttk.Label(frame, background='White', borderwidth=0, padding=0)
        hdr = Label(frame, borderwidth=0, highlightthickness=0, bd=0)
        #, text='Hay Hoist', background='White')
        hdr['image'] = self._logo
        hdr.grid(column=0,
                 padx=0,
                 pady=0,
                 row=row,
                 columnspan=4,
                 sticky=(
                     E,
                     W,
                 ))
        hdr.bind('<Enter>',
                 lambda event, text=_HELP_TOOL: self.setHelp(text),
                 add='+')
        row += 1

        # Status indicator
        ttk.Label(frame, text="Status:").grid(column=0, row=row, sticky=(E, ))
        self.statvar = StringVar(value='[Not Connected]')
        statlbl = ttk.Label(frame,
                            textvariable=self.statvar,
                            font='TkHeadingFont')
        statlbl.grid(column=1, row=row, sticky=(
            E,
            W,
        ), columnspan=3)
        statlbl.bind('<Enter>',
                     lambda event, text=_HELP_STAT: self.setHelp(text),
                     add='+')
        row += 1

        # io port setting
        self._ioports = []
        self._ionames = []
        self.getports()
        ttk.Label(frame, text="Hoist:").grid(column=0, row=row, sticky=(E, ))
        self.portsel = ttk.Combobox(frame)
        self.portsel['values'] = self._ionames
        self.portsel.state(['readonly'])
        self.portsel.bind('<<ComboboxSelected>>', self.portchange)
        #if self._ionames:
        #self.portsel.current(0)
        self.portsel.grid(column=1, row=row, sticky=(
            E,
            W,
        ), columnspan=3)
        self.portsel.bind('<Enter>',
                          lambda event, text=_HELP_PORT: self.setHelp(text),
                          add='+')
        row += 1

        # validators
        check_cent_wrapper = (window.register(self.check_cent), '%P', '%V')
        check_int_wrapper = (window.register(self.check_int), '%P', '%V')

        # PIN entry
        self.pinval = _mkopt(frame, "PIN:", "", row, check_int_wrapper,
                             self.uiupdate, self.setHelp, _HELP_PIN)
        if self.pin:  # is nonzero
            self.pinval.set(str(self.pin))
        row += 1

        # device values
        self.devval = {}
        self.uval = {}
        for k in _CFGKEYS:
            self.devval[k] = None
            self.uval[k] = None

        # config options
        self.uival = {}
        self.uival['H-P1'] = _mkopt(frame, "H-P1:", "seconds", row,
                                    check_cent_wrapper, self.uiupdate,
                                    self.setHelp, _HELP_HP1)
        row += 1
        self.uival['P1-P2'] = _mkopt(frame, "P1-P2:", "seconds", row,
                                     check_cent_wrapper, self.uiupdate,
                                     self.setHelp, _HELP_P1P2)
        row += 1
        self.uival['Man'] = _mkopt(frame, "Man:", "seconds", row,
                                   check_cent_wrapper, self.uiupdate,
                                   self.setHelp, _HELP_MAN)
        row += 1
        self.uival['H'] = _mkopt(frame, "Home:", "seconds", row,
                                 check_cent_wrapper, self.uiupdate,
                                 self.setHelp, _HELP_HOME)
        row += 1
        self.uival['H-Retry'] = _mkopt(frame, "Home-Retry:", "seconds", row,
                                       check_cent_wrapper, self.uiupdate,
                                       self.setHelp, _HELP_HOMERETRY)
        row += 1
        self.uival['Feed'] = _mkopt(frame, "Feed:", "minutes", row,
                                    check_int_wrapper, self.uiupdate,
                                    self.setHelp, _HELP_FEED)
        row += 1
        self.uival['Feeds/week'] = _mkopt(frame, "Feeds/week:", "(max 5000)",
                                          row, check_int_wrapper,
                                          self.uiupdate, self.setHelp,
                                          _HELP_FEEDWEEK)
        row += 1

        # firmware version label
        ttk.Label(frame, text='Firmware:').grid(column=0,
                                                row=row,
                                                sticky=(E, ))
        self.fwval = StringVar()
        fwlbl = ttk.Label(frame, textvariable=self.fwval)
        fwlbl.grid(column=1, row=row, sticky=(W, ), columnspan=3)
        fwlbl.bind('<Enter>',
                   lambda event, text=_HELP_FIRMWARE: self.setHelp(text),
                   add='+')
        row += 1

        # tool version
        ttk.Label(frame, text="Tool Version:").grid(column=0,
                                                    row=row,
                                                    sticky=(E, ))
        lbl = ttk.Label(frame, text=_VERSION)
        lbl.grid(column=1, row=row, sticky=(
            E,
            W,
        ), columnspan=3)
        lbl.bind('<Enter>',
                 lambda event, text=_HELP_TOOL: self.setHelp(text),
                 add='+')
        row += 1

        # help text area
        obg = frame._root().cget('bg')
        self.help = Text(frame,
                         width=40,
                         height=3,
                         padx=6,
                         pady=3,
                         bg=obg,
                         font='TkTooltipFont',
                         wrap="word",
                         state="disabled")
        self.help.grid(column=0, row=row, sticky=(
            N,
            S,
            E,
            W,
        ), columnspan=4)
        frame.rowconfigure(row, weight=1)
        row += 1

        # action buttons
        aframe = ttk.Frame(frame)
        aframe.grid(column=0, row=row, sticky=(
            E,
            W,
            S,
        ), columnspan=4)
        aframe.columnconfigure(0, weight=1)
        aframe.columnconfigure(1, weight=1)
        aframe.columnconfigure(2, weight=1)
        aframe.columnconfigure(3, weight=1)
        self.dbut = ttk.Button(aframe, text='Down', command=self.triggerdown)
        self.dbut.grid(column=0, row=0, sticky=(
            E,
            W,
        ))
        self.dbut.state(['disabled'])
        self.dbut.bind('<Enter>',
                       lambda event, text=_HELP_DOWN: self.setHelp(text),
                       add='+')
        self.ubut = ttk.Button(aframe, text='Up', command=self.triggerup)
        self.ubut.grid(column=1, row=0, sticky=(
            E,
            W,
        ))
        self.ubut.state(['disabled'])
        self.ubut.bind('<Enter>',
                       lambda event, text=_HELP_UP: self.setHelp(text),
                       add='+')
        lbut = ttk.Button(aframe, text='Load', command=self.loadfile)
        lbut.grid(column=2, row=0, sticky=(
            E,
            W,
        ))
        lbut.focus()
        lbut.bind('<Enter>',
                  lambda event, text=_HELP_LOAD: self.setHelp(text),
                  add='+')
        sbut = ttk.Button(aframe, text='Save', command=self.savefile)
        sbut.grid(column=3, row=0, sticky=(
            E,
            W,
        ))
        sbut.bind('<Enter>',
                  lambda event, text=_HELP_SAVE: self.setHelp(text),
                  add='+')
        row += 1

        # status label
        self.logvar = StringVar(value='Waiting for hoists...')
        self.loglbl = ttk.Label(frame, textvariable=self.logvar)
        self.loglbl.grid(column=0, row=row, sticky=(
            W,
            E,
        ), columnspan=4)
        row += 1

        for child in frame.winfo_children():
            if child is not hdr:
                child.grid_configure(padx=6, pady=4)

        # connect event handlers
        window.bind('<Return>', self.uiupdate)
        window.bind('<<SerialDevEvent>>', self.devevent)
        self.window = window
        self.portsel.focus_set()

        # start device polling
        self.devpoll()
        self.scanio.trigger()


def main():
    logging.basicConfig()
    if len(sys.argv) > 1 and '-v' in sys.argv[1:]:
        _log.setLevel(logging.DEBUG)
        _log.debug('Enabled debug logging')
    sio = SerialConsole()
    sio.start()
    btc = BTCScan()
    btc.start()
    win = Tk()
    app = HHConfig(window=win, devio=sio, scanio=btc)
    win.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
