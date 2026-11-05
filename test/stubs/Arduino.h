#pragma once
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef unsigned int uint;
typedef uint8_t byte;
typedef uint8_t pin_size_t;
#define OUTPUT 0x1
#define INPUT 0x0
#define INPUT_PULLUP 0x2
#define HIGH 1
#define LOW 0
void pinMode(pin_size_t pin, int mode);
void digitalWrite(pin_size_t pin, int val);
unsigned long millis();
void delay(unsigned long ms);
class Print {
 public:
  size_t print(const char*);
};
class RP2040 {
 public:
  void wdt_begin(uint32_t delay_ms);
  void wdt_reset();
};
extern RP2040 rp2040;
