// SPDX-License-Identifier: MIT

/*
 * AVR m328p (Nano) Serial "PLC"
 */
#include <stdint.h>
#include <avr/sleep.h>
#include "system.h"
#include "console.h"

struct state_machine feed;

static void flag_error(void)
{
	PORTD &= (uint8_t) ~ _BV(R5);
	PORTB &= (uint8_t) ~ _BV(LED);
	feed.error = 1U;
}

static void clear_error(void)
{
	PORTD |= _BV(R5);
	PORTB |= _BV(LED);
	feed.error = 0;
}

static void motor_start(void)
{
	OCR2B = 0;		// lower brake CV
	PORTD &= (uint8_t) ~ (_BV(R4));	// disable brake sw
	PORTD |= _BV(R1);	// connect throttle
	OCR2A = feed.throttle & 0xff;	// raise throttle CV
}

static void motor_stop(void)
{
	OCR2A = 0;		// lower throttle CV
	PORTD &= (uint8_t) ~ (_BV(R1));	// disable throttle sw
	PORTD |= _BV(R4);	// connect brake sw
	OCR2B = feed.brake & 0xff;	// raise brake CV
}

static void motor_reverse(void)
{
	PORTD &= (uint8_t) ~ (_BV(R2));	// disable R2 FWD
	PORTD |= _BV(R3);	// enable R3 REV
}

static void motor_forward(void)
{
	PORTD &= (uint8_t) ~ (_BV(R3));	// disable R3 REV
	PORTD |= _BV(R2);	// enable R2 FWD
}

static void stop_at(uint8_t newstate)
{
	motor_stop();
	feed.state = newstate;
}

static void stop_at_home(void)
{
	stop_at(state_at_h);
	clear_error();
}

static void move_up(uint8_t newstate)
{
	motor_reverse();
	motor_start();
	feed.state = newstate;
}

static void move_down(uint8_t newstate)
{
	motor_forward();
	motor_start();
	feed.state = newstate;
}

static void trigger_up(void)
{
	switch (feed.state) {
	case state_stop:
	case state_stop_h_p1:
	case state_stop_p1_p2:
	case state_at_p1:
	case state_at_p2:
		feed.h = 0;
		move_up(state_move_h);
		break;
	case state_move_h_p1:
		stop_at(state_stop_h_p1);
		break;
	case state_move_p1_p2:
		stop_at(state_stop_p1_p2);
		break;
	case state_move_h:
	case state_move_man:
		stop_at(state_stop);
		break;
	case state_at_h:
	default:
		break;
	}
}

static void trigger_down(void)
{
	switch (feed.state) {
	case state_stop:
		feed.man = 0;
		move_down(state_move_man);
		break;
	case state_stop_h_p1:
		move_down(state_move_h_p1);
		break;
	case state_stop_p1_p2:
		move_down(state_move_p1_p2);
		break;
	case state_at_h:
		feed.p1 = 0;
		move_down(state_move_h_p1);
		break;
	case state_at_p1:
		feed.p2 = 0;
		move_down(state_move_p1_p2);
		break;
	case state_at_p2:
		feed.man = 0;
		move_down(state_move_man);
		break;
	case state_move_h_p1:
		stop_at(state_stop_h_p1);
		break;
	case state_move_p1_p2:
		stop_at(state_stop_p1_p2);
		break;
	case state_move_h:
	case state_move_man:
		stop_at(state_stop);
		break;
	default:
		break;
	}
}

static void trigger_home(void)
{
	switch (feed.state) {
	case state_stop:
	case state_move_h:
		stop_at_home();
		break;
	case state_at_h:
	case state_move_h_p1:
		// possible noise problem
		break;
	default:
		// spurious home sense
		flag_error();
		break;
	}
}

static void read_triggers(void)
{
	uint8_t triggers = read_inputs();
	if (triggers & TRIGMASK) {
		if (triggers & TRIGGER_HOME) {
			// Transition to home will mask concurrent trigs
			trigger_home();
		} else {
			if (triggers & TRIGGER_DOWN) {
				trigger_down();
			}
			if (triggers & TRIGGER_UP) {
				// up cancels a concurrent down
				trigger_up();
			}
		}
	}
}

static void read_timers(void)
{
	uint16_t thresh;
	switch (feed.state) {
	case state_move_h_p1:
		feed.p1++;
		if (feed.p1 > feed.p1_timeout) {
			stop_at(state_at_p1);
		}
		break;
	case state_move_p1_p2:
		feed.p2++;
		if (feed.p2 > feed.p2_timeout) {
			stop_at(state_at_p2);
		}
		break;
	case state_move_man:
		feed.man++;
		if (feed.man > feed.man_timeout) {
			stop_at(state_stop);
		}
		break;
	case state_move_h:
		feed.h++;
		if (feed.error) {
			thresh = feed.man_timeout;
		} else {
			thresh = feed.h_timeout;
		}
		if (feed.h > thresh) {
			stop_at(state_stop);
			flag_error();	// failed to reach home
		}
		break;
	default:
		break;
	}
}

static void read_voltage()
{
	if (ADCH < LOWVOLTS) {
		flag_error();
	}
}

static void update_state(uint8_t clock)
{
	read_triggers();
	read_timers();
	if (clock == 0) {
		read_voltage();
	}
}

static void show_value(struct console_event *event)
{
	switch (event->key) {
	case 0x68:
		console_showval("H time = ", feed.h_timeout);
		break;
	case 0x31:
		console_showval("P1 time = ", feed.p1_timeout);
		break;
	case 0x32:
		console_showval("P2 time = ", feed.p2_timeout);
		break;
	case 0x6d:
		console_showval("Man time = ", feed.man_timeout);
		break;
	case 0x74:
		console_showval("Throttle = ", feed.throttle & 0xff);
		break;
	case 0x62:
		console_showval("Brake = ", feed.brake & 0xff);
		break;
	default:
		console_write("Unknown value\r\n");
		break;
	}
}

static void update_value(struct console_event *event)
{
	switch (event->key) {
	case 0x31:
		feed.p1_timeout = event->value;
		console_showval("P1 time = ", feed.p1_timeout);
		save_config(0, feed.p1_timeout);
		break;
	case 0x32:
		feed.p2_timeout = event->value;
		console_showval("P2 time = ", feed.p2_timeout);
		save_config(0x2, feed.p2_timeout);
		break;
	case 0x6d:
		feed.man_timeout = event->value;
		console_showval("Man time = ", feed.man_timeout);
		save_config(0x4, feed.man_timeout);
		break;
	case 0x68:
		feed.h_timeout = event->value;
		console_showval("H time = ", feed.h_timeout);
		save_config(0x6, feed.h_timeout);
		break;
	case 0x62:
		feed.brake = event->value;
		console_showval("Brake = ", feed.brake & 0xff);
		save_config(0x8, feed.brake);
		if (bit_is_set(PORTD, R4)) {
			OCR2B = (uint8_t) (feed.brake & 0xff);
		}
		break;
	case 0x74:
		feed.throttle = event->value;
		console_showval("Throttle = ", feed.throttle & 0xff);
		save_config(0xa, feed.throttle);
		if (bit_is_set(PORTD, R1)) {
			OCR2A = (uint8_t) (feed.throttle & 0xff);
		}
		break;
	default:
		console_write("Unknown value\r\n");
		break;
	}
}

static void show_status(void)
{
	console_showstate(feed.state, feed.error, ADCH);
}

static void handle_event(struct console_event *event)
{
	switch (event->type) {
	case event_getvalue:
		show_value(event);
		break;
	case event_setvalue:
		update_value(event);
		break;
	case event_status:
		show_status();
		break;
	default:
		break;
	}
}

void main(void)
{
	uint8_t lt = 0;
	uint8_t nt;
	struct console_event event;
	system_init();
	feed.state = state_stop;

	do {
		sleep_mode();
		nt = SYSTICK;
		if (nt != lt) {
			update_state(nt);
			lt = nt;
		}
		console_read(&event);
		if (event.type != event_none) {
			handle_event(&event);
		}
	} while (1);
}
