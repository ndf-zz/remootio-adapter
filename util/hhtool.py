#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""hhtool

Read/Write hay hoist config

"""

import sys
from serial import Serial
import json
import argparse
import logging

# Constants
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

_log = logging.getLogger('hhtool')


class hhconsole:
    """Hay Hoist Serial Console Wrapper"""

    def __init__(self, port=None):
        self._port = None
        self.port = port
        self.stat = None
        if self.port is None:
            self._getport()

    def _getport(self):
        devs = {}
        try:
            from serial.tools.list_ports import comports
            for port in comports():
                devs[port.device] = str(port)
        except Exception:
            pass

        for cp in sorted(devs):
            self.port = cp
            _log.debug('Automatically selected %s', devs[cp])
            break

        if self.port is None:
            raise RuntimeError('Unable to find comport, use option -p')

    def _subkey(self, key):
        if key in _KEYSUBS:
            key = _KEYSUBS[key]
        return key

    def _send(self, buf):
        _log.debug('SEND: %r', buf)
        return self._port.write(buf)

    def _recv(self, len):
        rb = self._port.read(len)
        if rb:
            _log.debug('RECV: %r', rb)
        return rb

    def _readstatus(self):
        rb = self._recv(_READLEN)
        ret = None
        if rb:
            m = rb.decode('ascii', 'ignore').strip()
            if m.startswith('State:'):
                ret = m.split(': ', maxsplit=1)[1].strip()
        return ret

    def getstatus(self):
        """Fetch current status from device"""
        self._recv(_READLEN)
        self._send(b's')
        return self._readstatus()

    def _readvalues(self):
        rb = self._recv(_READLEN)
        ret = None
        if rb:
            mv = rb.decode('ascii', 'ignore').strip().split('\n')
            if mv[0].startswith('Current Values:'):
                ret = {}
                for line in mv[1:]:
                    lv = line.split(' = ', maxsplit=1)
                    if len(lv) == 2:
                        k = self._subkey(lv[0].strip())
                        if k == 'Firmware':
                            v = lv[1].strip()
                            _log.debug('Firmware version = %s', lv[1].strip())
                            ret[k] = v
                        elif k in _CFGKEYS:
                            v = int(lv[1].strip())
                            ret[k] = v
                        else:
                            _log.debug('%s = %s', k, lv[1].strip())
                    else:
                        _log.debug('Ignored unexpected response %r', line)
            else:
                _log.debug('Unexpected value response %r', mv[0])
        return ret

    def showvalues(self, cfg=None):
        """Format values in cfg for display to screen"""
        if cfg is None:
            cfg = self.getvalues()
        if cfg is None:
            raise RuntimeError('Error reading configuration')
        ret = []
        for k in cfg:
            kv = self._subkey(k)
            if kv in (
                    'H-P1',
                    'P1-P2',
                    'Man',
                    'H',
            ):
                ret.append('%s = %0.2f seconds' % (
                    kv,
                    cfg[k] / 100,
                ))
            elif kv == 'Feed':
                ret.append('Feed = %d minutes' % (cfg[k], ))
            elif kv == 'Feeds/week':
                n = cfg[k]
                if n == 0:
                    n = 'Off'
                else:
                    n = str(n)
                ret.append('Feeds/week = %s' % (n, ))
            elif kv == 'Firmware':
                ret.append('Firmware = %s' % (cfg[k], ))
            else:
                ret.append('Unknown key %r = %s' % (kv, cfg[k]))
        return '\n'.join(ret)

    def getvalues(self):
        """Get current config values from device"""
        self._send(b'v')
        return self._readvalues()

    def _readvalue(self, key):
        rb = self._recv(_READLEN)
        ret = None
        if rb:
            mv = rb.decode('ascii', 'ignore').split(' = ', maxsplit=1)
            kv = self._subkey(mv[0].split('\n')[-1])
            vv = mv[1].split('\n')[0].strip()
            if kv == key:
                lv = int(vv)
                ret = lv
            else:
                _log.warning('Read value returned invalid key %r', kv)
        return ret

    def setvalue(self, key, value):
        """Set single value and confirm update on device"""
        cmd = _CFGKEYS[key] + str(value) + '\r\n'
        self._send(cmd.encode('ascii', 'ignore'))
        return value == self._readvalue(key)

    def setvalues(self, cfg):
        """Set and confirm cfg"""
        oldcfg = self.getvalues()
        if oldcfg is None:
            _log.error('Unable to fetch current config')
            return False

        ret = True
        for k in cfg:
            kv = self._subkey(k)
            if kv in _CFGKEYS:
                ov = None
                if kv not in oldcfg:
                    _log.warning('Option %r not set on device', kv)
                else:
                    ov = oldcfg[kv]
                if cfg[k] == oldcfg[kv]:
                    _log.debug('Option %r OK', kv)
                else:
                    _log.debug('Updating %r from %r to %r', kv, ov, cfg[k])
                    ret = self.setvalue(kv, cfg[k])
                    if not ret:
                        break
            else:
                _log.debug('Ignored unknown config key %r', kv)
        return ret

    def open(self):
        """Establish and check serial connection"""
        self._open()
        self.stat = self.getstatus()
        if self.stat is not None:
            _log.debug('Connected to hay hoist: %s', self.stat)
        else:
            _log.error('Error connecting to hay hoist')
            self.close()

        return self._port is not None

    def _open(self):
        if self._port is not None:
            _log.debug('Controller already open')
            return True

        _log.debug('Open serial port %s %d,8n1', self.port, _BAUDRATE)
        self._port = Serial(port=self.port,
                            baudrate=_BAUDRATE,
                            rtscts=False,
                            timeout=0.1)

    def close(self):
        """Close serial port and delete handle"""
        if self._port is not None:
            self._port.close()
            self._port = None
            _log.debug('Close serial port')


def main():
    logging.basicConfig()
    parser = argparse.ArgumentParser(prog='hhtool')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-s',
                       '--show',
                       action='store_true',
                       help='show current configuration')
    group.add_argument('-r',
                       '--read',
                       action='store_true',
                       help='read configuration from device')
    group.add_argument('-w',
                       '--write',
                       action='store_true',
                       help='write configuration to device')
    parser.add_argument('-v',
                        '--verbose',
                        action='store_true',
                        help='show debug log')
    parser.add_argument(
        '-p',
        dest='port',
        help='specify serial port',
    )
    parser.add_argument('file',
                        nargs='?',
                        help='JSON settings file',
                        default=None)
    args = parser.parse_args()
    if args.verbose:
        _log.setLevel(logging.DEBUG)
        _log.debug('Debug logs enabled')
    else:
        _log.setLevel(logging.WARNING)

    if args.file is None:
        _log.debug('No config file specified')
        if args.read or args.write:
            parser.print_usage()
            return -1

    try:
        h = hhconsole(args.port)
        if h.open():
            if args.read:
                cfg = h.getvalues()
                if cfg is not None:
                    with open(args.file, 'w') as f:
                        json.dump(cfg, f, indent=1)
                    _log.debug('Saved config to %s', args.file)
                else:
                    raise RuntimeError('Unable to read current config')
            elif args.write:
                cfg = None
                with open(args.file) as f:
                    cfg = json.load(f)
                if cfg is not None:
                    _log.debug('Loaded config from %s', args.file)
                    if h.setvalues(cfg):
                        _log.debug('Config updated')
                    else:
                        raise RuntimeError('Unable to update config')
                else:
                    raise RuntimeError('Unable to read config file')
            else:
                print(h.showvalues())
                print(h.stat)
    except Exception as e:
        _log.error('%s: %s', e.__class__.__name__, e)
        return -1

    return 0


if __name__ == '__main__':
    sys.exit(main())
