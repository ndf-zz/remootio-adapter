// SPDX-License-Identifier: MIT

#include <stdint.h>
#include <stdlib.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
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
	static uint8_t prev = _BV(S3) | _BV(S4);
	uint8_t cur = PINC & SMASK;
	uint8_t flags = 0;
	uint8_t mask;
	if ((cur ^ prev) == 0) {
		mask = cur ^ feed.bstate;
		flags = (uint8_t) (mask & (~feed.bstate));
		feed.bstate = cur;
	}
	prev = cur;
	return flags;
}

static void watchdog_init(void)
{
	// set watchdog timer to ~ 0.25s
	wdt_enable(WDTO_250MS);
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

static void write_eeprom(uint16_t addr, uint8_t val)
{
	loop_until_bit_is_clear(EECR, EEPE);
	EEAR = addr;
	EEDR = val;
	EECR |= _BV(EEMPE);
	EECR |= _BV(EEPE);
}

static void write_word(uint16_t addr, uint16_t val)
{
	write_eeprom(addr++, val & 0xff);
	write_eeprom(addr, (uint8_t) (val >> 8));
}

static uint8_t read_eeprom(uint16_t addr)
{
	loop_until_bit_is_clear(EECR, EEPE);
	EEAR = addr;
	EECR |= _BV(EERE);
	return EEDR;
}

static uint16_t read_word(uint16_t addr)
{
	uint16_t val = read_eeprom(addr++);
	return val | (uint16_t) (read_eeprom(addr) << 8);
}

static void load_parameters(void)
{
	// Set initial input state
	feed.bstate = _BV(S3) | _BV(S4);

	// Load feeder parameters from EEPROM
	uint16_t seedoft = 0;
	uint16_t tmp = read_word(NVM_KEY);
	if (tmp == NVM_KEYVAL) {
		feed.p1_timeout = read_word(NVM_P1);
		feed.p2_timeout = read_word(NVM_P2);
		feed.man_timeout = read_word(NVM_MAN);
		feed.h_timeout = read_word(NVM_H);
		feed.f_timeout = read_word(NVM_F);
		feed.nf = read_word(NVM_NF);
		feed.brake = read_word(NVM_BRAKE);
		feed.throttle = read_word(NVM_THROTTLE);
		seedoft = read_word(NVM_SEEDOFT) + 4U;
		if (seedoft >= SEEDOFT_LEN) {
			seedoft = 0;
		}
		write_word(NVM_SEEDOFT, seedoft);
	} else {
		feed.p1_timeout = DEFAULT_P1;
		write_word(NVM_P1, feed.p1_timeout);
		feed.p2_timeout = DEFAULT_P2;
		write_word(NVM_P2, feed.p2_timeout);
		feed.man_timeout = DEFAULT_MAN;
		write_word(NVM_MAN, feed.man_timeout);
		feed.h_timeout = DEFAULT_H;
		write_word(NVM_H, feed.h_timeout);
		feed.f_timeout = DEFAULT_F;
		write_word(NVM_F, feed.f_timeout);
		feed.nf = DEFAULT_NF;
		write_word(NVM_NF, feed.nf);
		feed.brake = DEFAULT_BRAKE;
		write_word(NVM_BRAKE, feed.brake);
		feed.throttle = DEFAULT_THROTTLE;
		write_word(NVM_THROTTLE, feed.throttle);
		write_word(NVM_SEEDOFT, seedoft);
		write_word(NVM_KEY, NVM_KEYVAL);
	}

	// Initialise PRNG using next value from eeprom
	uint32_t seed = 0 | read_word(seedoft);
	seed = (seed << 16) | read_word(seedoft + 2U);
	srandom(seed);
}

void save_config(uint16_t addr, uint16_t val)
{
	ATOMIC_BLOCK(ATOMIC_FORCEON) {
		write_word(addr, val);
	}
}

void system_init(void)
{
	watchdog_init();
	timer_init();
	gpio_init();
	adc_init();
	console_init();
	load_parameters();
	sei();
}
