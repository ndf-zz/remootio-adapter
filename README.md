# Remootio Adapter "PLC"

Adapt a Remootio door opener remote to a golf buggy
motor controller using an AVR m328p (Nano)
with six switch inputs, 2 PWM CVs and 5 relay outputs.

![Prototype](reference/remootio_adapter_prototype.jpg "Prototype")


## Operation

On reception of "down" signal, lower payload to a pre-determined
height, then stop. From that position, lower to the ground or retract
to on reception of "down". Return to home position on reception
of an "up" signal. On error or low voltage, signal Remootio "closed"
via input 1.

Refer to
[state machine diagram](reference/remootio_adapter_state_diagram.pdf)
in reference folder.


## Wiring

Connect Remootio and motor controller as indicated in
the [wiring diagram](reference/remootio_adapter_wiring_diagram.pdf).

## Configuration

Connect usb cable and open a serial terminal
9600, 8n1. Press "?" for help:

	Commands:
	        1       H-P1 time (0.01s)
	        2       P1-P2 time
	        m       Man time
	        h       H time
	        b       Brake (1-255)
	        t       Throttle (1-255)
	        s       Show Status

Time values are set in units of 0.01s. Throttle and brake
CVs are roughly 5.0 * val / 255 Volts.


## Remootio Preparation

   - Configure both "open" and "close" impulse length to 50ms.
   - Select output configuration 4: "Output 1 to open, Output 2 to close"
   - Enable sensor add-on: Input 1, Flip logic

Application interface displays "open" (ready for use) when the
unit is operating normally, and displays "closed" (reduced function)
when there is a sensor error or low battery condition.

To clear an error state, lower pully slightly, then raise until the
home state is reached.


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

Connect AVR ISP to programming header, program fuses, then build
and upload firmware to MCU:

	$ make fuse
	$ make upload


## Build Requirements

   - GNU Make
   - gcc-avr
   - binutils-avr
   - avr-libc
   - avrdude

On a Debian system, use make to install required packages:

	$ make requires

