# Remootio Adapter "PLC" - Hay Hoist

Adapt a Remootio door opener remote to a golf buggy
motor controller using an AVR m328p (Nano)
for remote control of a hay hoist.

![Prototype](reference/remootio_adapter_prototype.jpg "Prototype")


## Operation

### Manual Operation

On reception of "down" command, hoist is lowered to P1 height.
If no further commands are received, it will retract to the home
position after the configured feed time minutes have elapsed.

A further "down" command will lower the hoist to the P2 height.

Return to home position on reception of an "up" signal. On error
or low voltage, signal Remootio "closed"
via input 1.

Refer to
[state machine diagram](reference/remootio_adapter_state_diagram.pdf)
in reference folder.

### Scheduled Feeding

If a number of feeds per day is specified, the hoist will lower
from the home position to P1 after a randomly chosen interval,
roughly "feeds/day" times a day.

The hoist will remain at P1 until feed time minutes have elapsed, 
then retract to the home position. Manual operation "down" or
"up" will cancel a pending automatic schedule.

To disable scheduled feeding, manually lower the hoist slightly
from the home position. To re-enable, return hoist to home
position.


## Wiring

Connect Remootio and motor controller as indicated in
the [wiring diagram](reference/remootio_adapter_wiring_diagram.pdf).

## Configuration

Connect USB cable and open a serial terminal
9600, 8n1. Press "?" for help:

	Commands:
		1	H-P1 time (0.01s)
		2	P1-P2 time
		m	Man time
		h	H time
		f	Feed time (min)
		n	Feeds/day (0=off)
		t	Throttle (1-255)
		s	Status
		d	Lower
		u	Raise

Time values 1,2,m and h are set in units of 0.01s.
Feeding time is in minutes. Throttle
CV is roughly 5.0 * val / 255 Volts.


## Remootio Preparation

   - Select output configuration 4: "Output 1 to open, Output 2 to close"
   - Configure both "open" and "close" impulse length to 50ms.
   - Enable sensor add-on: Input 1, Flip logic

Application interface displays "open" (ready for use) when the
unit is operating normally, and displays "closed" (reduced function)
when there is a sensor error or low battery condition.

To clear an error state, lower pulley slightly, then raise until the
home state is reached.


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

## Prototype Layout

Refer to 
[port-pins diagram](reference/remootio_adapter_portpins.pdf)
and
[schematic diagram](reference/remootio_adapter_schematic.pdf)
in reference folder.


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

