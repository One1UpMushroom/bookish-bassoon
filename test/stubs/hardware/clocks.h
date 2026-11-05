#pragma once
#include <stdint.h>
enum clock_index { clk_gpout0 = 0, clk_ref = 4, clk_sys = 5 };
uint32_t clock_get_hz(enum clock_index clk_index);
