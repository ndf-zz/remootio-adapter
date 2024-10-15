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
                if self.uval[k] is not None:
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
        window.title('Hay Hoist')
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
        ttk.Label(frame, text="Hay Hoist").grid(column=0,
                                                row=0,
                                                columnspan=2,
                                                sticky=(
                                                    E,
                                                    W,
                                                ))
        self.statvar = StringVar(value='[Not Connected]')
        self.statlbl = ttk.Label(frame, textvariable=self.statvar)
        self.statlbl.grid(column=2, row=0, sticky=(E, ), columnspan=2)
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
