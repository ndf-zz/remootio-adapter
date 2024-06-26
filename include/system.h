// SPDX-License-Identifier: MIT

#ifndef SYSTEM_H
#define SYSTEM_H

// Default user settings
#define DEFAULT_P1	800U	// 8s H -> P1
#define DEFAULT_P2	1500U	// 15s P1 -> P2
#define DEFAULT_F	30U	// 30 minutes, triggers P1->M_H
#define DEFAULT_NF	3	// 3 feeds per day (~4-12h gaps)
#define DEFAULT_MAN	250U	// 2.5s MAN Adjustment
#define DEFAULT_H	4000U	// 40s Max return home time
#define DEFAULT_BRAKE	0U	// Brake voltage ~= 5.0*val/255
#define DEFAULT_THROTTLE 255U	// Throttle voltage ~= 5.0*val/255

// Fixed voltage threshold
#define LOWVOLTS	0x35	// ~8.5V

// Define I/O aliases, Refer: remootio_adapter_portpins.pdf
#define V1	3U		// PORTB.3:OCR2A
#define LED	5U		// PORTB.5
#define S1	0		// PORTC.0
#define S2	1U		// PORTC.1
#define S3	2U		// PORTC.2
#define S4	3U		// PORTC.3
#define S5	4U		// PORTC.4
#define S6	5U		// PORTC.5
#define R1	7U		// PORTD.7
#define R2	6U		// PORTD.6
#define R3	5U		// PORTD.5
#define R4	4U		// PORTD.4
#define V2	3U		// PORTD.3:OCR2B
#define R5	2U		// PORTD.2
#define A1	7U		// ADC7
#define SMASK	(_BV(S1)|_BV(S2)|_BV(S3)|_BV(S4)|_BV(S5)|_BV(S6))
#define RMASK	(_BV(R1)|_BV(R2)|_BV(R3)|_BV(R4)|_BV(R5))
#define SYSTICK	GPIOR0

// Non-volatile data addresses
#define NVM_BASE	0x3e0
#define NVM_P1		(NVM_BASE + 0)
#define NVM_P2		(NVM_BASE + 0x2)
#define NVM_MAN		(NVM_BASE + 0x4)
#define NVM_H		(NVM_BASE + 0x6)
#define NVM_F		(NVM_BASE + 0x8)
#define NVM_NF		(NVM_BASE + 0xa)
#define NVM_BRAKE	(NVM_BASE + 0xc)
#define NVM_THROTTLE	(NVM_BASE + 0xe)
#define NVM_SEEDOFT	(NVM_BASE + 0x10)
#define NVM_KEY		(NVM_BASE + 0x12)
#define NVM_KEYVAL	0x55aa

// Random seed area
#define SEEDOFT_LEN	NVM_BASE

// Timing estimator (for 7812.5 Hz / 78 timer)
#define ONEMINUTE	6000U

// Throttle CV and motor switch pause
#define THROTTLE_DELAY 0x2000
#define MOTOR_DELAY 0xf00

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

struct state_machine {
	uint8_t state;	// machine state
	uint8_t error;  // error flag
	uint8_t bstate;  // current accepted input state
	uint16_t p1;  // elapsed 0.01s from H->P1
	uint16_t p1_timeout;  // target elapsed p1
	uint16_t p2;  // elapsed 0.01s from P1->P2
	uint16_t p2_timeout;  // target elapsed p2
	uint16_t man; // elapsed 0.01s manual adjust
	uint16_t man_timeout;  // max manual adjust
	uint16_t h;  // elapsed 0.01s moving toward h
	uint16_t h_timeout;  // maximum h movement
	uint16_t f;  // elapsed minutes at p1
	uint16_t f_timeout;  // maximum minutes at p1
	uint16_t nf;  // number of feeds/day
	uint16_t nf_count;  // minutes waiting for next feed
	uint16_t nf_timeout;  // target minutes for h->p1
	uint16_t brake;  // brake CV [unused]
	uint16_t throttle;  // throttle CV
	uint16_t count;  // 0.01s state counter for determining minutes
};

// global system variable
extern struct state_machine feed;

// Function prototypes
uint8_t read_inputs(void);
void save_config(uint16_t addr, uint16_t val);
void system_init(void);

#endif // SYSTEM_H
