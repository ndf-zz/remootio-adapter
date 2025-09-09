#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""hhconfig

Crude TK Graphical front-end for Hay Hoist serial console

"""
__version__ = '1.2.0'

import os
import re
import sys
import json
from serial import Serial
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from base64 import b64decode
import threading
import queue
import logging
from time import sleep

_log = logging.getLogger('hhconfig')
_log.setLevel(logging.WARNING)

# Constants
_CFGFILE = '.hh.cfg'
_HELP_ACN = 'ACN: Hoist serial console access code number (v25001)'
_HELP_HP1 = 'H-P1: Time in seconds hoist requires to move \
down from home to position P1 (feed)'

_HELP_P1P2 = 'P1-P2: Time in seconds hoist requires to move \
down from position P1 (feed) to P2 (ground)'

_HELP_MAN = 'Man: Manual override adjustment time in seconds'
_HELP_HOME = 'Home: Maximum time in seconds hoist will raise \
toward home position before flagging error condition'

_HELP_HOMERETRY = 'Home-Retry: Retry return home after \
this many seconds (v25001)'

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
_VER_ACN = 25001
_VER_RETRY = 25001
_SERPOLL = 0.2
_DEVPOLL = 3000
_ERRCOUNT = 2  # Tolerate two missed status before dropping connection
_DEVRETRY = 2  # If devpoll gets stuck waiting for status, restart
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
_SPINKEYS = (
    'H-P1',
    'P1-P2',
)
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
    'p': 'ACN',
}

_LOGODATA = b64decode(b'\
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\
QmCC\
')


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
           helptext='',
           optionKey=None):
    prompt = ttk.Label(parent, text=prompt)
    prompt.grid(column=0, row=row, sticky=(E, ))
    svar = StringVar()
    ent = None
    if optionKey in _SPINKEYS:
        ent = ttk.Spinbox(parent,
                          textvariable=svar,
                          width=6,
                          justify='right',
                          validate='key',
                          validatecommand=validator,
                          command=update,
                          from_=0.0,
                          to=120.0,
                          increment=0.5)
    else:
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
    return svar, ent


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

    def updateacn(self, acn):
        """Update the auth acn on attached device"""
        self._cqueue.put_nowait(('_updateacn', acn))
        self._cqueue.put_nowait(('_message', 'Console ACN updated'))

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

    def setacn(self, acn):
        self._acn = acn

    def __init__(self):
        threading.Thread.__init__(self, daemon=True)
        self._acn = 0
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

    def _updateacn(self, acn):
        self._acn = acn
        if self.connected() and self.configured():
            cmd = 'p' + str(acn) + '\r\n'
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
        """Send console ACN"""
        cmd = '\x10' + str(self._acn) + '\r\n'
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
        elif key == 'ACN':
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
                self._equeue.put(('message', l))
                docb = True
                if l.startswith('Trigger:'):
                    if 'reset' in l:
                        # re-auth required
                        self._cqueue.put_nowait(('_auth', None))
            elif '=' in l:
                lv = l.split(' = ', maxsplit=1)
                if len(lv) == 2:
                    key = _subkey(lv[0].strip())
                    if key != 'ACN':
                        self._setvalue(key, lv[1].strip())
                        docb = True
                        if self.configured() and not wasconfigured:
                            self._equeue.put((
                                'connect',
                                None,
                            ))
                    else:
                        _log.debug('ACN Updated')

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
    """TK Hay Hoist serial console utility"""

    def getports(self):
        """Update the list of available ports"""
        self._ioports = []
        self._ionames = []

        devs = {}
        try:
            from serial.tools.list_ports import comports
            for port in comports():
                devname = str(port)
                if ' n/a' not in devname:
                    devs[port.device] = devname
        except Exception:
            pass
        if devs:
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

    def checkversion(self, fwver):
        """Disable unavailable elements based on firmware"""
        fvno = 0
        fwver = fwver.lstrip('v')
        if fwver and fwver.isdigit():
            fvno = int(fwver)
        if fvno < _VER_ACN:
            _log.debug('ACN entry disabled: %d < %d', fvno, _VER_ACN)
            self.acnentry.state(['disabled'])
            self.acnenabled = False
        else:
            self.acnentry.state(['!disabled'])
            self.acnenabled = True
        if fvno < _VER_RETRY:
            _log.debug('Home-Retry entry disabled: %d < %d', fvno, _VER_RETRY)
            self.retryentry.state(['disabled'])
            self.enabled['H-Retry'] = False
        else:
            self.retryentry.state(['!disabled'])
            self.enabled['H-Retry'] = True

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
                self.checkversion(evt[1])
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
        self.window.event_generate('<<SerialDevEvent>>', when='tail')

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
        if k not in self.uival:
            _log.warning('xfertimeval key %s not in uival', k)
            return
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
        if k not in self.uival:
            _log.warning('xferint key %s not in uival', k)
            return
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
            if k in self.devval and self.devval[k] is not None:
                v = self.devval[k]
                fv = '%d' % (v, )

        self.uval[k] = v
        if fv is not None and fv != nv:
            self.uival[k].set(fv)

    def _saveacn(self):
        """Write the cache acn config"""
        try:
            with open(_CFGFILE, 'w') as f:
                f.write('%d\r\n' % (self.acn, ))
        except Exception as e:
            _log.error('%s saving cfg: %s', e.__class__.__name__, e)

    def xferacn(self):
        """Check for an updated console ACN"""
        if self.acnenabled:
            newacn = self.acn
            try:
                pv = self.acnval.get()
                if pv and pv.isdigit():
                    newacn = int(pv)
                else:
                    newacn = 0
            except Exception as e:
                pass
            if newacn != self.acn:
                if newacn == 0:
                    self.acnval.set('')
                self.acn = newacn
                self._saveacn()
                self.devio.updateacn(self.acn)
        else:
            _log.debug('ACN disabled due to firmware')

    def hp1update(self, data=None):
        """Process a change in the H-P1 time"""
        oldp1 = self.uval['H-P1']
        oldp2 = self.uval['P1-P2']
        self.xfertimeval('H-P1')
        newp1 = self.uval['H-P1']
        if newp1 != oldp1:
            diff = newp1 - oldp1
            newp2 = max(0, min(oldp2 - diff, 12000))
            fv = '%0.2f' % (newp2 / 100.0, )
            self.uival['P1-P2'].set(fv)
        self.uiupdate()

    def uiupdate(self, data=None):
        """Check for required updates and send to attached device"""
        _log.debug('uiupdate')
        for k in _TIMEKEYS:
            self.xfertimeval(k)
        for k in _INTKEYS:
            self.xferintval(k)
        self.xferacn()

        # if connected, update device
        if self.devio.connected():
            cfg = {}
            for k in self.devval:
                if self.enabled[k]:
                    if k in self.uval and self.uval[k] is not None:
                        if self.uval[k] != self.devval[k]:
                            cfg[k] = self.uval[k]
                else:
                    _log.debug('Config key %s disabled due to firmware level',
                               k)
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
            elif k == 'ACN':
                if isinstance(cfg[key], int):
                    if cfg[key] != self.acn:
                        if cfg[key]:
                            self.acnval.set('%d' % (cfg[key], ))
                        else:
                            self.acnval.set('')
                        _log.debug('Console ACN updated')
                        doupdate = True
            else:
                _log.debug('Ignored invalid config key %r', k)
        if doupdate:
            self.uiupdate()

    def flatconfig(self):
        """Return a flattened config for the current values"""
        cfg = {}
        cfg['ACN'] = self.acn
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

    def _loadacn(self):
        """Check for a cached access control number config"""
        if os.path.exists(_CFGFILE):
            with open(_CFGFILE) as f:
                a = f.read().strip()
                if a and a.isdigit():
                    aval = int(a)
                    if aval > 0 and aval < 65535:
                        self.acn = aval

    def __init__(self, window=None, devio=None):
        self.acn = 0
        self._loadacn()
        self.devio = devio
        self.devio.cb = self.devcallback
        self.devio.setacn(self.acn)
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

        # ACN entry
        self.acnenabled = True
        self.acnval, self.acnentry = _mkopt(frame, "ACN:", "", row,
                                            check_int_wrapper, self.uiupdate,
                                            self.setHelp, _HELP_ACN)
        if self.acn:  # is nonzero
            self.acnval.set(str(self.acn))
        row += 1

        # device values
        self.enabled = {}
        self.devval = {}
        self.uval = {}
        for k in _CFGKEYS:
            self.devval[k] = None
            self.uval[k] = None
            self.enabled[k] = True

        # config options
        self.uival = {}
        self.uival['H-P1'], junk = _mkopt(frame, "H-P1:", "seconds", row,
                                          check_cent_wrapper, self.hp1update,
                                          self.setHelp, _HELP_HP1, 'H-P1')
        row += 1
        self.uival['P1-P2'], junk = _mkopt(frame, "P1-P2:", "seconds", row,
                                           check_cent_wrapper, self.uiupdate,
                                           self.setHelp, _HELP_P1P2, 'P1-P2')
        row += 1
        self.uival['Man'], junk = _mkopt(frame, "Man:", "seconds", row,
                                         check_cent_wrapper, self.uiupdate,
                                         self.setHelp, _HELP_MAN)
        row += 1
        self.uival['H'], junk = _mkopt(frame, "Home:", "seconds", row,
                                       check_cent_wrapper, self.uiupdate,
                                       self.setHelp, _HELP_HOME)
        row += 1
        self.uival['H-Retry'], self.retryentry = _mkopt(
            frame, "Home-Retry:", "seconds", row, check_cent_wrapper,
            self.uiupdate, self.setHelp, _HELP_HOMERETRY)
        row += 1
        self.uival['Feed'], junk = _mkopt(frame, "Feed:", "minutes", row,
                                          check_int_wrapper, self.uiupdate,
                                          self.setHelp, _HELP_FEED)
        row += 1
        self.uival['Feeds/week'], junk = _mkopt(frame, "Feeds/week:",
                                                "(max 5000)", row,
                                                check_int_wrapper,
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
        lbl = ttk.Label(frame, text=__version__)
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


def main():
    logging.basicConfig()
    if len(sys.argv) > 1 and '-v' in sys.argv[1:]:
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
