#pragma once
#include <stdint.h>
typedef struct { volatile uint32_t owner; } mutex_t;
#define auto_init_mutex(name) mutex_t name
void mutex_enter_blocking(mutex_t* mtx);
bool mutex_try_enter(mutex_t* mtx, uint32_t* owner_out);
void mutex_exit(mutex_t* mtx);
