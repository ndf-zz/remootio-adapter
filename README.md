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

If a number of feeds per day is specified, the hoist will lower
from the home position to P1 after a randomly chosen interval,
roughly "feeds/day" times a day.

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

Connect RS-232 serial adapter to console port
and open a terminal at 9600 baud, 8n1.

Triggers, state changes and errors will
be displayed.

Enter '?' to display available commands:

	Commands:
	        1       H-P1 time (0.01s)
	        2       P1-P2 time
	        m       Man time
	        h       H time
	        f       Feed time (min)
	        n       Feeds/day (0=off)
	        t       Throttle (1-255)
	        v       Show current values
	        s       Status
	        d       Lower
	        u       Raise

Configuration parameters are adjusted
by entering the command key followed by
an updated value and then enter.
Time values 1,2,m and h are set in units of 0.01s.
Feeding time is in minutes. Throttle
CV is roughly 5.0 * val / 255 Volts.


## Connectors

Adapter | Connector | Description
--- | --- | ---
J1:1 |  | "S5" Auxiliary I/O
J1:2 |  | "GND" Auxiliary I/O
J1:3 |  | "S6" Auxiliary I/O
J1:4 |  | "GND" Auxiliary I/O
J2:1 | C4:1 | "+12V" Battery +
J2:2 | C4:2 | "0V" Battery -
J3:1 |  | ICSP MISO
J3:2 |  | ICSP VCC
J3:3 |  | ICSP SCK
J3:4 |  | ICSP MOSI
J3:5 |  | ICSP RST
J3:6 |  | ICSP GND
J4:1 | C1:2 | "RxD" Console DCE Received Data
J4:2 | C1:3 | "TxD" Console DCE Transmitted Data
J4:3 | C1:5 | "GND" Console DCE Common Ground
J5:1 | C2:1 | "Home" Home Limit Input (NC output)
J5:2 | C2:2 | "GND" Home Limit Ground
J5:3 | C2:3 | "AUX" Encoder/Counter Input (unused)
J5:4 | C2:4 | "GND" Encoder/Counter Ground
J6:1 | M1:7 | "PWR" Controller power
J6:2 | M1:6 | "GND" Controller ground
J6:3 | M2:3 | "Throttle" Controller speed
J6:4 | M1:12 | "FWD" Controller forward
J6:5 | M1:14 | "REV" Controller reverse
J6:6 | M3:Rx | "Rx" Controller serial receive
J6:7 | M3:Tx | "Tx" Controller serial transmit
J6:8 | M2:20 | "GND" Controller ground


## Remootio Preparation

Remove DC socket and screw terminal blocks,
then fit module to adapter board as indicated
on the silkscreen.

In the Remootio application:

   - Select output configuration 4: "Output 1 to open, Output 2 to close"
   - Configure both "open" and "close" impulse length to 50ms.
   - Enable sensor add-on: Input 1, Flip logic

Application interface displays "open" when the hay hoist is
retracted to the home position. The display will show "closed"
when the hoist has been lowered to the feeding position (P1).


## Motor Controller Preparation

Run the Kelly Controllers configuration program (v4.5)

### General Setting

   - Forward Switch: Enable
   - Foot Switch: Disable
   - Throttle Sensor Type: 0-5V
   - Throttle Effective Starting: 5%
   - Throttle Effective Ending: 95%
   - Max Motor Current: 30%
   - Max Battery Current: 50%
   - Start-up Delay: 0 sec
   - Control Mode: Balanced
   - Under voltage: 9V
   - Over Voltage: 30V
   - Throttle Up/Down Rate: 1 (Fast)
   - Power On High Pedal Disable: Disable
   - Releasing Brake High Pedal Disable: Disable
   - Motor Top Speed: 100%
   - Boost Function: Disable
   - Economy Function: Disable
   - Half Current in Reverse: Disable
   - ABS: Disable
   - 12V Output: Disable
   - Motor Top Speed in Reverse: 100%
   - Joysticker[sic] Throttle: Disable

### Regeneration Setting

   - Regeneration: Disable
   - Brake Switch: Disable
   - Releasing Throttle Starts Regen: Disable
   - Regen Current By Brake Switch On: 20% [unused]
   - Max Regen Current: 100% [unused]
   - Brake Sensor Type: No
   - Brake Sensor Starting Point: 20% [unused]
   - Brake Sensor Ending Point: 80% [unused]

### Sensor Setting

   - Motor Temperature Sensor: Disable
   - Controller Stop Output Temperature: 125C
   - Controller Resume Output 90C

### CAN Setting

[empty]

### Smooth Setting

   - Smooth: Disable

## Firmware layout

	Main event loop:	src/main.c: 	main()
	State machine logic:	src/main.c:	update_state()
	Reset/initialisation:	src/system.c:	system_init()
	Serial console logic:	src/console.c:	read_input()


## Build

Connect AVR ISP to programming header, program fuses, initialise
the random seed book, then build and upload firmware to MCU:

	$ make fuse
	$ make randbook
	$ make upload

Note: randbook will overwrite any stored configuration, so it should
only be run once when initialising a new unit. Uploading a new
firmware will not overwrite stored configuration.


## Build Requirements

   - GNU Make
   - gcc-avr
   - binutils-avr
   - avr-libc
   - avrdude

On a Debian system, use make to install required packages:

	$ make requires

## Prototype Unit Reference

![Prototype](reference/remootio_adapter_prototype.jpg "Prototype")

   - [wiring diagram](reference/remootio_adapter_protoype_wiring.pdf)
   - [port-pins diagram](reference/remootio_adapter_prototype_portpins.pdf)
   - [schematic diagram](reference/remootio_adapter_prototype_schematic.pdf)

