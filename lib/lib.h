#ifndef LIB_H
#define LIB_H

#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

void var_print_int(int64_t x);
int64_t var_add(int64_t x, int64_t y);
void decref(void *ptr);

#endif