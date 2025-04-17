# Remootio Adapter "PLC" - Hay Hoist

Adapt a Remootio door opener remote to
a golf buggy motor controller using an
AVR m328pb for remote control of a hay hoist.

![PCB](pcb/remootio-adapter.png "PCB")


## Operation


### Manual Operation

On reception of "down" command, hoist is lowered to P1 height.
If no further commands are received, it will retract to the home
position after the configured feed time minutes have elapsed.

A further "down" command will lower the hoist to the P2 height.

Return to home position on reception of an "up" signal, or
after a programmable duration without input.

![State Machine](reference/remootio_adapter_state_diagram.svg "State Diagram")


### Scheduled Feeding

If a number of feeds per week is specified, the hoist will lower
from the home position to P1 after a randomly chosen interval,
roughly "feeds/week" times a week and provided there is enough
charge in the battery to retract.

The hoist will remain at P1 until feed time minutes have elapsed, 
then retract to the home position. Manual operation "down" or
"up" will cancel a pending automatic schedule.

To disable scheduled feeding, manually lower the hoist slightly
from the home position. To re-enable, return hoist to home
("open") position.


### Special Cases

If an error condition is flagged, the hoist will only allow
movement up and down small amounts determined by the "Man time"
setting. To correct an error state, clear the sensor
switch and then manually operate the hoist down slightly and
then up to the home position.

Errors and exceptions may be triggered by the following conditions:

   - Low Battery: Scheduled feeding is suppressed when battery
     voltage falls below 11.8V. In this state, the battery LED
     is illuminated, manual operation is still enabled.
   - Spurious Sensor: In the case of a spurious triggering of
     the home sensor, an error condition is flagged and the
     motor is stopped.
   - Not at Home: If the home sensor is prematurely
     triggered, the hoist will attempt to continue retraction
     after Home-Retry seconds.
   - Sensor Failure: If the home sensor fails "open", or if the
     state logic is out of sync, the hoist will not react to
     up (raise) commands. If the sensor fails "closed", and max
     H time has elapsed, the hoist will flag an error condition.
   - Safetime: If the hoist is left at position P2, between P1 and P2,
     or in the STOP state, it will attempt to retract automatically
     to the home position after about 30 minutes.
   - Disable Schedule: Scheduled feeding may be temporarily disabled
     by manually lowering the hoist slightly from the home position
     to state "STOP H-P1". To re-enable scheduled feeding, return
     hoist to home position.


### Serial Console

Connect RS-232 serial adapter to J4 (console)
and open a terminal at 19200 baud, 8n1.

Enter 'p' followed by pin number and enter to enable
console.

Triggers, state changes and errors will
be displayed.

Enter '?' to display available commands:

	Commands:
	        1       H-P1 (0.01s)
	        2       P1-P2 (0.01s)
	        m       Man (0.01s)
	        h       H (0.01s)
	        r       H-Retry (0.01s)
	        f       Feed (minutes)
	        n       Feeds/week (0=off)
	        v       Show values
	        s       Status
	        d       Lower
	        u       Raise

Configuration parameters are adjusted
by entering the command key followed by
an updated value and then enter.
Time values 1,2,m,h and r are set in units of 0.01s.
Feeding time f is in minutes.


## Connectors

Adapter | Connector | Description
--- | --- | ---
J1:1 |  | "S5" Auxiliary I/O (unused)
J1:2 |  | "GND"
J1:3 |  | "S6" Auxiliary I/O (unused)
J1:4 |  | "GND"
N/C | C3:B | Motor + (blue/black)
N/C | C3:C | Motor - (yellow/red)
J2:1 | C4:D | "+12V" Battery + (red)
J2:2 | C4:A | "0V" Battery - (black)
J3:1 |  | ICSP MISO
J3:2 |  | ICSP VCC
J3:3 |  | ICSP SCK
J3:4 |  | ICSP MOSI
J3:5 |  | ICSP RST
J3:6 |  | ICSP GND
J4:1 | C1:2 | "RxD" Console DCE Received Data (brown)
J4:2 | C1:3 | "TxD" Console DCE Transmitted Data (yellow)
J4:3 | C1:5 | "GND" Console DCE Common Ground (white)
J5:1 | C2:C | "Home" Home Limit Input (NC output green)
N/C | C2:B | Short to C2:D (green)
J5:2 | C2:A | "GND" Home Limit Ground (blue)
N/C | C2:D | Short to C2:B
J5:3 |  | "AUX" Encoder/Counter Input (unused)
J5:4 |  | "GND" Encoder/Counter Ground
J6:1 | M1:7 | "PWR" Controller power (pink)
J6:2 | M:6,20 | "GND" Controller ground (black)
J6:3 | M:3 | "Throttle" Controller speed (green)
J6:4 | M:12 | "FWD" Controller forward (white)
J6:5 | M:14 | "REV" Controller reverse (orange)
J6:6 | M:Rx | "Rx" Controller serial receive (blue)
J6:7 | M:Tx | "Tx" Controller serial transmit (green)
J6:8 | M:Gnd | "GND" Controller ground (black)


## Firmware

### Source Layout

	Main event loop:	src/main.c: 	main()
	State machine logic:	src/main.c:	update_state()
	Reset/initialisation:	src/system.c:	system_init()
	Serial console logic:	src/console.c:	read_input()
	SPM controller setting:	src/spmcheck.c	spm_check()


### Version Summaries

   - 25002: Version 2.1, ignore home trigger when at P1
   - 25001: Version 2
      - include Home Retry option & logic
      - add trivial plaintext 'passkey' to protect serial console
   - 24012: Version 1, cosmetic updates for GUI tool, October 2024
   - 24011: Version 0, initial release September 2024

## Build

Connect AVR ISP to programming header, program fuses, initialise
the random seed book, then build and upload firmware to MCU:

	$ make fuse
	$ make randbook
	$ make upload

Note: randbook will overwrite any stored configuration, so it should
only be run once when initialising a new unit. Uploading a new
firmware will not overwrite stored configuration.

On boot, the SPM controller will be updated if required. Updates are
reported to the console output:

	Info: Boot v24011
	SPM: Config updated
	Info: Boot v24011
	SPM: 23014810
	Trigger: reset
	State: [STOP] Batt: 0.0V
	Trigger: home
	[...]


## Build Requirements

   - GNU Make
   - gcc-avr
   - binutils-avr
   - avr-libc
   - avrdude
   - python3 (if controller config is edited)

On a Debian system, use make to install required packages:

	$ make requires


## Production Unit Assembly

   - [assembly/](assembly/ "Assembly instruction")


## Prototype Unit Reference

![Prototype](reference/remootio_adapter_prototype.jpg "Prototype")

   - [wiring diagram](reference/remootio_adapter_protoype_wiring.pdf)
   - [port-pins diagram](reference/remootio_adapter_prototype_portpins.pdf)
   - [schematic diagram](reference/remootio_adapter_prototype_schematic.pdf)

