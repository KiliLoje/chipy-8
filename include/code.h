#include "common.h"

typedef struct {
  u16 raw;
  u8 category;
  u8 x;
  u8 y;
  u8 n1;
  u8 n2;
  u16 n3;
} ch8_code_t;

ch8_code_t ch8_get_code(u16 raw);
