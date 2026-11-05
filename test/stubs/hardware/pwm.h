#pragma once
#include <stdint.h>
typedef unsigned int uint;
enum pwm_chan { PWM_CHAN_A = 0, PWM_CHAN_B = 1 };
typedef struct { uint32_t csr, div, top; } pwm_config;
typedef struct { volatile uint32_t en; } pwm_hw_t;
extern pwm_hw_t* pwm_hw;
enum gpio_function { GPIO_FUNC_PWM = 4 };
void gpio_set_function(uint gpio, enum gpio_function fn);
uint pwm_gpio_to_slice_num(uint gpio);
uint pwm_gpio_to_channel(uint gpio);
pwm_config pwm_get_default_config(void);
void pwm_config_set_clkdiv_int(pwm_config* c, uint div);
void pwm_config_set_wrap(pwm_config* c, uint16_t wrap);
void pwm_config_set_output_polarity(pwm_config* c, bool a, bool b);
void pwm_init(uint slice_num, pwm_config* c, bool start);
void pwm_set_mask_enabled(uint32_t mask);
void pwm_set_counter(uint slice_num, uint16_t c);
void pwm_set_gpio_level(uint gpio, uint16_t level);
