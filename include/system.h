// SPDX-License-Identifier: MIT

#ifndef SYSTEM_H
#define SYSTEM_H
#include <avr/io.h>

// Define missing IO regs - fixed in avr-libc 2.2
#ifndef PORTE
#define PORTE _SFR_IO8(0x0E)
#define UBRR1L  _SFR_MEM8(0xCC)
#define UCSR1A  _SFR_MEM8(0xC8)
#define UCSR1B  _SFR_MEM8(0xC9)
#define UCSR1C  _SFR_MEM8(0xCA)
#define UDR1    _SFR_MEM8(0xCE)
#endif // PORTE

// Default user settings
#define DEFAULT_P1	1250U	// 12.5s H -> P1
#define DEFAULT_P2	1500U	// 15s P1 -> P2
#define DEFAULT_F	30U	// 30 minutes, triggers P1->M_H
#define DEFAULT_NF	0U	// Feeds/week disabled
#define DEFAULT_MAN	400U	// 4s MAN adjustment
#define DEFAULT_H	4000U	// 40s Max return home time
#define DEFAULT_HR	250U	// 2.5s Home retry timeout
#define DEFAULT_S	45U	// 45 minutes safe time, triggers M_H
#define DEFAULT_PK	0U	// Default Console PIN

// Fixed voltage threshold
#define LOWVOLTS	0x4a	// ~11.8V

// Auto lowering voltage threshold
#define NIGHTVOLTS	0x53	// ~13.2V

// Define I/O aliases, Refer: pcb/m328pb_portpins.pdf
#define S1	0		// PORTC.0
#define S2	1U		// PORTC.1
#define S6	2U		// PORTC.2
#define S5	3U		// PORTC.3
#define S3	4U		// PORTC.4
#define S4	5U		// PORTC.5
#define LED	2U		// PORTD.2
#define V1	3U		// PORTD.3
#define R4	4U		// PORTD.4
#define R3	5U		// PORTD.5
#define R1	6U		// PORTD.6
#define R2	7U		// PORTD.7
#define A1	3U		// PORTE.3:ADC7
#define IMASK	(_BV(S1)|_BV(S2)|_BV(S3)|_BV(S4)|_BV(S5)|_BV(S6))
#define OMASK	(_BV(LED)|_BV(V1)|_BV(R1)|_BV(R2)|_BV(R3)|_BV(R4))
#define SYSTICK	GPIOR0

// Non-volatile data addresses
#define NVM_BASE	0x3e0
#define NVM_P1		(NVM_BASE + 0)
#define NVM_P2		(NVM_BASE + 0x2)
#define NVM_MAN		(NVM_BASE + 0x4)
#define NVM_H		(NVM_BASE + 0x6)
#define NVM_F		(NVM_BASE + 0x8)
#define NVM_NF		(NVM_BASE + 0xa)
#define NVM_SPMOFT	(NVM_BASE + 0xc)
#define NVM_RSV0E	(NVM_BASE + 0xe)
#define NVM_SEEDOFT	(NVM_BASE + 0x10)
#define NVM_KEY		(NVM_BASE + 0x12)
#define NVM_KEYVAL	0x55aa
#define NVM_HR		(NVM_BASE + 0x14)
#define NVM_PK		(NVM_BASE + 0x16)
#define NVM_RSV18	(NVM_BASE + 0x18)
#define NVM_RSV1A	(NVM_BASE + 0x1a)
#define NVM_RSV1C	(NVM_BASE + 0x1c)
#define NVM_RSV1E	(NVM_BASE + 0x1e)

// Random seed area
#define SEEDOFT_LEN	NVM_BASE

// Timing estimator (for 7812.5 Hz / 78 timer)
#define ONEMINUTE	6000U

// One week of minutes
#define ONEWEEK		10080U

// Motor enable/disable delay time
#define MOTOR_DELAY	0x2710	// ~ 20ms
#define MOTOR_OFFTIME	0xc350	// ~ 0.1s
#define MOTOR_OFFCOUNT	2U

// Output function labels
#define FWD		R1
#define REV		R2
#define PWR		R3
#define ATP1		R4
#define THROTTLE	V1

// Input switch triggers (asserted after debouncing via read_input)
#define TRIGGER_HOME	_BV(S1)
#define TRIGGER_UP	_BV(S3)
#define TRIGGER_DOWN	_BV(S4)
#define TRIGMASK	(TRIGGER_HOME|TRIGGER_UP|TRIGGER_DOWN)

enum machine_state {
	state_stop,
	state_stop_h_p1,
	state_stop_p1_p2,
	state_at_h,
	state_at_p1,
	state_at_p2,
	state_move_h_p1,
	state_move_p1_p2,
	state_move_h,
	state_move_man,
	state_error,
};

// Note: counters p1 and p2 are preserved across move/stop transitions:
//       MOVE H-P1 <-> STOP H-P1
//       MOVE P1-P2 <-> STOP P1-P2
struct state_machine {
	uint8_t state;		// machine state
	uint8_t error;		// error flag
	uint8_t bstate;		// current accepted input state
	uint16_t p1;		// elapsed 0.01s moving h->p1
	uint16_t p1_timeout;	// target elapsed p1
	uint16_t p2;		// elapsed 0.01s moving p1->p2
	uint16_t p2_timeout;	// target elapsed p2
	uint16_t man_timeout;	// max manual adjust
	uint16_t h_timeout;	// maximum h movement
	uint16_t f_timeout;	// maximum minutes at p1
	uint16_t nf;		// number of feeds/day
	uint16_t nf_timeout;	// target minutes for h->p1
	uint16_t count;		// 0.01s state counter
	uint16_t mincount;	// 0.01s state counter for determining minutes
	uint16_t minutes;	// minute state counter
	uint16_t hr_timeout;	// home retry timeout
	uint16_t pk;		// serial console passkey
};

// global system variable
extern struct state_machine feed;

// global system version
extern uint16_t sw_version;

// Function prototypes
void write_word(uint16_t addr, uint16_t val);
uint16_t read_word(uint16_t addr);
uint8_t read_inputs(void);
void save_config(uint16_t addr, uint16_t val);
void system_init(void);

#endif // SYSTEM_H
