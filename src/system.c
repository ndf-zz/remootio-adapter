// SPDX-License-Identifier: MIT

#include <stdint.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>
#include "system.h"
#include "console.h"

// Global state machine
struct state_machine feed;

ISR(TIMER0_COMPA_vect)
{
	++SYSTICK;
}

uint8_t read_inputs(void)
{
	static uint8_t bstate = SMASK;
	static uint8_t prev = SMASK;
	uint8_t cur = PINC & SMASK;
	uint8_t flags = 0;
	uint8_t mask;
	if ((cur ^ prev) == 0) {
		mask = cur ^ bstate;
		flags = (uint8_t) (mask & (~bstate));
		bstate = cur;
	}
	prev = cur;
	return flags;
}

static void timer_init(void)
{
	// ~10ms Uptime timer
	OCR0A = 78U;
	TCCR0A = _BV(WGM01);
	TCCR0B = _BV(CS02);
	TIMSK0 |= _BV(OCIE0A);

	// fast PWM output timer
	OCR2A = 0;
	OCR2B = 0;
	TCCR2A = _BV(COM2A1) | _BV(COM2B1) | _BV(WGM20) | _BV(WGM21);
	TCCR2B = _BV(CS20);
}

// Refer: remootio_adapter_portpins.pdf
static void gpio_init(void)
{
	// Pullup unused inputs
	PORTB |= _BV(0) | _BV(1) | _BV(2) | _BV(4);

	// Pullup non-protected inputs S3-S6
	PORTC |= _BV(2) | _BV(3) | _BV(4) | _BV(5);

	// Enable outputs
	DDRB |= _BV(3) | _BV(5);
	DDRD |= _BV(2) | _BV(3) | _BV(4) | _BV(5) | _BV(6) | _BV(7);
}

static void adc_init(void)
{
	ADMUX |= _BV(REFS0) | _BV(ADLAR) | _BV(MUX2) | _BV(MUX1) | _BV(MUX0);
	ADCSRA |= _BV(ADEN) | _BV(ADPS2) | _BV(ADPS0);
}

static void write_eeprom(uint8_t addr, uint8_t val)
{
	loop_until_bit_is_clear(EECR, EEPE);
	EEARL = addr;
	EEDR = val;
	EECR |= _BV(EEMPE);
	EECR |= _BV(EEPE);
}

static void write_word(uint8_t addr, uint16_t val)
{
	write_eeprom(addr++, val & 0xff);
	write_eeprom(addr, (uint8_t) (val >> 8));
}

static uint8_t read_eeprom(uint8_t addr)
{
	loop_until_bit_is_clear(EECR, EEPE);
	EEARL = addr;
	EECR |= _BV(EERE);
	return EEDR;
}

static uint16_t read_word(uint8_t addr)
{
	uint16_t val = read_eeprom(addr++);
	return val | (uint16_t) (read_eeprom(addr) << 8);
}

static void load_parameters(void)
{
	// Load feeder parameters from EEPROM
	uint16_t tmp = read_word(0);
	if (tmp == 0xffff || tmp == 0) {
		feed.p1_timeout = DEFAULT_P1;
		write_word(0, feed.p1_timeout);
		feed.p2_timeout = DEFAULT_P2;
		write_word(0x2, feed.p2_timeout);
		feed.man_timeout = DEFAULT_MAN;
		write_word(0x4, feed.man_timeout);
		feed.h_timeout = DEFAULT_H;
		write_word(0x6, feed.h_timeout);
		feed.brake = DEFAULT_BRAKE;
		write_word(0x8, feed.brake);
		feed.throttle = DEFAULT_THROTTLE;
		write_word(0xa, feed.throttle);
	} else {
		feed.p1_timeout = tmp;
		feed.p2_timeout = read_word(0x2);
		feed.man_timeout = read_word(0x4);
		feed.h_timeout = read_word(0x6);
		feed.brake = read_word(0x8);
		feed.throttle = read_word(0xa);
	}
}

void save_config(uint8_t addr, uint16_t val)
{
	ATOMIC_BLOCK(ATOMIC_FORCEON) {
		write_word(addr, val);
	}
}

void system_init(void)
{
	timer_init();
	gpio_init();
	adc_init();
	console_init();
	load_parameters();
	sei();
}
