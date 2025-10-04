#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""blehhconfig

Bluetooth Config tool for Hay Hoist

Usage: blehhconfig [-v]

"""
__version__ = '1.0.0'

import os
import sys
import json
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from base64 import b64decode  # Embedded logo
from contextlib import suppress
from struct import pack
import threading
import queue
import logging
import asyncio
from bleak import BleakClient, BleakScanner

_log = logging.getLogger('blehhconfig')
_log.setLevel(logging.WARNING)

# Constants
_CFGFILE = '.blehh.cfg'
_DEVPOLL = 8000  # Poll connected hoist status after ~8s
_ERRCOUNT = 2  # Tolerate 2 missed status requests before dropping connection
_DEVRETRY = 5  # If devpoll gets stuck waiting on connect, restart
_CFG_LEN = 8  # Number of required config elements for full connection
_BLE_MID = 0xffff  # TBC BLE Manufactuter ID
_CHARGEDVOLTS = 13.2  # Low charge state threshold
_LOWVOLTS = 11.8  # Low voltage threshold, Remootio access is disabled
_BLE_READTIME = 2.0  # timeout for command response
_BLE_SCANTIME = 5.0  # maximum scan time
_BLE_CNAMELEN = 6  # Maximum valid encoded CNAME length
_BLE_PINMAX = 999999  # Maximum BLE PIN
_PIN_UUID = '0000b0a4-99c7-4647-956b-8a57cb5907d9'
_RX_UUID = '0001b0a4-99c7-4647-956b-8a57cb5907d9'
_TX_UUID = '0010b0a4-99c7-4647-956b-8a57cb5907d9'
_CNAME_UUID = '0100b0a4-99c7-4647-956b-8a57cb5907d9'
_DNAME_UUID = '1000b0a4-99c7-4647-956b-8a57cb5907d9'
_FOTA_UUID = 'f07ab0a4-99c7-4647-956b-8a57cb5907d9'
_DEV_UUID = '2a00'
_FWVER_UUID = '2a26'

# Help messages
_HELP_LOC = 'Location: Hoist identifier eg H1F2'
_HELP_PIN = 'Pairing PIN: Bluetooth pairing PIN (write only)'
_HELP_ACN = 'ACN: Hoist serial console access code number'
_HELP_HP1 = 'H-P1: Time in seconds hoist requires to move \
down from home to position P1 (feed)'

_HELP_SP1 = 'Set P1 by manual control'

_HELP_P1P2 = 'P1-P2: Time in seconds hoist requires to move \
down from position P1 (feed) to P2 (ground)'

_HELP_SP2 = 'Set P2 by manual control'

_HELP_MAN = 'Adjust: Position adjustment time in seconds'
_HELP_HOME = 'Home: Maximum time in seconds hoist will raise \
toward home position before flagging error condition'

_HELP_HOMERETRY = 'Home-Retry: Retry return to home after \
this many seconds'

_HELP_FEED = 'Feed: Return hoist automatically from P1 (feed) to \
home position after this many minutes (0 = disabled)'

_HELP_FEEDWEEK = 'Feeds/week: Schedule this many randomly spaced \
feeds per week (0 = disabled)'

_HELP_DOWN = 'Send down command to connected hoist'
_HELP_UP = 'Send up command to connected hoist'
_HELP_LOAD = 'Load configuration values from file and update connected hoist'
_HELP_SAVE = 'Save current configuration values to file'
_HELP_TOOL = 'Hyspec Hay Hoist Bluetooth config v%s, MIT License.\n\
Source: https://pypi.org/project/blehhconfig/\n\
Support: https://hyspec.com.au/' % (__version__)

_HELP_PORT = 'Hoist device, select to re-connect'
_HELP_STAT = 'Current status of connected hoist'
_HELP_FIRMWARE = 'Firmware version of connected hoist'

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


def _subkey(key):
    """Translate key string to dict value"""
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
    """Create UI controls and return value, entry"""
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
    lbl.grid(column=2, row=row, sticky=(W, ))  #, columnspan=2)
    ent.bind('<FocusOut>', update, add='+')
    if help is not None and helptext:
        prompt.bind('<Enter>',
                    lambda event, text=helptext: help(text),
                    add='+')
        ent.bind('<Enter>', lambda event, text=helptext: help(text), add='+')
        lbl.bind('<Enter>', lambda event, text=helptext: help(text), add='+')
    return svar, ent


class BleConsole(threading.Thread):
    """Bluetooth (bleak) console command/response wrapper for hay hoist"""

    def get_event(self):
        """Return next available UI event from response queue or None"""
        m = None
        try:
            m = self._equeue.get_nowait()
        except queue.Empty:
            pass
        return m

    def connected(self):
        """Return True if Bluetooth client is defined"""
        return self._portdev is not None

    def configured(self):
        """Return True if hoist config has been read"""
        return self.cfg is not None and len(self.cfg) > _CFG_LEN

    def inproc(self):
        """Return True if Bluetooth connect or disconnect underway"""
        return self._portinproc or self._closeinproc

    def flush(self):
        """Clear all pending requests from command queue"""
        try:
            while True:
                c = self._cqueue.get_nowait()
                _log.debug('Flush queued command: %r', c)
        except queue.Empty:
            pass

    def message(self, msg):
        """Queue message to be returned after other requests are processed"""
        self._cqueue.put_nowait(('_message', msg))

    def setpin(self, pin):
        """Update Bluetooth pairing PIN on connected hoist"""
        if isinstance(pin, int) and pin >= 0 and pin <= _BLE_PINMAX:
            pv = pack('<L', pin)
            self._cqueue.put_nowait(
                ('_setblechar', _PIN_UUID, pv, 'Pairing PIN'))
        else:
            _log.debug('Ignored invalid pin: %r', pin)
            self.message('Invalid PIN ignored')

    def setdname(self, dname):
        """Update Bluetooth device name on connected hoist"""
        self._cqueue.put_nowait(
            ('_setblechar', _DNAME_UUID, dname, 'Device Name'))

    def setcname(self, cname):
        """Update Bluetooth location ID on connected hoist"""
        self._cqueue.put_nowait(
            ('_setblechar', _CNAME_UUID, cname, 'Location ID'))

    def updateacn(self, acn):
        """Update the console ACN on connected hoist"""
        self._cqueue.put_nowait(('_updateacn', acn))
        self._cqueue.put_nowait(('_message', 'Console ACN updated'))

    def update(self, cfg):
        """Update keys in cfg on connected hoist"""
        self._cqueue.put_nowait(('_update', cfg))
        cl = len(cfg)
        if cl > 1:
            self._cqueue.put_nowait(
                ('_message', 'Updated %d value%s on hoist' % (
                    cl,
                    '' if cl == 1 else 's',
                )))

    def down(self, data=None):
        """Request down trigger"""
        self._cqueue.put_nowait(('_down', data))

    def up(self, data=None):
        """Request up trigger"""
        self._cqueue.put_nowait(('_up', data))

    def status(self, data=None):
        """Request update of status on connected hoist"""
        self._sreq += 1
        self._cqueue.put_nowait(('_status', data))

    def setport(self, device=None):
        """Request new hoist connection"""
        self._cqueue.put_nowait(('_port', device))

    def setacn(self, acn):
        """Save console ACN"""
        self._acn = acn

    def exit(self):
        """Request thread termination"""
        self._running = False
        self._cqueue.put_nowait(('_disconnect', True))
        self._cqueue.put_nowait(('_exit', True))

    def run(self):
        """Thread main loop, called by object.start()"""
        self._running = True
        return asyncio.run(self._blemain())

    def __init__(self):
        threading.Thread.__init__(self, daemon=False)
        self._stopscan = asyncio.Event()
        self._startscan = asyncio.Event()
        self._resp = asyncio.Event()
        self._acn = 0
        self._sreq = 0
        self._portbuf = bytearray()
        self._portdev = None
        self._loop = None
        self.portdev = None
        self._cqueue = queue.SimpleQueue()
        self._equeue = queue.SimpleQueue()
        self._running = False
        self._portinproc = False
        self._closeinproc = False
        self.cb = self._defcallback
        self.cfg = None

    async def _setblechar(self, char, val, label=None):
        """Write val to BLE characteristic char"""
        if label is None:
            label = char
        _log.debug('BLE Write %s [%s]: %r', label, char, val)
        await self._portdev.write_gatt_char(char, val, True)
        await self._message('Updated %s OK' % (label, ))

    async def _waitresp(self):
        """Wait for a response from connected hoist"""
        try:
            await asyncio.wait_for(self._resp.wait(), timeout=_BLE_READTIME)
        except TimeoutError:
            _log.debug('Response timeout')

    async def _blescan_cb(self, device=None, adv=None):
        """Scanner detection callback"""
        if adv.manufacturer_data is not None:
            if _BLE_MID in adv.manufacturer_data:
                cname = adv.manufacturer_data[_BLE_MID][0:_BLE_CNAMELEN]
                if cname:
                    dname = '[Unknown Device]'
                    if adv.local_name is not None:
                        dname = adv.local_name  # filled after pairing
                    namestr = cname.decode('utf-8', 'ignore').rstrip('\x00')
                    ioname = ' %s - %s' % (
                        dname,
                        namestr,
                    )
                    self._equeue.put(('scan', device, ioname))
                    self.cb()

    async def _waitscan(self):
        """Wait for the bluetooth scanner to end"""
        try:
            await asyncio.wait_for(self._stopscan.wait(),
                                   timeout=_BLE_SCANTIME)
        except TimeoutError:
            _log.debug('Scanner done')

    async def _blescan(self):
        """Bluetooth scanner background task"""
        while self._running:
            try:
                await self._startscan.wait()
                self._startscan.clear()
                async with BleakScanner(detection_callback=self._blescan_cb,
                                        scanning_mode='active') as s:
                    await self._waitscan()
                    await s.stop()
            except Exception as e:
                _log.debug('%s in scanner task: %s', e.__class__.__name__, e)
                self.message(str(e))
                await asyncio.sleep(1)

    async def _blecq(self):
        """BLE Command Queue task"""
        self._startscan.set()
        while self._running:
            c = await self._loop.run_in_executor(None, self._cqueue.get)
            if c is not None:
                await self._proccmd(c)
        self._stopscan.set()
        self._startscan.set()

    async def _blemain(self):
        """Async bleak interface wrapper"""
        self._loop = asyncio.get_running_loop()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._blescan())
            tg.create_task(self._blecq())
        return None

    async def _updateacn(self, acn):
        self._acn = acn
        if self.connected() and self.configured():
            cmd = 'p' + str(acn) + '\r\n'
            await self._send(cmd.encode('ascii', 'ignore'))
            await self._waitresp()

    async def _update(self, cfg):
        for k in cfg:
            cmd = _CFGKEYS[k] + str(cfg[k]) + '\r\n'
            await self._send(cmd.encode('ascii', 'ignore'))
            await self._waitresp()

    async def _discard(self, data=None):
        """Send hello prompt"""
        await self._send(b' ')

    async def _auth(self, data=None):
        """Send console ACN"""
        cmd = '\x10' + str(self._acn) + '\r\n'
        await self._send(cmd.encode('ascii', 'ignore'))
        await self._waitresp()

    async def _status(self, data=None):
        await self._send(b's')
        await self._waitresp()
        if self._sreq > _ERRCOUNT:
            _log.debug('No response to status request, closing device')
            await self._disconnect()

    async def _getvalues(self, data=None):
        await self._send(b'v')
        await self._waitresp()

    async def _setvalue(self, key, value):
        """Response from BLE to PC"""
        if self.cfg is None:
            self.cfg = {}
        if key == 'Firmware':
            self.cfg[key] = value
            self._equeue.put(('firmware', value))
        elif key == 'ACN':
            pass
        else:
            with suppress(Exception):
                v = int(value)
                self.cfg[key] = v
                self._equeue.put(('set', key, v))

    async def _message(self, data=None):
        """Return a message line to the UI"""
        if data:
            self._equeue.put(('message', data))
            self.cb()

    async def _down(self, data=None):
        if self.connected():
            await self._send(b'd')
            await self._waitresp()

    async def _up(self, data=None):
        if self.connected():
            await self._send(b'u')
            await self._waitresp()

    async def _send(self, buf):
        if self._portdev is not None:
            _log.debug('SEND: %r', buf)
            self._resp.clear()
            await self._portdev.write_gatt_char(_TX_UUID, buf, False)
        else:
            self._resp.set()

    def _splitstate(self, smsg):
        """Return the content of a status message"""
        state = 'Unknown/Error'
        error = False
        voltage = None
        clock = None
        cind = smsg.find('@')
        if cind > 0:
            with suppress(Exception):
                clock = int(smsg[cind + 1:])
            smsg = smsg[0:cind]
        sv = smsg.split(']')
        if sv[0]:
            state = sv[0].lstrip('[')
        for spart in sv[1:]:
            if '[Error' in spart:
                error = True
            elif 'Batt:' in spart:
                bv = spart.split()[-1].replace('V', '')
                with suppress(Exception):
                    voltage = float(bv)
        return state, error, voltage, clock

    async def _readresponse(self, line):
        """Process a line of response from the connected hoist"""
        if not self._running or not self.connected():
            return False
        docb = False
        wasconfigured = self.configured()
        if line.startswith('State:'):
            self._sreq = 0
            statmsg = line.split(': ', maxsplit=1)[1].strip()
            state, error, voltage, clock = self._splitstate(statmsg)
            self._equeue.put((
                'status',
                state,
                error,
                voltage,
                clock,
            ))
            docb = True
        elif ':' in line:
            self._equeue.put(('message', line))
            docb = True
            if line.startswith('Trigger:'):
                if 'reset' in line:
                    # re-auth required
                    self._cqueue.put_nowait(('_auth', None))
        elif '=' in line:
            lv = line.split(' = ', maxsplit=1)
            if len(lv) == 2:
                key = _subkey(lv[0].strip())
                if key != 'ACN':
                    await self._setvalue(key, lv[1].strip())
                    docb = True
                    if self.configured() and not wasconfigured:
                        self._equeue.put((
                            'connect',
                            None,
                        ))
                else:
                    _log.debug('ACN Updated')

            else:
                _log.debug('Ignored unexpected response %r', line)
        elif '?' in line:
            pass
        else:
            if line:
                self._equeue.put(('message', line))
                docb = True
        return docb

    async def _notify(self, characteristic, data):
        """Receive bytes from connected hoist"""
        self._portbuf.extend(data)
        self._resp.set()
        docb = False
        while b'\n' in self._portbuf:
            idx = self._portbuf.index(b'\n')
            _log.debug('RECV: %r', self._portbuf[0:idx + 1])
            l = self._portbuf[0:idx + 1].decode('ascii', 'ignore').strip()
            del self._portbuf[0:idx + 1]
            docb = await self._readresponse(l)
        if docb:
            self.cb()

    def _ble_disconnect_cb(self, client):
        """Handle Bluetooth client disconnect event"""
        if not self.inproc():
            _log.debug('Unexpected client disconnect')
            self.flush()  # clear any pending requests
            self._resp.set()  # terminate a pending read request
            self._cqueue.put_nowait(('_disconnect', None))

    async def _connect(self):
        """Connect to hoist and subscribe RX notifications"""
        if self._portdev is not None:
            _log.debug('Already connected')
            return True
        if self.portdev is not None:
            self._portinproc = True
            self._resp.set()
            self._startscan.clear()
            self._stopscan.set()
            self._portdev = BleakClient(
                self.portdev, disconnected_callback=self._ble_disconnect_cb)
            await self._portdev.connect()
            if self._portdev.is_connected:
                await self._portdev.start_notify(_RX_UUID, self._notify)
                self._portinproc = False
        return self._portdev is not None

    async def _disconnect(self, data=None):
        """Disconnect connected hoist"""
        if self._portdev is not None:
            self._closeinproc = True
            self.cfg = None
            self._equeue.put((
                'disconnect',
                None,
            ))
            self.cb()
            await asyncio.sleep(0)
            if self._portdev.is_connected:
                await self._doclose()
            self._portdev = None
            self._portbuf.clear()
        else:
            _log.debug('Client not connected')
        self._closeinproc = False
        self._portinproc = False

    async def _getblecname(self, data=None):
        """Fetch BLE cname from connected hoist"""
        cname = await self._portdev.read_gatt_char(_CNAME_UUID)
        cl = len(cname)
        if cl > _BLE_CNAMELEN:
            cname = cname[0:_BLE_CNAMELEN]
        cstr = cname.decode('utf-8', 'replace').rstrip('\x00')
        _log.debug('Read CNAME = %r (%s)', cstr, cname.hex())
        self._equeue.put(('cname', cstr))
        self.cb()

    async def _getblefwver(self, data=None):
        """Fetch BLE firmware version from connected hoist"""
        fwver = await self._portdev.read_gatt_char(_FWVER_UUID)
        self._equeue.put(('fwver', fwver.decode('utf-8', 'replace')))
        self.cb()

    async def _port(self, port):
        """Blocking close, followed by blocking open"""
        if port is not None:
            # re-connect will be required
            self._portinproc = True
        # Empty any pending commands from the the queue
        self.flush()
        if self.connected():
            await self._disconnect()
            await asyncio.sleep(0)
        self.portdev = port
        if port is not None:
            conn = await self._connect()
            if conn:
                self.cfg = {}
                self._cqueue.put_nowait(('_getblecname', None))
                self._cqueue.put_nowait(('_getblefwver', None))
                self._cqueue.put_nowait(('_discard', None))
                self._cqueue.put_nowait(('_auth', None))
                self._cqueue.put_nowait(('_getvalues', None))
                self._cqueue.put_nowait(('_status', None))
                self._equeue.put((
                    'connect',
                    None,
                ))
                self.cb()
            else:
                _log.debug('Unable to connect')
        else:
            _log.debug('Re-start scanner')
            self._stopscan.clear()
            self._startscan.set()

    async def _exit(self, data=None):
        self._running = False
        self.flush()
        # ensure scanner terminates
        self._stopscan.set()
        self._startscan.set()
        await self._disconnect()
        self._cqueue.put_nowait(None)

    async def _doclose(self):
        """Close bleak client ignoring exceptions"""
        try:
            self._resp.set()  # terminate a pending read request
            await self._portdev.disconnect()
        except Exception as e:
            _log.debug('%s closing client: %s', e.__class__.__name__, e)

    async def _proccmd(self, cmd):
        """Process a command tuple"""
        try:
            method = getattr(self, cmd[0], None)
            if method is not None:
                _log.debug('BLE command: %r', cmd)
                await method(*cmd[1:])
            else:
                _log.error('Unknown BLE command: %r', cmd)
        except EOFError:
            _log.debug('EOF Error waiting on method %s', cmd[1])
        except Exception as e:
            await self._message('Bluetooth error')
            _log.warning('%s: %s', e.__class__.__name__, e)
            self.setport(None)

    def _defcallback(self, evt=None):
        pass


class HHConfig:
    """TK Hay Hoist BLE utility"""

    def check_cname(self, newval, op):
        """Validate text entry for CNAME"""
        ret = False
        if newval:
            try:
                enctxt = newval.encode('utf-8', 'replace')
                if len(enctxt) > _BLE_CNAMELEN:
                    ret = False
                else:
                    ret = True
            except Exception:
                pass
        else:
            ret = True
        return ret

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

    def check_pin(self, newval, op):
        """Verify text entry for PIN"""
        ret = False
        if newval:
            try:
                v = int(newval)
                if v >= 0 and v <= _BLE_PINMAX:
                    ret = True
            except Exception:
                pass
            if not ret:
                self.logvar.set('Invalid entry')
        else:
            ret = True
        return ret

    def connect(self, data=None):
        """Handle connection event"""
        self.devval = {}
        if self.devio.configured():
            # after values received from connected hoist
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
            self.enable_ctrls()
            self.uiupdate()
        elif self.devio.connected():
            # after Bluetooth client connection
            self.logvar.set('Reading hoist configuration...')

    def enable_ctrls(self):
        """Enable control buttons"""
        self.dbut.state(['!disabled'])
        self.ubut.state(['!disabled'])
        self.lbut.state(['!disabled'])
        self.sbut.state(['!disabled'])

    def disable_ctrls(self):
        """Disable control buttons"""
        self.dbut.state(['disabled'])
        self.ubut.state(['disabled'])
        self.lbut.state(['disabled'])
        self.sbut.state(['disabled'])

    def disconnect(self):
        """Handle disconnection event"""
        if not self.devio.connected() or self.devio.inproc():
            if self.fwval.get():
                self.logvar.set('Hoist disconnected')
            self.statvar.set('[Not Connected]')
            self.devval = {}
            for k in _CFGKEYS:
                self.devval[k] = None
            self.fwval.set('')
            self.blefwval.set('')
            self.disable_ctrls()
            self.p1but.state(['disabled'])
            self.p2but.state(['disabled'])

    def update_device(self, bledevice, cname):
        """Update the ioports list with discovered hoists"""
        devaddr = bledevice.address
        self._iodevs[devaddr] = bledevice
        dochange = False
        for idx, ioport in enumerate(self._ioports):
            if ioport == devaddr:
                if self._ionames[idx] != cname:
                    self._ionames[idx] = cname
                    dochange = True
                break
        else:
            self._ionames.append(cname)
            self._ioports.append(devaddr)
            dochange = True

        if dochange:
            self.logvar.set('Found hoist %s' % (cname, ))
            oldport = None
            selid = self.portsel.current()
            if selid >= 0 and selid < len(self._ioports):
                oldport = self._ioports[selid]
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

    def receivestatus(self, newstate, newerror, voltage, clock):
        """Receive status info from connected hoist"""
        sv = [newstate]
        if voltage is not None:
            sv.append('%0.1fV' % (voltage, ))
            if voltage < _CHARGEDVOLTS:
                sv.append('\U0001faab')
                if voltage < _LOWVOLTS:
                    # force error flag
                    newerror = True
            else:
                sv.append('\U0001f50b')
        if newerror:
            sv.append('\u26a0\ufe0f')
        self.statvar.set(' '.join(sv))
        docheck = False
        if newstate != self.curstate:
            _log.debug('Hoist status change %r -> %r', self.curstate, newstate)
            self.curstate = newstate
            docheck = True
        if newerror != self.curerror:
            _log.debug('Hoist error flag %r -> %r', self.curerror, newerror)
            self.curerror = newerror
            docheck = True

        if docheck:
            # update P1/P2 set buttons
            if not self.curerror and self.curstate == 'AT H':
                if clock is not None:
                    self.p1but.state(['!disabled'])
                    self.p2but.state(['!disabled'])
                if self.mstate is not None:
                    _log.debug('Measurement error, reset')
                    self.enableui()
                    self.mstate = None
                    self.uiupdate()
            elif self.mstate is not None and 'P1' in self.mstate:
                self.p1but.state(['!disabled'])
                self.p2but.state(['disabled'])
                if self.mstate == 'P1READY':
                    self._startp1measure(clock)
                elif self.mstate in ('P1START', 'P1STOP'):
                    self._endp1measure(clock)
            elif self.mstate is not None and 'P2' in self.mstate:
                self.p1but.state(['disabled'])
                self.p2but.state(['!disabled'])
                if self.mstate == 'P2READY':
                    self._startp2measure(clock)
                elif self.mstate in ('P2START', 'P2STOP'):
                    self._endp2measure(clock)
            else:
                self.p1but.state(['disabled'])
                self.p2but.state(['disabled'])

    def disableui(self):
        """Disable UI elems for measure process"""
        for key, control in self.uictl.items():
            control.state(['disabled'])

    def enableui(self):
        """Enable UI elems for normal use"""
        for key, control in self.uictl.items():
            control.state(['!disabled'])

    def devevent(self, data=None):
        """Extract any pending events from the connected hoist"""
        while True:
            evt = self.devio.get_event()
            if evt is None:
                break

            _log.debug('Event: %r', evt)
            if evt[0] == 'status':
                self.receivestatus(evt[1], evt[2], evt[3], evt[4])
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
            elif evt[0] == 'fwver':
                self.blefwval.set('(BLE: v%s)' % (evt[1], ))
            elif evt[0] == 'cname':
                self.cname = evt[1]
                self.cnameval.set(self.cname)
            elif evt[0] == 'connect':
                self.connect()
            elif evt[0] == 'disconnect':
                self.disconnect()
            elif evt[0] == 'message':
                self.logvar.set(evt[1])
            elif evt[0] == 'scan':
                # ('scan', DEVICE, CNAME)
                self.update_device(evt[1], evt[2])
            else:
                _log.debug('Unknown event')

    def devcallback(self, data=None):
        """Generate event in tk main loop"""
        with suppress(Exception):
            self.window.event_generate('<<BleDevEvent>>', when='tail')

    def doreconnect(self):
        """Initiate a re-list and re-connect sequence"""
        self._devpollcnt = 0
        self.disconnect()
        oldport = None
        self.portchange(None)

    def devpoll(self):
        """Request update from connected hoist or re-init connection"""
        try:
            self._devpollcnt += 1
            if self.devio.connected():
                if self.devio.configured():
                    self._devpollcnt = 0
                    if self.mstate is None and 'MOVE' not in self.curstate:
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
            _log.debug('devpoll %s: %s', e.__class__.__name__, e)

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
            with suppress(Exception):
                t = max(round(float(nv) * 100), 1)
                if t > 0 and t < 65536:
                    v = t
                    fv = '%0.2f' % (v / 100.0, )
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
            with suppress(Exception):
                t = int(nv)
                if t >= 0 and t < 65536:
                    v = t
                    fv = '%d' % (v, )
        else:
            if k in self.devval and self.devval[k] is not None:
                v = self.devval[k]
                fv = '%d' % (v, )

        self.uval[k] = v
        if fv is not None and fv != nv:
            self.uival[k].set(fv)

    def _saveacn(self):
        """Write the cached acn config"""
        try:
            with open(_CFGFILE, 'w') as f:
                f.write('%d\r\n' % (self.acn, ))
        except Exception as e:
            _log.debug('%s saving cfg: %s', e.__class__.__name__, e)

    def xferacn(self):
        """Check for an updated console ACN"""
        if self.acnenabled:
            newacn = self.acn
            with suppress(Exception):
                pv = self.acnval.get()
                if pv and pv.isdigit():
                    newacn = int(pv)
                else:
                    newacn = 0
            if newacn != self.acn:
                if newacn == 0:
                    self.acnval.set('')
                self.acn = newacn
                self._saveacn()
                self.devio.updateacn(self.acn)

    def hp1update(self, data=None):
        """Process a change in the H-P1 time"""
        if 'H-P1' in self.uval and 'P1-P2' in self.uval:
            oldp1 = self.uval['H-P1']
            oldp2 = self.uval['P1-P2']
            if oldp1 is not None and oldp2 is not None:
                self.xfertimeval('H-P1')
                newp1 = self.uval['H-P1']
                if newp1 != oldp1:
                    diff = newp1 - oldp1
                    newp2 = max(0, min(oldp2 - diff, 12000))
                    fv = '%0.2f' % (newp2 / 100.0, )
                    self.uival['P1-P2'].set(fv)
        self.uiupdate()

    def bleupdate(self, data=None):
        """Send updated BLE config to connected hoist"""
        _log.debug('bleupdate')
        # if connected, update device
        if self.devio.connected():
            pv = self.pinval.get()
            if pv and pv.isdigit():
                newpin = int(pv)
                if newpin != self.lastpin:
                    self.devio.setpin(newpin)
                    self.lastpin = newpin
                    _log.debug('Update BLE PIN')
            cname = self.cnameval.get()
            if cname and cname != self.cname:
                cv = cname.encode('utf-8')
                self.devio.setcname(cv)
                self.cname = cname
                _log.debug('Update BLE CNAME')

    def uiupdate(self, data=None):
        """Check for required updates and send to connected hoist"""
        _log.debug('Update UI')
        for k in _TIMEKEYS:
            self.xfertimeval(k)
        for k in _INTKEYS:
            self.xferintval(k)
        self.xferacn()

        if self.devio.connected():
            cfg = {}
            for k in self.devval:
                if self.enabled[k]:
                    if k in self.uval and self.uval[k] is not None:
                        if self.uval[k] != self.devval[k]:
                            cfg[k] = self.uval[k]
                else:
                    _log.debug('Config key %s disabled', k)
            if cfg:
                _log.debug('Sending %d updated values to hoist', len(cfg))
                self.logvar.set('Updating hoist...')
                self.devio.update(cfg)

    def portchange(self, data):
        """Handle change of selected hoist"""
        selid = self.portsel.current()
        if selid is not None:
            if self._ioports and selid >= 0 and selid < len(self._ioports):
                self.clearall()
                self.enableui()
                if self._ioports[selid] is None:
                    if self.devio.connected():
                        _log.debug('Disconnect')
                        self.devio.setport(None)
                else:
                    # force reconnect to specified port
                    self._devpollcnt = 0
                    dev = self._ioports[selid]
                    if dev in self._iodevs:
                        dev = self._iodevs[dev]
                    self.devio.setport(dev)
        self.portsel.selection_clear()

    def triggerdown(self, data=None):
        """Request down trigger"""
        self.devio.down()

    def triggerup(self, data=None):
        """Request up trigger"""
        self.devio.up()

    def loadvalues(self, cfg):
        """Load configuration from cfg and update as required"""
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
        """Choose file and load values, update hoist if connected"""
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

    def clearall(self):
        """Clear entries to initial conditions"""
        self.fwval.set('')
        self.blefwval.set('')
        self.pinval.set('')
        self.cnameval.set('')
        self.lastpin = None
        self.cname = None
        self.curstate = None
        self.curerror = None
        self.mstate = None

        for k in _CFGKEYS:
            self.devval[k] = None
            self.uval[k] = None
            self.enabled[k] = True
            self.uival[k].set('')

    def _overridetime(self, k, v):
        """Override UI with an updated value"""
        if k not in self.uival:
            _log.debug('Unable to override, key %s not in ui')
            return
        self.uval[k] = v
        fv = None
        with suppress(Exception):
            if v > 0 and v < 65536:
                fv = '%0.2f' % (v / 100.0, )
        if fv is not None:
            self.uival[k].set(fv)
        else:
            self.uival[k].set('')

    def _beginp2measure(self):
        """Begin P2 measurement"""
        self.mstate = 'P2READY'
        self.disableui()
        self.disable_ctrls()
        # save old P1
        self.oldp1 = self.uval['H-P1']
        self.devio.update({'H-P1': self.uval['H']})
        self.devio.down()  # trigger change of state
        self.devio.message('Select "Set P2" again at desired height')
        _log.debug('P2 Measure %s', self.mstate)

    def _beginp1measure(self):
        """Begin P1 measurement"""
        self.mstate = 'P1READY'
        self.disableui()
        self.disable_ctrls()
        # save old P1
        self.oldp1 = self.uval['H-P1']
        self.devio.update({'H-P1': self.uval['H']})
        self.devio.down()  # trigger change of state
        self.devio.message('Select "Set P1" again at desired height')
        _log.debug('P1 Measure %s', self.mstate)

    def _startp1measure(self, clock):
        self.mstate = 'P1START'
        self.measurestart = clock
        _log.debug('P1 Measure %s: %r', self.mstate, self.measurestart)

    def _startp2measure(self, clock):
        self.mstate = 'P2START'
        self.measurestart = clock
        _log.debug('P2 Measure %s: %r', self.mstate, self.measurestart)

    def _stopp1measure(self):
        self.mstate = 'P1STOP'
        self.devio.up()  # trigger a change of state
        _log.debug('P1 Measure %s', self.mstate)

    def _stopp2measure(self):
        self.mstate = 'P2STOP'
        self.devio.up()  # trigger a change of state
        _log.debug('P2 Measure %s', self.mstate)

    def _endp1measure(self, clock):
        self.mstate = 'P1END'
        if self.measurestart is not None:
            elap = (clock - self.measurestart) & 0xffff
            _log.debug('End P1 measure at %d: dt = %d', clock, elap)
            oldp2 = self.uval['P1-P2']
            oldtot = self.oldp1 + oldp2
            # set P1
            self._overridetime('H-P1', elap)
            np2 = max(1, oldtot - elap)
            self._overridetime('P1-P2', np2)
            self.uiupdate()
            self.devio.message('P1 set OK')
        self.enable_ctrls()
        self.p1but.state(['disabled'])
        self.p2but.state(['disabled'])
        self.enableui()
        self.mstate = None

    def _endp2measure(self, clock):
        self.mstate = 'P2END'
        if self.measurestart is not None:
            result = 'Error'
            elap = (clock - self.measurestart) & 0xffff
            _log.debug('End P2 measure at %d: dt = %d', clock, elap)
            p2tot = elap
            # restore H-P1
            self._overridetime('H-P1', self.oldp1)
            if p2tot > self.oldp1:
                np2 = p2tot - self.oldp1
                self._overridetime('P1-P2', np2)
                _log.debug('New P2 set to: %d', np2)
                result = 'P2 set OK'
            else:
                _log.debug('P2 Measure invalid')
                result = 'Invalid P2 measure ignored'
            self.uiupdate()
            self.devio.message(result)
        self.enable_ctrls()
        self.p1but.state(['disabled'])
        self.p2but.state(['disabled'])
        self.enableui()
        self.mstate = None

    def measurep1(self):
        """P1 measurement trigger"""
        _log.debug('P1 measurement button press')
        if self.mstate is None:
            if self.curstate == 'AT H' and not self.curerror:
                _log.debug('P1 Measure: Request begin')
                self._beginp1measure()
            else:
                _log.debug('P1 Measure: Unable to start measurement')
        elif self.mstate == 'P1START':
            _log.debug('P1 Measure: Request stop')
            self._stopp1measure()
        else:
            _log.debug('P1 Measure: unexpected state: %s', self.mstate)

    def measurep2(self):
        """P2 measurement trigger"""
        _log.debug('P2 measurement button press')
        if self.mstate is None:
            if self.curstate == 'AT H' and not self.curerror:
                _log.debug('P2 Measure: Request begin')
                self._beginp2measure()
            else:
                _log.debug('P2 Measure: Unable to start measurement')
        elif self.mstate == 'P2START':
            _log.debug('P2 Measure: Request stop')
            self._stopp2measure()
        else:
            _log.debug('P2 Measure: unexpected state: %s', self.mstate)

    def __init__(self, window=None, devio=None):
        self.window = None
        self.acn = 0
        self.curstate = None
        self.curerror = None
        self.mstate = None
        self.measurestart = None
        self.oldp1 = None
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
        self._iodevs = {}
        self._ioports = [None]
        self._ionames = ['-- Select Hoist --']
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
        check_pin_wrapper = (window.register(self.check_pin), '%P', '%V')
        check_cname_wrapper = (window.register(self.check_cname), '%P', '%V')

        # ACN entry
        self.acnenabled = False
        #self.acnval, self.acnentry = _mkopt(frame, "ACN:", "", row,
        #check_int_wrapper, self.uiupdate,
        #self.setHelp, _HELP_ACN)
        #if self.acn:  # is nonzero
        #self.acnval.set(str(self.acn))
        #row += 1

        # device values
        self.enabled = {}
        self.devval = {}
        self.uval = {}
        for k in _CFGKEYS:
            self.devval[k] = None
            self.uval[k] = None
            self.enabled[k] = True

        # config options
        self.uictl = {}
        self.uival = {}
        self.uival['H-P1'], self.uictl['H-P1'] = _mkopt(
            frame, "H-P1:", "seconds", row, check_cent_wrapper, self.hp1update,
            self.setHelp, _HELP_HP1, 'H-P1')
        self.p1but = ttk.Button(frame, text='Set P1', command=self.measurep1)
        self.p1but.grid(column=3, row=row, sticky=(
            E,
            W,
        ))
        self.p1but.state(['disabled'])
        self.p1but.bind('<Enter>',
                        lambda event, text=_HELP_SP1: self.setHelp(text),
                        add='+')
        row += 1
        self.uival['P1-P2'], self.uictl['P1-P2'] = _mkopt(
            frame, "P1-P2:", "seconds", row, check_cent_wrapper, self.uiupdate,
            self.setHelp, _HELP_P1P2, 'P1-P2')
        self.p2but = ttk.Button(frame, text='Set P2', command=self.measurep2)
        self.p2but.grid(column=3, row=row, sticky=(
            E,
            W,
        ))
        self.p2but.state(['disabled'])
        self.p2but.bind('<Enter>',
                        lambda event, text=_HELP_SP2: self.setHelp(text),
                        add='+')
        row += 1
        self.uival['Man'], self.uictl['Man'] = _mkopt(frame, "Adjust:",
                                                      "seconds", row,
                                                      check_cent_wrapper,
                                                      self.uiupdate,
                                                      self.setHelp, _HELP_MAN)
        row += 1
        self.uival['H'], self.uictl['H'] = _mkopt(frame, "Home:", "seconds",
                                                  row, check_cent_wrapper,
                                                  self.uiupdate, self.setHelp,
                                                  _HELP_HOME)
        row += 1
        self.uival['H-Retry'], self.uictl['H-Retry'] = _mkopt(
            frame, "Home-Retry:", "seconds", row, check_cent_wrapper,
            self.uiupdate, self.setHelp, _HELP_HOMERETRY)
        row += 1
        self.uival['Feed'], self.uictl['Feed'] = _mkopt(
            frame, "Feed:", "minutes", row, check_int_wrapper, self.uiupdate,
            self.setHelp, _HELP_FEED)
        row += 1
        self.uival['Feeds/week'], self.uictl['Feeds/week'] = _mkopt(
            frame, "Feeds/week:", "(max 5000)", row, check_int_wrapper,
            self.uiupdate, self.setHelp, _HELP_FEEDWEEK)
        row += 1

        # BLE Pin
        self.lastpin = None
        self.pinval, self.pinentry = _mkopt(frame, "Pairing PIN:", "", row,
                                            check_pin_wrapper, self.bleupdate,
                                            self.setHelp, _HELP_PIN)
        self.pinentry.bind('<Return>', self.bleupdate)
        row += 1

        # BLE CNAME
        self.cname = None
        self.cnameval, self.cnameentry = _mkopt(frame, "Location:", "", row,
                                                check_cname_wrapper,
                                                self.bleupdate, self.setHelp,
                                                _HELP_LOC)
        self.cnameentry.bind('<Return>', self.bleupdate)
        row += 1

        # firmware version label
        ttk.Label(frame, text='Firmware:').grid(column=0,
                                                row=row,
                                                sticky=(E, ))
        self.fwval = StringVar()
        fwlbl = ttk.Label(frame, textvariable=self.fwval)
        fwlbl.grid(column=1, row=row, sticky=(W, ))
        fwlbl.bind('<Enter>',
                   lambda event, text=_HELP_FIRMWARE: self.setHelp(text),
                   add='+')
        self.blefwval = StringVar()
        blefwlbl = ttk.Label(frame, textvariable=self.blefwval)
        blefwlbl.grid(column=2, row=row, sticky=(W, ), columnspan=2)
        blefwlbl.bind('<Enter>',
                      lambda event, text=_HELP_FIRMWARE: self.setHelp(text),
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
        self.lbut = ttk.Button(aframe, text='Load', command=self.loadfile)
        self.lbut.grid(column=2, row=0, sticky=(
            E,
            W,
        ))
        self.lbut.state(['disabled'])
        self.lbut.bind('<Enter>',
                       lambda event, text=_HELP_LOAD: self.setHelp(text),
                       add='+')
        self.sbut = ttk.Button(aframe, text='Save', command=self.savefile)
        self.sbut.grid(column=3, row=0, sticky=(
            E,
            W,
        ))
        self.sbut.state(['disabled'])
        self.sbut.bind('<Enter>',
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
        window.bind('<<BleDevEvent>>', self.devevent)
        self.window = window
        self.portsel.focus_set()

        # start device polling
        self.devpoll()


def main():
    logging.basicConfig()
    if len(sys.argv) > 1 and '-v' in sys.argv[1:]:
        _log.setLevel(logging.DEBUG)
        _log.debug('Enabled debug logging')
    sio = BleConsole()
    try:
        sio.start()
        win = Tk()
        app = HHConfig(window=win, devio=sio)
        win.mainloop()
    finally:
        sio.exit()
    return 0


_LOGODATA = b64decode(b'\
iVBORw0KGgoAAAANSUhEUgAAAZAAAACQBAMAAADU5iBLAAAAMFBMVEWmViOvZTfjcSa6e1XD\
jWzpjFPrm2rRpo/wsInZtqHwwKLnzb712cTx4dfw8PD///9GoVldAAAACXBIWXMAAAsTAAAL\
EwEAmpwYAAAH6UlEQVR42u2azWsbVxDAn1iBEULWFgd6KKkgkLuCDjmEVrrnsGCQ6T8Q4aOK\
CyKExLcgfNKh0EMougbhgiGFHEyre5BBkEMPiSIHeukhkoUNQojV68y8tx9arW2cxLubMA8s\
b/bDmt+b79kI+ZUswSAMwiAMwiAMwiAMwiAMwiAMwiAMwiAMwiAMwiBJAXnZaDyS8p9G47GU\
v+HxtOGsLp7G9TveaKvjh0P8B16g+3E9GsOZufvYEzlzj9vRgdSFMOgzI6UpRFYeC2dZ8kAf\
fQuizvVx6gk8hRekLOpTRlfKqftYTk7c43J0ICBSikRKwxWUIgwEKefu+XYQBC/HDnJMIpmo\
FxsOC+EgILwHklkBgcuxg+CXDhf4pSSqdQ7Iug9EjFdACvGDnMHXdUnI4Yy2NhxkzQ+yuwKS\
jR8Epd/FD9FFpmEQJFUqobwGgWyUSko8F2St0dghzthB0DGsM9rnU5JOOY0bCSAGLCqe4cl/\
4VfeA8nDXRW8a0qa8plr5AkR9422ED+NMBA6NdQgC9rzJZCWo5F4QUCawgk57AmJHQIy8YFg\
gFsFySQABHLhep8CU58iK4IcHh7+5QM58YOsaGRuYlBDkPvwnAPyTP+J6EBAplxLpOATj6Tj\
7GkfyIHPR+bLPrKSR4YahAJEpCCgh2xdpEEbLcwHISD/mU7UsuSitRy1VjJ7fCDwrZmKWCuK\
tTpteQDEFdWXR9pBkJtJAIHQCxTAkq6Qu4aDXJLZuwkAgWSYNtG6jCIKdA7IJbVWLgEgkBEN\
2HHwd5PibijIJdWvTojxgkhV9fWdrw6EX9WDDH0gN/39CIRfG3kSEH7VvpaPHTUEEqICkT6Q\
QgBEpZn4EyKWShCuJtqCgiAGxme0JgQp2/qmJZDThIC0yO5Plc+GlCinSgsqjxSVepZAJgkB\
Ie8gQUisFY3MPWdXmbAdAKk7PhIzCBnVeOa0D8e+tk9ldpO0oDQyUepxQYxS6Q5Fiakv5cTS\
j6geMUV9CW3pKkjLzSMW9WEheWQtCSBT4YxQMB8GQQwVlQratKSKYQfOyMIVPgEgc9pR2l4Z\
CjKlplyD1Ik3CNJOAogkOTEKp2SoadnCq34pNJQvnGvFB1LEL0dPSIeDUKbpapAzwl4GSQ+T\
AfKy0dh1xr/SN/tt47mHetLbtdUoF389unD2uxvP7JdfKzBI8kDenFOGDHSjM4wYZOebu+Ct\
O6VS6YkuhfMS29mKaDul/A3VLqWoMitAGQnhemoKY6iL+7aevVIFUMTzUr4W4l6kIO9Vr1RU\
Yrgglh8EBccMMsTPNQWCD3wfAtJSVbTtnI9y0ihSYwWS80BySyApVe63FQ6CzFQjtgJi69sn\
TlsQFQhIsoHVYlFsFEGwCk7cyxJTuQuytkOiVpzMbiEIGNrPYIDwONgk1mg2zeW70L38ohST\
rqsMG9n7EQMgCvCzewY7WaGxKFYtXRckD0XVLlVWBQLJnVJuz8Hmt+dC+K3UgMIgA3+rDD/W\
VIgIQSZKKARBoTyQsg8Ez9oijaYCIAaCVIDqzn25BFKhqfA6aAONs2tfc3sVfIeI7z+zHsi9\
wyGBZHwgcBF8IIPFIRaNL+h+S6rZipqcqMGSBdVxAe7JEcQ1e7sINLp5aDgynmm5XYcLkn2J\
lfuZyKHNI0hJgzizlaHboY1JU32RneOx6Ta/EYFMIKQWxd0KObsCSZmiuBy1TkTZTOH9kD8A\
xBTW61LJ8oMcoMYq8Dj4iQax4gBxwy9ppO6kgQM9lOsLqwgi98UNyisgJFwp+EEwZpBG4gfp\
ghx3sfYW4ngJpI2t4S4aW1/cJJCiC9JojJ0hcldqH8naMZjWOlgNgWw8ll7UmnogWfIHSDQm\
KAtKlIoCKb8uEogX/wxKm/l4nP3Ei1oqgmoQTBtO1GphBylUzgeQ9wiidr7sA6lTIsfwiz8q\
/HajzCMZJ48sg7Q8kL77nieHIDOhc09LWB6IrV4x4r0VSrDWDM0rMpCpMEY6sysQKFF+QJCJ\
B3JKA7hU6Q6YIFa/JoCcCOOZSZkdSpS2Cr7Q20IdJn7FkifyEsXWVZ8LQvuuXn46IOAv41OA\
OKORdgGE1P9lI6UVZelRNhDEVjSS6IZcBZFuHsljUXWsKl4CmThlfHYVhAZfsZTxON/5MQzk\
wF80ltGB0XsRZEaNFb3/CYK08bW701h9F22H+GfpvsTRzlUjzPwwvCS09fk3Ub+x4uEDgzAI\
gzAIgzAIgzAIgzAIgzAIgzAIgzAIgzAIgzAIgzAIgzAIgzAIgzAIg8QGshj0Xj1vNpv775IL\
Yr/t9XodlLLZfFqltdXc6w0XeB4v1KrVW761td3pHY0TCHLr49btarVWI/pmp9NLANrHgoSQ\
1Zqgqy8fxAUCw+zsg1UOPH8afRgMyFKX1uCqDvf2FRk6rRqa/7WCXHmhUGCfvQuwFoDwoLr6\
6Nbe0chZ8YP4mbZhn3uOfS5Ai686z58+2AxX/fYfI99KFIgvklQ3L7zhp72/R8srkSAXa21v\
/2i0ur4ckNtb2+hJo3OWSJA9benEVKtRbHL9prm33xuMLlniGqNRcG2eH7ZCreVKS1yHFXfO\
FSuYTo4Go8+0RLP5YPPzQWxt778bxbKE+vW2c164vqVqqhoaMGTsgZZz0Otglt30K+LT7ePT\
QUZL4ilPq2Kku0z1H7StxMkQAvIFLwZhEAZhEAZhEAb5mkD+B0WhZnUcgEfCAAAAAElFTkSu\
QmCC\
')

if __name__ == '__main__':
    sys.exit(main())
