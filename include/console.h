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
	event_status,		// Request for display of state
};

// Console event structure
struct console_event {
	uint8_t type;
	uint8_t key;
	uint16_t value;
};

// Poll for new console event
void console_read(struct console_event *event);

// Write string and decimal value to console
void console_showval(const char *message, uint16_t value);

// Output current machine state and voltage
void console_showstate(uint8_t state, uint8_t error, uint8_t vsense);

// Write null-terminated message to console
void console_write(const char *message);

// Initialise serial device and prepare buffers
void console_init(void);

#endif // CONSOLE_H
