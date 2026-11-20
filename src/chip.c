#include "chip.h"


void *ch8_new_core()
{
  ch8_core_t *core = calloc(1, sizeof(ch8_core_t));
  if (!core) return NULL;
  core.stack = calloc(CH8_STACK_SIZE, sizeof(u8));
  if (!core.stack) { free(core); return NULL }

  return core;
}

void ch8_update_inputs(u16 inputs, void *core)
{
  core = (ch8_core_t *)core;
  core.inputs = (ch8_inputs_t)inputs;
}
