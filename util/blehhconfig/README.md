# Hay Hoist Bluetooth Configuration Tool

![screenshot](blehhconfig.png "blehhconfig screenshot")

Configure Hay Hoist connected via a
[bleuart](https://github.com/ndf-zz/bleuart/)
Bluetooth to RS232 adapter.

## Usage

	blehhconfig [-v]

Launch blehhconfig utility, then select hoist from
devices list.

Current status is displayed on the top line. Use
"Down" and "Up" buttons to trigger the hoist. "Load"
and "Save" buttons read or write configuration
from/to a JSON text file.

Set P1 and Set P2 buttons measure time and update
a connected hoist accordingly.

## Installation

Install into a venv with pip:

	$ python -m venv hh
	$ ./hh/bin/pip install blehhconfig
	$ ./hh/bin/blehhconfig

