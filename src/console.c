// SPDX-License-Identifier: MIT

#include <stdint.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include "system.h"
#include "console.h"

#define BUFLEN 0x100
#define BUFMASK (BUFLEN-1)
#define RXWI GPIOR1
#define RXRI GPIOR2
#define IDLE_TIMEOUT	700U	// Disable console after 7s idle

static uint8_t rxbuf[BUFLEN];
static uint8_t txbuf[BUFLEN];
static volatile uint8_t TXRI;
static volatile uint8_t TXWI;
static volatile uint8_t rx_stall;
static uint8_t wrenabled = 1;
static uint8_t rdenabled = 0;
static uint8_t command;

static const char help[] = "\
\r\n\
Commands:\r\n\
\t1\tH-P1 (0.01s)\r\n\
\t2\tP1-P2 (0.01s)\r\n\
\tm\tMan (0.01s)\r\n\
\th\tH (0.01s)\r\n\
\tr\tH-Retry (0.01s)\r\n\
\tf\tFeed (minutes)\r\n\
\tn\tFeeds/week (0=off)\r\n\
\tv\tShow values\r\n\
\ts\tStatus\r\n\
\td\tLower\r\n\
\tu\tRaise\r\n\
\r\n";

ISR(USART_RX_vect)
{
	uint8_t status = UCSR0A;
	uint8_t tmp = UDR0;
	uint8_t look = (uint8_t) ((RXWI + 1) & BUFMASK);
	// stall input when output buf is full
	if (look != RXRI) {
		if (status & (_BV(FE0) | _BV(DOR0))) {
			rxbuf[look] = 0;
		} else {
			rxbuf[look] = tmp;
		}
		RXWI = look;
	}
}

ISR(USART_UDRE_vect)
{
	if (TXRI != TXWI) {
		uint8_t look = (uint8_t) ((TXRI + 1U) & BUFMASK);
		UDR0 = txbuf[look];
		TXRI = look;	// Release FIFO slot
	} else {
		UCSR0B &= (uint8_t) ~ _BV(UDRIE0);
		rx_stall = 0;
	}
}

// Set UDREIE to begin transfer
static void enable_transfer(void)
{
	UCSR0B |= _BV(UDRIE0);
}

// Write byte to tx buffer
static void write_serial(uint8_t ch)
{
	if (wrenabled) {
		uint8_t look = (uint8_t) ((TXWI + 1) & BUFMASK);
		if (look != TXRI) {
			txbuf[look] = ch;
			TXWI = look;
		} else {
			rx_stall = 1U;
			// drop output
		}
	}
}

// Write byte and then flag transfer
static void send_byte(uint8_t ch)
{
	write_serial(ch);
	enable_transfer();
}

// Write 16 bit word value as decimal integer
static void write_wordval(uint16_t value)
{
	uint8_t leading = 0;
	uint16_t divisor = 10000;
	while (divisor) {
		if (value >= divisor) {
			write_serial((uint8_t) (0x30 + value / divisor));
			value = value % divisor;
			leading = 1;
		} else if (leading) {
			write_serial(0x30);
		}
		divisor = divisor / 10;
		if (divisor == 1) {
			write_serial((uint8_t) (0x30 + value));
			break;
		}
	}
}

static void write_nibble(uint8_t nibble)
{
	if (nibble > 0x09) {
		nibble = (uint8_t) (nibble + 0x7);
	}
	write_serial((uint8_t) (0x30 + nibble));
}

// Write a single ascii character
static void write_ascii(uint8_t value)
{
	if (value >= 0x20 && value < 0x7f) {
		write_serial(value);
	} else {
		write_serial(0x3f);
	}
}

// Write a single byte to console as hexadecimal string
static void write_hexval(uint8_t value)
{
	write_nibble(value >> 4);
	write_nibble(value & 0xf);
}

// Copy string to write buffer
static void write_string(const char *message)
{
	while (*message) {
		write_serial((uint8_t) * message++);
	}
}

// Write null-terminated string to serial out
void console_write(const char *message)
{
	write_string(message);
	enable_transfer();
}

static void newline(void)
{
	console_write("\x0d\x0a");
}

// Read command byte
static uint8_t get_cmd(uint8_t ch)
{
	switch (ch) {
	case 0x10:
		return 0x10;
		break;
	case 0x68:
	case 0x48:
		console_write("H? ");
		return 0x68;
		break;
	case 0x70:
	case 0x50:
		console_write("P? ");
		return 0x70;
		break;
	case 0x72:
	case 0x52:
		console_write("H-Retry? ");
		return 0x72;
		break;
	case 0x31:
		console_write("H-P1? ");
		return 0x31;
		break;
	case 0x32:
		console_write("P1-P2? ");
		return 0x32;
		break;
	case 0x66:
	case 0x46:
		console_write("Feed min? ");
		return 0x66;
		break;
	case 0x6e:
	case 0x4e:
		console_write("Feeds/week? ");
		return 0x6e;
		break;
	case 0x6d:
	case 0x4d:
		console_write("Man? ");
		return 0x6d;
		break;
	case 0x3f:
		console_write(help);
		break;
	case 0x73:		// s : status
	case 0x53:
		return 0x73;
		break;
	case 0x76:		// v : get all values
	case 0x56:
		return 0x76;
		break;
	case 0x75:		// u : raise/up
	case 0x55:
		return 0x75;
		break;
	case 0x64:		// d : lower/down
	case 0x44:
		return 0x64;
		break;
	default:
		break;
	}
	return 0;
}

// Read next base 10 digit into val
static uint16_t read_val(uint8_t ch, uint16_t val)
{
	switch (ch) {
	case 0x30:
	case 0x31:
	case 0x32:
	case 0x33:
	case 0x34:
	case 0x35:
	case 0x36:
	case 0x37:
	case 0x38:
	case 0x39:
		if (val == 0xffff) {
			val = 0;
		}
		send_byte(ch);
		val = val * 10U + ch - 0x30;
		break;
	default:
		break;
	}
	return val;
}

// Read next input byte and update event as required
static void read_input(uint8_t ch, struct console_event *event)
{
	static uint16_t val = 0xffff;

	event->type = event_none;

	if (rdenabled) {
		if (command == 0) {
			command = get_cmd(ch);
			if (command == 0x73) {
				event->type = event_status;
				event->key = 0;
				event->value = 0;
				newline();
				command = 0;
			} else if (command == 0x76) {
				event->type = event_values;
				event->key = 0;
				event->value = 0;
				newline();
				command = 0;
			} else if (command == 0x75) {
				event->type = event_up;
				event->key = 0;
				event->value = 0;
				newline();
				command = 0;
			} else if (command == 0x64) {
				event->type = event_down;
				event->key = 0;
				event->value = 0;
				newline();
				command = 0;
			}
			val = 0xffff;
		} else {
			switch (ch) {
			case 0x1b:
			case 0x08:
				// escape
				newline();
				command = 0;
				break;
			case 0x20:
				break;
			case 0x0d:
			case 0x0a:
				if (val != 0xffff) {
					event->type = event_setvalue;
					event->key = command;
					event->value = val;
					newline();
				} else {
					event->type = event_getvalue;
					event->key = command;
					event->value = 0;
					newline();
				}
				command = 0;
				break;
			default:
				val = read_val(ch, val);
				break;
			}
		}
	} else {
		if (command == 0) {
			if (ch == 0x10) {
				command = 0x10;
			}
			val = 0xffff;
		} else {
			switch (ch) {
			case 0x0d:
			case 0x0a:
				// check auth key
				if (val == feed.pk) {
					newline();
					event->type = event_auth;
					event->key = 0;
					event->value = 0;
				}
				command = 0;
				break;
			default:
				val = read_val(ch, val);
				break;
			}
		}
	}
}

// Clear the input buffer
void console_flush(void)
{
	RXRI = RXWI;
}

// Fetch next event from console
void console_read(struct console_event *event)
{
	uint8_t look;
	uint8_t ch;
	static uint16_t count = 0;
	event->type = event_none;
	++count;
	if (count >= IDLE_TIMEOUT) {
		count = 0xfffe;
		if (rdenabled) {
			console_write("\r\nIdle Timeout\r\n");
		}
		command = 0;
		rdenabled = 0;
		wrenabled = 0;
	}
	while (RXRI != RXWI) {
		count = 0;
		look = (uint8_t) ((RXRI + 1U) & BUFMASK);
		ch = rxbuf[look];
		RXRI = look;	// Release FIFO slot
		read_input(ch, event);
		if (event->type == event_auth) {
			rdenabled = 1;
			wrenabled = 1;
			console_write("OK\r\n");
		} else {
			if (event->type) {
				break;
			}
		}
	}
}

static void show_voltage(uint8_t vsense)
{
	uint16_t scaled = (uint16_t) (vsense << 7U);
	uint16_t av = (uint8_t) ((scaled + 40U) / 80U);
	write_string(" Batt: ");
	if (av > 99U) {
		write_serial((uint8_t) (0x30 + av / 100));
		av = av % 100;
	}
	if (av > 9) {
		write_serial((uint8_t) (0x30 + av / 10));
		av = av % 10;
	} else {
		write_serial(0x30);
	}
	write_serial(0x2e);
	write_serial((uint8_t) (0x30 + av));
	write_string("V");
}

// Output current machine state and voltage
void console_showstate(uint8_t state, uint8_t error, uint8_t vsense)
{
	const char *smsg;
	write_string("State: ");
	switch (state) {
	case state_stop:
		smsg = "[STOP]";
		break;
	case state_stop_h_p1:
		smsg = "[STOP H-P1]";
		break;
	case state_stop_p1_p2:
		smsg = "[STOP P1-P2]";
		break;
	case state_at_h:
		smsg = "[AT H]";
		break;
	case state_at_p1:
		smsg = "[AT P1]";
		break;
	case state_at_p2:
		smsg = "[AT P2]";
		break;
	case state_move_h_p1:
		smsg = "[MOVE H-P1]";
		break;
	case state_move_p1_p2:
		smsg = "[MOVE P1-P2]";
		break;
	case state_move_h:
		smsg = "[MOVE -H]";
		break;
	case state_move_man:
		smsg = "[MOVE MAN]";
		break;
	case state_error:
	default:
		smsg = "[Unknown/Error]";
		break;
	}
	write_string(smsg);
	if (error) {
		write_string(" [Error]");
	}
	show_voltage(vsense);
	newline();
}

// Write string and decimal value to console
void console_showval(const char *message, uint16_t value)
{
	write_string(message);
	write_wordval(value);
	newline();
	enable_transfer();
}

// Show buffer as hex values
void console_showhex(const char *message, uint8_t * buf, uint8_t len)
{
	write_string(message);
	while (len) {
		write_hexval(*(buf++));
		--len;
	}
	newline();
	enable_transfer();
}

// Show ascii string with max length
void console_showascii(const char *message, uint8_t * buf, uint8_t len)
{
	write_string(message);
	uint8_t ch;
	while (len) {
		ch = *buf;
		if (ch) {
			write_ascii(*(buf++));
			--len;
		} else {
			break;
		}
	}
	newline();
	enable_transfer();
}

void console_init(void)
{
	// 19200,8n1 w/ interrupt receive & send
	UBRR0L = 12;
	UCSR0A |= _BV(U2X0);	// x2 clock
	UCSR0B = _BV(RXCIE0) | _BV(RXEN0) | _BV(TXEN0);
	UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);
	console_showval("Info: Boot v", sw_version);
}
