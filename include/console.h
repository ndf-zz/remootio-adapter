// SPDX-License-Identifier: MIT

/*
 * Minimal event-based serial console
 */
#ifndef CONSOLE_H
#define CONSOLE_H

// Console event types
enum event_type {
	event_none,		// No new event
	event_error,		// Serial read error
	event_getvalue,		// Request for the value of a variable
	event_setvalue,		// Request to set the value of a variable
	event_values,		// Request values of all variables
	event_status,		// Request for display of state
	event_down,		// Request to lower
	event_up,		// Request to raise
	event_auth,		// PIN OK
};

// Console event structure
struct console_event {
	uint8_t type;
	uint8_t key;
	uint16_t value;
};

// Clear the read buffer
void console_flush(void);

// Poll for new console event
void console_read(struct console_event *event);

// Write string and decimal value to console
void console_showval(const char *message, uint16_t value);

// Output current machine state and voltage
void console_showstate(uint8_t state, uint8_t error, uint8_t vsense);

// Show buffer as hex values
void console_showhex(const char *message, uint8_t * buf, uint8_t len);

// Show ascii string with max length
void console_showascii(const char *message, uint8_t * buf, uint8_t len);

// Write null-terminated message to console
void console_write(const char *message);

// Initialise serial device and prepare buffers
void console_init(void);

#endif // CONSOLE_H
