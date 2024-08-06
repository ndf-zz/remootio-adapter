// SPDX-License-Identifier: MIT

#include <stdint.h>
#include <avr/io.h>
#include <avr/wdt.h>
#include <util/delay_basic.h>
#include <string.h>
#include "system.h"
#include "console.h"
#include "spm_config.h"

#define SPM_MAXLEN	24U
#define SPM_CHARWAIT	32U	// ~ 0.000048s
#define SPM_TIMEOUT	4150U	// roughly 0.2s
#define SPM_PACKLEN	0x10
#define SPM_SUBLEN	0x0d
#define SPM_WAKECOUNT	3U	// controller needs time to wake up

static uint8_t readbuf[SPM_MAXLEN];	// read buffer
static uint8_t cfgmem[128];	// mem buffer

// Write byte to controller USART
static void spm_write(uint8_t ch)
{
	loop_until_bit_is_set(UCSR1A, UDRE0);
	UDR1 = ch;
}

// Read len bytes from controller USART or timeout
static uint8_t spm_read(uint8_t len)
{
	uint8_t *buf = &readbuf[0];
	uint8_t count = 0;
	uint16_t waits = 0;
	do {
		if (count >= len) {
			break;
		}
		if (bit_is_set(UCSR1A, RXC0)) {
			*(buf++) = UDR1;
			++count;
			waits = 0;
		} else {
			_delay_loop_1(SPM_CHARWAIT);
			++waits;
		}
	} while (waits < SPM_TIMEOUT);
	return count;
}

// Compute checksum
static uint8_t rcvsum(uint8_t len)
{
	uint8_t *buf = &readbuf[1];
	uint8_t sum = readbuf[0];
	len = (uint8_t) (len - 2U);
	while (len) {
		sum = (uint8_t) (sum + *(buf++));
		--len;
	}
	return sum;
}

// Receive an expected packet with header and length
static uint8_t spm_receive(uint8_t hdr, uint8_t bodylen)
{
	uint8_t total = (uint8_t) (3U + bodylen);
	if (spm_read(total) == total) {
		// Check header and report length
		if (readbuf[0] != hdr || readbuf[1] != bodylen) {
			console_write("SPM: Invalid header\r\n");
			return 0;
		}
		// Compare checksum
		uint8_t sum = rcvsum(total);
		if (sum != readbuf[total - 1]) {
			console_write("SPM: Invalid checksum\r\n");
			return 0;
		}
		return 1U;
	} else {
		return 0;
	}
}

// Send a request with optional body to controller
static void spm_send(uint8_t hdr, uint8_t len, uint8_t * body)
{
	spm_write(hdr);
	spm_write(len);
	hdr = (uint8_t) (hdr + len);
	while (len) {
		uint8_t tmp = *(body++);
		spm_write(tmp);
		hdr = (uint8_t) (hdr + tmp);
		--len;
	}
	spm_write(hdr);
}

// Request controller interface version
static uint8_t spm_getinfo(void)
{
	spm_send(0x11, 0, 0);
	return spm_receive(0x11, 3U);
}

// Wait for controller then try to establish connection
static uint8_t spm_connect(void)
{
	spm_read(SPM_MAXLEN);
	uint8_t count = 0;
	do {
		wdt_reset();
		spm_send(0xf1, 0, 0);
		spm_read(SPM_MAXLEN);
		++count;
	} while (count < SPM_WAKECOUNT);
	wdt_reset();
	return spm_getinfo();
}

// Enable controller USART
static void spm_open(void)
{
	// 19200,8n1 blocking read/write
	UBRR1L = 12;
	UCSR1A |= _BV(U2X0);	// x2 clock
	UCSR1B = _BV(RXEN0) | _BV(TXEN0);
	UCSR1C = _BV(UCSZ01) | _BV(UCSZ00);
}

// Disable controller USART
static void spm_close(void)
{
	UCSR1B = 0;
}

// Issue a message to console then force reboot
static void spm_lockup(const char *message)
{
	console_write(message);
	PORTD &= (uint8_t) ~ _BV(PWR);	// disable motor controller
	wdt_reset();
	while (1U) ;
}

// Compare and update cfgmem with desired config values
static uint8_t spm_comparemem(void)
{
	uint8_t count = 0;
	uint8_t nochange = 1U;
	while (count < SPM_CFGLEN) {
		uint8_t oft = cfg_bytes[count];
		uint8_t val = cfg_vals[count];
		if (cfgmem[oft] != val) {
			cfgmem[oft] = val;
			nochange = 0;
		}
		++count;
	}
	return nochange;
}

// Pad request body with 0xff
static void spm_padblock(uint8_t * buf, uint8_t len)
{
	while (len) {
		*(buf++) = 0xff;
		--len;
	}
}

// Write cfgmem to controller over USART
static uint8_t spm_writemem(void)
{
	uint8_t oft = 0;

	while (oft < 0x80) {
		uint8_t remain = (uint8_t) (0x80 - oft);
		uint8_t plen = SPM_SUBLEN < remain ? SPM_SUBLEN : remain;
		readbuf[0] = oft;
		readbuf[1] = plen;
		readbuf[2] = 0;
		memcpy(&readbuf[3], &cfgmem[oft], plen);
		if (plen < SPM_SUBLEN) {
			spm_padblock(&readbuf[plen + 3],
				     (uint8_t) (SPM_SUBLEN - plen));
		}
		spm_send(0xf3, SPM_PACKLEN, &readbuf[0]);
		wdt_reset();
		if (!spm_receive(0xf3, 1)) {
			console_write("SPM: Write error\r\n");
			break;
		}
		wdt_reset();
		oft = (uint8_t) (oft + plen);
	}

	if (oft != 0x80) {
		console_write("SPM: Write error\r\n");
		return 0;
	}
	spm_send(0xf4, 0, 0);
	wdt_reset();
	return spm_receive(0xf4, 0);
}

// Check if controller model matches expected value
static uint8_t spm_modelok(void)
{
	uint8_t target[8U] = SPM_MODEL;
	uint8_t count = 0;
	uint8_t *src = &cfgmem[0x40];
	uint8_t *chk = &target[0];
	while (count < 8U) {
		if (*(src++) != *(chk++)) {
			console_showascii("SPM: Unknown model ", &cfgmem[0x40],
					  8U);
			return 0;
		}
		++count;
	}
	return 1U;
}

// Read controller memory and update if changes are required
static void spm_checkmem(void)
{
	uint8_t msg[] = { 0x00, SPM_PACKLEN, 0x00 };
	uint8_t count = 0;
	while (count < 8U) {
		spm_send(0xf2, 0x3, &msg[0]);
		if (spm_receive(0xf2, SPM_PACKLEN)) {
			memcpy(&cfgmem[msg[0]], &readbuf[2], SPM_PACKLEN);
		} else {
			break;
		}
		msg[0] = (uint8_t) (msg[0] + SPM_PACKLEN);
		wdt_reset();
		++count;
	}
	if (count != 8) {
		console_write("SPM: Read error\r\n");
		return;
	}
	if (!spm_modelok()) {
		return;
	}
	if (spm_comparemem()) {
		console_showhex("SPM: ", &cfgmem[0x4c], 4);
		return;
	}
	wdt_reset();
	if (spm_writemem()) {
		spm_lockup("SPM: Config updated\r\n");
	} else {
		console_write("SPM: Update error\r\n");
	}
}

// Perform controller check
void spm_check(void)
{
	PORTD |= _BV(PWR);	// enable controller power
	wdt_reset();
	_delay_loop_2(MOTOR_DELAY);
	wdt_reset();
	spm_open();
	if (spm_connect()) {
		wdt_reset();
		spm_checkmem();
	} else {
		console_write("SPM: Not connected\r\n");
	}
	spm_close();
	PORTD &= (uint8_t) ~ _BV(PWR);	// disable motor controller
}
