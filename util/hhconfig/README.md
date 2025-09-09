# Hay Hoist Configuration Tool

![screenshot](hhconfig.png "hhconfig screenshot")

## Usage

Launch hhconfig utility, enter device console pin
if applicable, attach console cable if applicable,
then select hoist from devices list.

Current status is displayed on the top line. Use
"Down" and "Up" buttons to trigger the hoist. "Load"
and "Save" buttons read or write configuration
from/to a JSON text file.


## Batch Programming

   - Open hhconfig utility, enter pin and attach a serial adapter
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

