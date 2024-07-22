// SPDX-License-Identifier: MIT

/*
 * AVR m328p (Nano) Serial "PLC"
 */
#include <stdint.h>
#include <stdlib.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include <util/delay_basic.h>
#include "system.h"
#include "console.h"

struct state_machine feed;

static void flag_error(void)
{
	// Clear Indicator
	PORTB &= (uint8_t) ~ _BV(LED);
	feed.error = 1U;
}

static void clear_error(void)
{
	// Set Indicator
	PORTB |= _BV(LED);
	feed.error = 0;
}

static void motor_start(void)
{
	OCR2B = 0;		// lower brake CV
	PORTD &= (uint8_t) ~ (_BV(R4));	// disable brake sw
	PORTD |= _BV(R1);	// connect throttle
	_delay_loop_2(MOTOR_DELAY);	// pause for controller
	OCR2A = feed.throttle & 0xff;	// raise throttle CV
}

static void motor_stop(void)
{
	OCR2A = 0;		// lower throttle CV
	_delay_loop_2(THROTTLE_DELAY);	// pause to allow CV to settle
	PORTD &= (uint8_t) ~ (_BV(R1));	// disable throttle sw
	PORTD &= (uint8_t) ~ (_BV(R2) | _BV(R3));	// disable direction
	PORTD |= _BV(R4);	// connect brake sw
	OCR2B = feed.brake & 0xff;	// raise brake CV
}

static void motor_reverse(void)
{
	PORTD |= _BV(R3);	// enable R3 REV
	_delay_loop_2(MOTOR_DELAY);	// pause for controller
}

static void motor_forward(void)
{
	PORTD |= _BV(R2);	// enable R2 FWD
	_delay_loop_2(MOTOR_DELAY);	// pause for controller
}

static void set_state(uint8_t newstate)
{
	feed.state = newstate;
	feed.count = 0;
	feed.mincount = 0;
	feed.minutes = 0;
	console_showstate(feed.state, feed.error, ADCH);
}

static void stop_at(uint8_t newstate)
{
	set_state(newstate);
	motor_stop();
}

static void set_randfeed(void)
{
	if (feed.nf) {
		uint16_t period = 1440 / feed.nf;
		if (period) {
			uint16_t oft = period >> 1;
			uint32_t randval = (uint32_t) random();
			uint32_t tmp =
			    ((uint32_t) (period) * (randval >> 12) +
			     (1UL << 18)) >> 19;
			feed.nf_timeout = oft + (uint16_t) (tmp);
		} else {
			feed.nf_timeout = 0;
		}
	} else {
		feed.nf_timeout = 0;
	}
	if (feed.nf_timeout) {
		console_showval("Feed in (min): ", feed.nf_timeout);
	}
}

static void stop_at_home(void)
{
	stop_at(state_at_h);
	clear_error();
	// Signal AT H state to Remootio
	PORTD |= _BV(R5);
	set_randfeed();
}

static void move_up(uint8_t newstate)
{
	if ((feed.bstate & TRIGGER_HOME) == 0) {
		set_state(newstate);
		motor_stop();
		motor_reverse();
		motor_start();
	} else {
		console_write("Sensor error\r\n");
		flag_error();
		stop_at(state_stop);
	}
}

static void move_down(uint8_t newstate)
{
	set_state(newstate);
	motor_forward();
	motor_start();
}

static void trigger_p1(void)
{
	if (feed.state == state_move_h_p1) {
		console_write("Trigger: p1\r\n");
		stop_at(state_at_p1);
		// Signal AT P1 state to Remootio
		PORTD &= (uint8_t) ~ _BV(R5);
	} else {
		console_write("Spurious P1 trigger ignored\r\n");
	}
}

static void trigger_reset(void)
{
	console_write("Trigger: reset\r\n");
	stop_at(state_stop);
}

static void trigger_p2(void)
{
	if (feed.state == state_move_p1_p2) {
		console_write("Trigger: p2\r\n");
		stop_at(state_at_p2);
	} else {
		console_write("Spurious P2 trigger ignored\r\n");
	}
}

static void trigger_man(void)
{
	if (feed.state == state_move_man) {
		console_write("Trigger: man\r\n");
		stop_at(state_stop);
	} else {
		console_write("Spurious Man trigger ignored\r\n");
	}
}

static void trigger_max(void)
{
	if (feed.state == state_move_h) {
		console_write("Trigger: max\r\n");
		flag_error();	// failed to reach home
		stop_at(state_stop);
	} else {
		console_write("Spurious Max trigger ignored\r\n");
	}
}

static void trigger_up(void)
{
	console_write("Trigger: up\r\n");
	switch (feed.state) {
	case state_stop:
	case state_stop_h_p1:
	case state_stop_p1_p2:
	case state_at_p1:
	case state_at_p2:
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
		console_write("Ignored spurious UP trigger\r\n");
		break;
	}
}

static void trigger_down(void)
{
	console_write("Trigger: down\r\n");
	switch (feed.state) {
	case state_stop:
		move_down(state_move_man);
		break;
	case state_stop_h_p1:
		move_down(state_move_h_p1);
		break;
	case state_stop_p1_p2:
		move_down(state_move_p1_p2);
		break;
	case state_at_h:
		move_down(state_move_h_p1);
		feed.p1 = 0;
		break;
	case state_at_p1:
		move_down(state_move_p1_p2);
		feed.p2 = 0;
		break;
	case state_at_p2:
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
		console_write("Ignored spurious DOWN trigger\r\n");
		break;
	}
}

static void trigger_home(void)
{
	console_write("Trigger: home\r\n");
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
		// spurious home sense - assume return to home or error?
		console_write("Spurious Home trigger\r\n");
		//flag_error();
		stop_at_home();
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
	feed.count++;
	feed.mincount++;
	switch (feed.state) {
	case state_move_h_p1:
		feed.p1++;
		if (feed.p1 > feed.p1_timeout) {
			trigger_p1();
		}
		break;
	case state_move_p1_p2:
		feed.p2++;
		if (feed.p2 > feed.p2_timeout) {
			trigger_p2();
		}
		break;
	case state_move_man:
		if (feed.count > feed.man_timeout) {
			trigger_man();
		}
		break;
	case state_move_h:
		if (feed.error) {
			thresh = feed.man_timeout;
		} else {
			thresh = feed.h_timeout;
		}
		if (feed.count > thresh) {
			trigger_max();
		}
		break;
	case state_at_p1:
		if (feed.f_timeout) {
			if (feed.minutes >= feed.f_timeout) {
				trigger_up();
			}
		}
		break;
	case state_at_h:
		if (feed.nf_timeout > 0) {
			if (feed.minutes >= feed.nf_timeout) {
				trigger_down();
			}
		}
		break;
	case state_stop:
	case state_stop_p1_p2:
	case state_at_p2:
		if (feed.minutes >= DEFAULT_S) {
			console_write("Safe time reached\r\n");
			trigger_up();
		}
		break;
	default:
		break;
	}
	if (feed.mincount >= ONEMINUTE) {
		feed.minutes++;
		feed.mincount = 0;
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
	case 0x66:
		console_showval("Feed time = ", feed.f_timeout);
		break;
	case 0x6e:
		console_showval("Feeds/day = ", feed.nf);
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
		if (event->value) {
			feed.p1_timeout = event->value;
		}
		console_showval("P1 time = ", feed.p1_timeout);
		save_config(NVM_P1, feed.p1_timeout);
		break;
	case 0x32:
		if (event->value) {
			feed.p2_timeout = event->value;
		}
		console_showval("P2 time = ", feed.p2_timeout);
		save_config(NVM_P2, feed.p2_timeout);
		break;
	case 0x66:
		feed.f_timeout = event->value;
		console_showval("Feed time = ", feed.f_timeout);
		save_config(NVM_F, feed.f_timeout);
		break;
	case 0x6e:
		feed.nf = event->value;
		console_showval("Feeds/day = ", feed.nf);
		save_config(NVM_NF, feed.nf);
		if (feed.state == state_at_h) {
			set_randfeed();
		}
		break;
	case 0x6d:
		if (event->value) {
			feed.man_timeout = event->value;
		}
		console_showval("Man time = ", feed.man_timeout);
		save_config(NVM_MAN, feed.man_timeout);
		break;
	case 0x68:
		if (event->value) {
			feed.h_timeout = event->value;
		}
		console_showval("H time = ", feed.h_timeout);
		save_config(NVM_H, feed.h_timeout);
		break;
	case 0x62:
		feed.brake = event->value;
		console_showval("Brake = ", feed.brake & 0xff);
		save_config(NVM_BRAKE, feed.brake);
		if (bit_is_set(PORTD, R4)) {
			OCR2B = (uint8_t) (feed.brake & 0xff);
		}
		break;
	case 0x74:
		feed.throttle = event->value;
		console_showval("Throttle = ", feed.throttle & 0xff);
		save_config(NVM_THROTTLE, feed.throttle);
		if (bit_is_set(PORTD, R1)) {
			OCR2A = (uint8_t) (feed.throttle & 0xff);
		}
		break;
	default:
		console_write("Unknown value\r\n");
		break;
	}
}

static void show_values(void)
{
	console_write("Current Values:\r\n");
	console_showval("\tH-P1 time (0.01s)= ", feed.p1_timeout);
	console_showval("\tP1-P2 time = ", feed.p2_timeout);
	console_showval("\tMan time = ", feed.man_timeout);
	console_showval("\tH time = ", feed.h_timeout);
	console_showval("\tFeed time (min)= ", feed.f_timeout);
	console_showval("\tFeeds/day (0=off)= ", feed.nf);
	console_showval("\tThrottle (1-255)= ", feed.throttle & 0xff);
	console_showval("\tState counter = ", feed.count);
	console_showval("\tState minutes = ", feed.minutes);
	console_write("\r\n");
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
	case event_values:
		show_values();
		break;
	case event_down:
		trigger_down();
		break;
	case event_up:
		trigger_up();
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
	trigger_reset();

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
		wdt_reset();
	} while (1);
}
