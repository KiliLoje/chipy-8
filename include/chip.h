#include "common.h"

typedef struct {
  u8 bitmap[256];
} ch8_screen_t;

typedef u16 ch8_inputs_t;

typedef struct {
  u8 delay;
  u8 sound;
} ch8_timers_t;

typedef struct {
  u16 pc;
  u16 i;
  u8 v[16];
} ch8_registers_t;

typedef struct {
  u8 RAM[KiB(64)];
  u8 *stack;

  ch8_screen_t screen;
  ch8_inputs_t inputs;
  ch8_timers_t timers;
  ch8_registers_t registers;
} ch8_core_t;

void *ch8_new_core();
void ch8_update_inputs(u16 inputs, void *core);
