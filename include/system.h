// SPDX-License-Identifier: MIT

#ifndef SYSTEM_H
#define SYSTEM_H

// Default user settings
#define DEFAULT_P1	800U	// 8s H -> P1
#define DEFAULT_P2	500U	// 5s P1 -> P2
#define DEFAULT_MAN	210U	// 2.1s MAN Adjustment
#define DEFAULT_H	1600U	// 16s Max return home time
#define DEFAULT_BRAKE	70U	// Brake voltage ~= 5.0*val/255
#define DEFAULT_THROTTLE 140U	// Throttle voltage ~= 5.0*val/255

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
	uint8_t state;
	uint16_t p1;
	uint16_t p1_timeout;
	uint16_t p2;
	uint16_t p2_timeout;
	uint16_t man;
	uint16_t man_timeout;
	uint16_t h;
	uint16_t h_timeout;
	uint16_t brake;
	uint16_t throttle;
	uint8_t error;
};

// global system variable
extern struct state_machine feed;

// Function prototypes
uint8_t read_inputs(void);
void save_config(uint8_t addr, uint16_t val);
void system_init(void);

#endif // SYSTEM_H
