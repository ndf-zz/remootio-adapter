#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""hhconfig

TK Graphical front-end for Hay Hoist console

"""

import sys
import json
from serial import Serial
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
import threading
import queue
import logging

_log = logging.getLogger('hhconfig')
_log.setLevel(logging.WARNING)

# Constants
_SERPOLL = 0.1
_DEVPOLL = 2000
_BAUDRATE = 19200
_READLEN = 512
_CFGKEYS = {
    'H-P1': '1',
    'P1-P2': '2',
    'Man': 'm',
    'H': 'h',
    'Feed': 'f',
    'Feeds/week': 'n',
}
_TIMEKEYS = (
    'H-P1',
    'P1-P2',
    'Man',
    'H',
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
}
_LOGODATA = b'GIF89a\x9d\x006\x00\xe3\x0f\x00\x00\x00\x00\x003\x9d\x113e\xd2\x00\x00231\xd1723f\x9abeasu\xa0\xd7gl\x90\x96\x93\xcc\x87\x8a\xb4\xaf\xb5\xdd\xaa\xa9\xd2\xd4\xd1\xad\xad\xad!\xf9\x04\x01\n\x00\x0f\x00,\x00\x00\x00\x00\x9d\x006\x00\x00\x04\xfe\xf0\xc9I\xabm8\xeb\xcd\xbb\xff`\xe8Ydi\x8a(f\xaeS\x93\x14C,\xcftm\xdfx\xae\xe3\x0b\xebW\x89\x9dPVh\xfc*\x8bXb\xc1l:\x9f\xd0\xa8tJ\xadF\x0b\xc5\xe3\xf1e\xed2cFmc\x90\xd0\x9a\xcf\xe8\x12\x03@H\x9b\x14lw\tf\x1e\x14\xe4\xf8\xfc\x1b\xa0\xd0S\x0e\x04}~\x12ca>I\x83\x89?\x0c\x07\x8d\x8e\x8e\x04\x91\x8f\x93\x94\x95\x94\x91\x04\x95\x82i\x03\x86,Xf\n\xa2\x8e\x8af\x98\xa7\xa8\xa9\xaa\xab\xac\xac\x07\xa2\n\x0cf\x85Gd?\n\x04l\xa7\x00\xb2\xa5>k\xad\xc1\xc2\xc3\xa8l\x00\xc7\xbd>AG\x88>\x07\xba\xc6\x98\xb0\xd3\xd4\xd5\xd6\xd7\xd8\xb8\xba\xc4\xdc\xdd\xadG\x05e?\xa0,p\x07\x12\xc0\xb9\x81\xd9\xec\xed\xd8\xde\xf0\xf1\xbd\x91?\xb4?v>\xf4\xe8\xdb\xaf\xee\xfe\xff\xdb\xe2\td\x05\xe0\x9c\x04},\x96\xfdh\xc6\x02\xe1\xae\x7f\x10\xdb\x01\x1aHq\x15\x9f\t\x05\xef\x89\xf3A\xae\xa1$u\xfe\xd2"\x8a\xb4V\xb1\xe4*@q\x0eu\xaag\xcb\x07\x9cH\xdb\n\x8e\x9c\t\x8b\x81\xc9\x9b0s\xa5Tv\xe7\x87\xc2[\xaa|\x1d\t\x88\xb3d2\x8e\x1b?\xf5\x14\xca\xf4\x01\x9ccP\xa3J\x9dJ\xb5\xaaU\xa9m\xd2\x04\xf1\xb4be\xd3\xaf`\xc1\xfeL8 \xac\xd9\xb3\x8a:*]\xc1@\x80\x80\x00p\x03\x08X\x117\xee\\\xb4x\xf3$\xe1j\xc2k\t\x04p\xdd\xc2\xddd\xa1\xad[\xc1w\'\xf49\xfa\xa0\x97\xa8d\xa2(0n,\x810\x83M\x91+\x13\xd6,\xe8rgt\x15\x8e\xc2\xd2<\x99\x82\xda\x15cI\xbc\r,w\x85\x81\xbar\x11Th\x935VV\xa7\x0f\xb2\x9e\xcb\x0cg\xc2\xeey\x7f\x04\xdd\xce]\x82\x80\xcd\t\xc6+?8\xc0x8s\xc5\x8cV\x9c61]\xf2\xea\xd5\xb2M\xbc]\xdd\x9a\x82\x82F\x9d\x93;epYB\xc1\xdb\x99\x90\x13o|\xb46aR\x923\x19\\\xdfX\xbcw\n\xb7\xcf\x917\xc1\xd0G\xcb\x12\xaf\xd5\xfe%@i\x95\xb1\x06Wv\xea\xc5\x82\xce&\x81\x18\xe4\x99p\xc7\x1d\xf4\xddA\xafH\x00He\x8dh6\x9fz\xde%S^\x05\xb888_&\xc3YP\x1d\tt\x98\xd0\x96\\v\xadp]`y\xc5(\xc7\x7fk\x99\x00\x18\x8bp\x11\xd8\x98]0\xca\xe8\xa3\x16\xfd\xad`O\t/vG$\x8b\xdb\xe9\xf8\xe3\x92\x13\x9ch\xc1\x0b+ \xc0\xdd`.\x06\xb6\x9d\x04\x06d\x99\xa5\x8dZ\x1a\xd0\xcbe\x08t)\xa6\x01\x0820\xe6\x98\x08(H\xc1\x99lz\xc8@\x98lnY\xc2\x00=\x8c\xb3\x14\t\x07\xc06\xa0\x8dS\x06\x90\xddvFV e\\\xb2\x99)\x18l\x02R0h\x9fV\x1e\x86\xe0\xa2\x88\xea\xe9\x18\xa3z\x1aPB\x90\'\xf8U\x18\xa3Ur\x97\x18\xa0\x89)ZW\xa1\x9enw\xd8a\x96N\x80\xe8\xa9V\xc2\x95\xea\x03}\x9ez\xd8\x81\x12\x00&+\xab\x81\x11\xe8$\x10wZ\xa0\x00\xa3\xb7\xe2\xca\xdd\xaby^)\xe8u\x824\x1al\x92\x13\xfe\xd8\xaa,\xae\xb46v\xe8\xb2\x87\xc9\xa2\x80\x80\xa6\xca\xbaa\x054J\xd7k\x05\x94R*\xa0\\{J`j\x00\xa2q\x97\xdd\xaf\x81\xbd\xca\xc2k\xccV\x10\xa0[\xd9\xc1+\x97\x92\xd2\x92[\xae\x19\xa9e\xcaW\xb3\x91\xea\x19p\x8f\xb5\xe2\xb8\xc9\x8a\xd1\xc2\xda\xe2"\x87\xba;\xc1\xbc\xe8\x9a{\x9d\x0f7\xba\x85\xef\x1c\xdf\x96\x00\xa5v8\x0e\xec1a7F\x8b\xb0\x00e"\x86 \x0b!\xef;\x01\xc2\x01\xa4\xca\xae\\\x9b\xa9\x16\xd7\xb6G\x8c\x911\t\xf8\xa8\x11+\xb5\xc0\x866\xaa\xc4\xaeR0\xe5\xc9U\x12\xec\xdd\xa1\xbd\\7 yL\xef\xd7,\xd2i`Z\xc2\x90\x16\x14k\x17\x02Mg\x1d2\xa1\x16l\xf7\xa7\x95\xd6a\x1b\xec\xc9\x15\x07\x103\xac\x13\xefH\xae\xbe\xb2\n\x9d6\x1a\xbbR\xb0\xf1\x91\x9e\x16\xbd0\xb8~Z\x88dh\xb3zL\xb2oVN&\xe5jI{Lee\x87\x12\xadE\xb7\xd4%u,l\x8a\xaf\x1c\xabj\xf5\xde-\xb4\xdf\xfeq\xa5:\xf2\xb9\x8d\xc25\x9f\xa7\xab\x86\x9a\xf2\xc5$HM\x02\xd5\xe0N\xa9\xb2\xa0z\x9em\xd0\xa0\x81Jv\xc0\xb2\x02\n\xb2\xf5\xb8\x92\x16\x9c\xb9\x02\x08\xf4\xee\xfb\xc9\xc3\xba\x11\xf7\x04\xfdJ>\xa5\xc3a\'j\xe3\xdeh\x04h$\xa0\x9d\xeby\xb9\xb1+\\\x9b\xab\x1b\x8c\xcf\xe1\xf8\x9a\xb9\xff\xa5g\xe4\x05^\x8f\x06\xa8\xb5\x82\xba\xac\x01\x96\x01\n\xfe\xe5F\x9b\x91\xa2\x0f\xa8\xb3\xff\xb6\xcc\xca\x93P6\xe9\x16\xdco.\xd8G\xbcH1wg\xb3\xd3\x16n\xf6\x00H\xc1LE\xa0C\xde\x04\xea\x86\x06\xd8\xb9\x05\x1d8Z\x1f\xdf\xc8e)\xa7\xb1\x872\x0fp\xde\xdfBc\xc19m\xcf\x83\x1c\xc3Q\xa8,\xe0<\xae\x91\xe0W\xab9\x9bax\xa6\xaf^\xd8k\x84Q\x8a\x9e\xd8\xee\x02=\x9e\x05\xf0\x01\xc5;\x9d\xa6\xbc\x83(\x05.\x90U0\\\xa0\xe5D5\xc3C%lJG`Y\xc0\xbc\xb6?}\xad*v\x15\x18\x9e\x04\xe6\xd65\'\xae\x8e\x87\x02Z\x1f\xfe\xa0h\x96/\xc3Y\xeci\xf1\xfa\x85\xac\x06\x96\x18\xd8\x91Q\x82t\xaaE\x9dNX\x8d\xea\xb5\xb1\x04\xbc\xf3\x9d\x8d\xe0\xc4\xa6\x98\xfdN\x82\x82\xba\xa3\x1e}\xb7\x19:\x8aI\x8e&\xc8\xe1\x05\xd2\xc8\xa4B\xc6H\x8a8$\xa0!\x17)\x94\x1dRG\x91\x8c\x8c\xa4\x1f\xde\xc7\x91\xb2H\xf2\x92\xbe@\xe4\x03\xc6\xf0\xc1\x16``\x01\x18H@\x02\\P\x86\x0e\xe0P\x94\xe2\x10\xe5\x02F\xb9\x04R\x16\x80\x01F(\x83(\xb1\x80\xcaP\x12\xa2\x07\xa3$\xe5\x14E\xd9\x00&\xa0\xf2\x05\xb5\xec\xe5\x03V\xb9\x04T\x9e2\x97\xc7\xfc\xe5&I\xd9K\x0c\x84C\x19\x8eD\x8d\x1d~)JB\x80B\x95\xbdd%)AY\x04#,\x80\x01k\\\xc24i\t\xceb\xba@\x03\xab<\xe53\x1f\x10\x8e\x06\xd0\xd2\x9d\x12(@\x0f\xe4\xb9\x04p\xdar\x96\xb1L\xa4,\xb9yNx\xf2\xf2\x05\xb4\x94\xa7;YI\x08j\xfe\x12\x0chp\'\rz\xc2M\x1c\x9e3\x1c\xe1H\x02/l\x05\xea\xces6f\xa2\xa3l\xe7\x1d\x8a\x00\x83\x0c\xf0\x13\x98\xa5|g\x116\xe6\x02vn\xd2\x98\xff\\\xa5\x11F\xfa\xccjj\xb3\xa2/h\x00\x03j\xa9\xcae\x88#\t7\x18\xa5\x1cd\xca\xb4\x13d`\x99\x9b\x84\xa5\x118\xb0L\xbe\x84a\xa8\x9b$\x04,ea\x88\xa1\x0e\x15\x96\x9e\\\x99\'~\xda\x02\xa1\x1a\xa1\x17\xa6\xbc\xc0O\x91\xaa\xd4\xa6\xc9\xd4\r\x11\x00\x00;'


def _subkey(key):
    if key in _KEYSUBS:
        key = _KEYSUBS[key]
    return key


def _mkopt(parent, prompt, units, row, validator, update):
    ttk.Label(parent, text=prompt).grid(column=0, row=row, sticky=(E, ))
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
    ttk.Label(parent, text=units).grid(column=2,
                                       row=row,
                                       sticky=(W, ),
                                       columnspan=2)
    ent.bind('<FocusOut>', update, add='+')
    return svar


class SerialConsole(threading.Thread):
    """Serial console command/response wrapper"""

    # UI-safe functions

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
        return self._portdev is not None and self.cfg is not None

    def update(self, cfg):
        """Update all keys in cfg on attached device"""
        self._cqueue.put_nowait(('_update', cfg))
        if len(cfg) > 1:
            self._cqueue.put_nowait(('_message', 'Device updated'))

    def down(self, data=None):
        """Request down trigger"""
        self._cqueue.put_nowait(('_down', data))

    def up(self, data=None):
        """Request up trigger"""
        self._cqueue.put_nowait(('_up', data))

    def exit(self, msg=None):
        """Request thread termination"""
        self._running = False
        self._cqueue.put_nowait(('_exit', msg))

    def setport(self, device=None):
        """Request new device address"""
        self._flush()
        self._cqueue.put_nowait(('_port', device))

    def status(self, data=None):
        """Request update of device status"""
        self._sreq += 1
        self._cqueue.put_nowait(('_status', data))

    def __init__(self):
        threading.Thread.__init__(self, daemon=True)
        self._sreq = 0
        self._portdev = None
        self.portdev = None
        self._cqueue = queue.Queue()
        self._equeue = queue.Queue()
        self._running = False
        self.cb = self._defcallback
        self.cfg = None

    # Thread-private functions

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
        return rb

    def _update(self, cfg):
        for k in cfg:
            kv = _subkey(k)
            cmd = _CFGKEYS[kv] + str(cfg[k]) + '\r\n'
            self._send(cmd.encode('ascii', 'ignore'))
            self._readresponse()

    def _status(self, data=None):
        self._send(b's')
        self._readresponse()
        if self._sreq != 0:
            _log.debug('No response to status request, closing device')
            self._close()

    def _setvalue(self, key, value):
        if self.cfg is None:
            self.cfg = {}
        k = _subkey(key)
        if k == 'Firmware':
            self.cfg[k] = value
            self._equeue.put(('firmware', value))
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
            elif '=' in l:
                lv = l.split(' = ', maxsplit=1)
                if len(lv) == 2:
                    self._setvalue(lv[0].strip(), lv[1].strip())
                    docb = True
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

    def _readstatus(self):
        rb = self._recv(_READLEN)
        ret = None
        if rb:
            m = rb.decode('ascii', 'ignore').strip()
            if m.startswith('State:'):
                ret = m.split(': ', maxsplit=1)[1].strip()
        return ret

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
            self._portdev = Serial(port=self.portdev,
                                   baudrate=_BAUDRATE,
                                   rtscts=False,
                                   timeout=_SERPOLL)
        return self._portdev is not None

    def _getvalues(self):
        self._send(b'v')
        self._readresponse()

    def _port(self, port):
        if self.connected():
            self._close()
        self.portdev = port
        if self._serialopen():
            self._status()
            self.cfg = {}
            self._getvalues()
            if len(self.cfg) > 0:
                self._equeue.put((
                    'connect',
                    None,
                ))
                self.cb()

    def _exit(self, msg):
        self._close()
        self._flush()
        self._running = False

    def _close(self):
        if self._portdev is not None:
            self.cfg = None
            self._portdev.close()
            self._portdev = None
            self._equeue.put((
                'disconnect',
                None,
            ))
            self.cb()

    def _flush(self):
        try:
            while True:
                self._cqueue.get_nowait()
                self._cqueue.task_done()
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
        """Update the list of available comports"""
        self._ioports = []
        self._ionames = []
        devs = {}
        try:
            from serial.tools.list_ports import comports
            for port in comports():
                devs[port.device] = str(port)
        except Exception:
            pass
        for cp in sorted(devs):
            self._ioports.append(cp)
            self._ionames.append(devs[cp])

    def check_cent(self, newval, op):
        """Validate text entry for a time value in hundredths"""
        ret = False
        if newval:
            try:
                v = int(float(newval) * 100)
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
        """Handle device connection event"""
        # initiate transfer of ui-entered values to new device
        self.devval = {}
        if self.devio.connected():
            self.logvar.set('Device connected')
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

    def disconnect(self):
        """Handle device disconnection event"""
        if self.fwval.get():
            self.logvar.set('Device disconnected')
        self.statvar.set('[Not Connected]')
        self.devval = {}
        for k in _CFGKEYS:
            self.devval[k] = None
        self.dbut.state(['disabled'])
        self.ubut.state(['disabled'])
        self.fwval.set('')

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
                key = _subkey(evt[1])
                val = evt[2]
                if key in _CFGKEYS:
                    self.devval[key] = val
                    self.logvar.set('Updated option ' + key)
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

    def devpoll(self):
        """Request update from attached device / reinit connection"""
        try:
            if self.devio.connected():
                self.devio.status()
            else:
                # not connected, begin a re-connnect sequence
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
                t = max(int(float(nv) * 100), 1)
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

    def uiupdate(self, data=None):
        """Check for required updates and send to attached device"""
        for k in _TIMEKEYS:
            self.xfertimeval(k)
        for k in _INTKEYS:
            self.xferintval(k)

        # if connected, update device
        if self.devio.connected():
            cfg = {}
            for k in self.devval:
                if k in self.uval and self.uval[k] is not None:
                    if self.uval[k] != self.devval[k]:
                        cfg[k] = self.uval[k]
            if cfg:
                _log.debug('Sending %d updated values to device', len(cfg))
                self.logvar.set('Updating device...')
                self.devio.update(cfg)

    def portchange(self, data):
        """Handle change of selected serial port"""
        selid = self.portsel.current()
        if selid is not None:
            if self._ioports and selid >= 0 and selid < len(self._ioports):
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
        for k in cfg:
            kv = _subkey(k)
            if kv in _TIMEKEYS:
                try:
                    self.uival[kv].set('%0.2f' % (cfg[k] / 100.0, ))
                    doupdate = True
                except Exception:
                    pass
            elif kv in _INTKEYS:
                try:
                    self.uival[kv].set('%d' % (cfg[k], ))
                    doupdate = True
                except Exception:
                    pass
            else:
                _log.debug('Ignored invalid config key %r', k)
        if doupdate:
            self.uiupdate()

    def flatconfig(self):
        """Return a flattened config for the current values"""
        cfg = {}
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

    def __init__(self, window=None, devio=None):
        self.devio = devio
        self.devio.cb = self.devcallback
        window.title('Hay Hoist Config')
        frame = ttk.Frame(window, padding="5 5 10 10")
        frame.grid(column=0, row=0, sticky=(
            E,
            S,
            W,
            N,
        ))
        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(9, weight=1)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        # header block / status
        self._logo = PhotoImage(data=_LOGODATA)
        hdr = ttk.Label(frame, text='Hay Hoist')
        hdr['image'] = self._logo
        hdr.grid(column=0, row=0, columnspan=2, sticky=(
            E,
            W,
        ))

        self.statvar = StringVar(value='[Not Connected]')
        self.statlbl = ttk.Label(frame, textvariable=self.statvar)
        self.statlbl.grid(column=2, row=0, sticky=(
            E,
            S,
        ), columnspan=2)
        ttk.Separator(frame, orient=HORIZONTAL).grid(column=0,
                                                     row=1,
                                                     columnspan=4,
                                                     sticky=(
                                                         E,
                                                         W,
                                                     ))

        # io port setting
        self._ioports = []
        self._ionames = []
        self.getports()
        ttk.Label(frame, text="Port:").grid(column=0, row=2, sticky=(E, ))
        self.portsel = ttk.Combobox(frame)
        self.portsel['values'] = self._ionames
        self.portsel.state(['readonly'])
        self.portsel.bind('<<ComboboxSelected>>', self.portchange)
        if self._ionames:
            self.portsel.current(0)
        self.portsel.grid(column=1, row=2, sticky=(
            E,
            W,
        ), columnspan=3)

        # device values
        self.devval = {}
        self.uval = {}
        for k in _CFGKEYS:
            self.devval[k] = None
            self.uval[k] = None

        # validators
        check_cent_wrapper = (window.register(self.check_cent), '%P', '%V')
        check_int_wrapper = (window.register(self.check_int), '%P', '%V')

        # config options
        self.uival = {}
        self.uival['H-P1'] = _mkopt(frame, "H-P1:", "seconds", 3,
                                    check_cent_wrapper, self.uiupdate)
        self.uival['P1-P2'] = _mkopt(frame, "P1-P2:", "seconds", 4,
                                     check_cent_wrapper, self.uiupdate)
        self.uival['Man'] = _mkopt(frame, "Man:", "seconds", 5,
                                   check_cent_wrapper, self.uiupdate)
        self.uival['H'] = _mkopt(frame, "Home:", "seconds", 6,
                                 check_cent_wrapper, self.uiupdate)
        self.uival['Feed'] = _mkopt(frame, "Feed:", "minutes", 7,
                                    check_int_wrapper, self.uiupdate)
        self.uival['Feeds/week'] = _mkopt(frame, "Feeds/week:", "(max 5000)",
                                          8, check_int_wrapper, self.uiupdate)

        # firmware version label
        ttk.Label(frame, text='Version:').grid(column=0, row=9, sticky=(E, ))
        self.fwval = StringVar()
        ttk.Label(frame, textvariable=self.fwval).grid(column=1,
                                                       row=9,
                                                       sticky=(W, ),
                                                       columnspan=3)

        # action buttons
        aframe = ttk.Frame(frame)
        aframe.grid(column=0, row=10, sticky=(
            E,
            W,
            S,
        ), columnspan=4)
        aframe.columnconfigure(0, weight=1)
        self.dbut = ttk.Button(aframe, text='Down', command=self.triggerdown)
        self.dbut.grid(column=1, row=0, sticky=(E, ))
        self.dbut.state(['disabled'])
        self.ubut = ttk.Button(aframe, text='Up', command=self.triggerup)
        self.ubut.grid(column=2, row=0, sticky=(E, ))
        self.ubut.state(['disabled'])
        lbut = ttk.Button(aframe, text='Load', command=self.loadfile)
        lbut.grid(column=3, row=0, sticky=(E, ))
        lbut.focus()
        sbut = ttk.Button(aframe, text='Save', command=self.savefile)
        sbut.grid(column=4, row=0, sticky=(E, ))

        ttk.Separator(frame, orient=HORIZONTAL).grid(column=0,
                                                     row=11,
                                                     columnspan=4,
                                                     sticky=(
                                                         E,
                                                         W,
                                                     ))

        # status label
        self.logvar = StringVar(value='Waiting for device...')
        self.loglbl = ttk.Label(frame, textvariable=self.logvar)
        self.loglbl.grid(column=0, row=12, sticky=(
            W,
            E,
        ), columnspan=4)

        for child in frame.winfo_children():
            child.grid_configure(padx=2, pady=2)

        # connect event handlers
        window.bind('<Return>', self.uiupdate)
        window.bind('<<SerialDevEvent>>', self.devevent)
        self.window = window

        # start device polling
        self.devpoll()


def main():
    logging.basicConfig()
    if len(sys.argv) > 1 and sys.argv[1] == '-v':
        _log.setLevel(logging.DEBUG)
        _log.debug('Enabled debug logging')
    sio = SerialConsole()
    sio.start()
    win = Tk()
    app = HHConfig(window=win, devio=sio)
    win.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
