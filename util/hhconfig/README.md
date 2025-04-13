# Hay Hoist Configuration Tool

![screenshot](hhconfig.png "hhconfig screenshot")

## Usage

Launch hhconfig utility, enter device console pin
if applicable, attache console cable if applicable,
then select hoist from devices list.

Current status is displayed on the top line. Use
"Down" and "Up" buttons to trigger the hoist. "Load"
and "Save" buttons read or write configuration
from/to a JSON text file.

### Windows

Before launching the config tool in Windows,
Bluetooth settings and pairing will need to be
complete.

Use the following procedure:

   - Open Bluetooth devices, scroll down to "More Bluetooth options"
   - Select the option "Allow Bluetooth devices to find this PC", and OK
   - Select "Add Bluetooth or other device", and "Bluetooth"
   - for each of the hoists with a Bluetooth serial adapter, select
     the device and pair, enter passphrase and select done
   - Run hhconfig util


## Batch Programming

### RS232 connection

   - Open hhconfig utility, enter pin and attach a serial adapter
   - Read desired settings from a saved configuration file
   - For each unit to be updated:
     - Plug serial cable onto console port
     - Wait until status line reports "Device updated"
     - Disconnect serial cable
     - Wait until status line reports "Device disconnected"

### Bluetooth connection

   - Open hhconfig utility, enter pin and wait for Bluetooth
     devices to be discovered
   - Read desired settings from a saved configuration file
   - For each unit to be updated:
     - Select the Hoist device
     - Wait until status line reports "Device updated"

Note: Bluetooth connections may take up to 30 seconds to
complete. If an update fails, re-select the hoist device.

## Installation

Run python script directly:

	$ python hhconfig.py

Install into a venv with pip:

	$ python -m venv hh
	$ ./hh/bin/pip install hhconfig
	$ ./hh/bin/hhconfig

Windows systems without Python already installed, download
the self-contained binary (~9MB) and signature:

   - [hhconfig.zip](https://6-v.org/hh/hhconfig.zip) [zip 9M]
   - [hhconfig.zip.sig](https://6-v.org/hh/hhconfig.zip.sig)

Check signature with gpg (or equivalent) then unzip and run exe.
