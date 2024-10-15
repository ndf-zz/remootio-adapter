# Hay Hoist Configuration Tool

![screenshot](hhconfig.png "hhconfig screenshot")

## Usage

Connect serial adapter to computer, launch hhconfig
utility. Select comport if required, then attach serial
cable to hay hoist console port.

Current status is displayed on the top line. Use
"Down" and "Up" buttons to trigger the hoist. "Load"
and "Save" buttons read or write configuration
from/to a JSON text file.

## Batch Programming

Multiple units can be programmed using the following
steps:

   - Open hhconfig utility and attach a serial adapter
   - Read desired settings from a saved configuration file
   - For each unit to be updated:
     - Plug serial cable onto console port
     - Wait until status line reports "Device updated"
     - Disconnect serial cable
     - Wait until status line reports "Device disconnected"

## Installation

Run python script directly:

	$ python hhconfig.py

Install into a venv with pip:

	$ python -m venv hh
	$ ./hh/bin/pip install hhconfig
	$ ./hh/bin/hhconfig

Windows systems without Python already installed, download
the self-contained binary (~10MB) and signature:

   - [hhconfig.zip](https://6-v.org/hh/hhconfig.zip) [zip 9.9M]
   - [hhconfig.zip.sig](https://6-v.org/hh/hhconfig.zip.sig)

Check signature with gpg (or equivalent) then unzip and run exe.
