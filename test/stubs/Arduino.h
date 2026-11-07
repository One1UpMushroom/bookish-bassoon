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
#define FALLING 2
int digitalRead(pin_size_t pin);
int digitalPinToInterrupt(pin_size_t pin);
void attachInterrupt(int interrupt, void (*callback)(void), int mode);
void pinMode(pin_size_t pin, int mode);
void digitalWrite(pin_size_t pin, int val);
unsigned long millis();
void delay(unsigned long ms);
class Print {
 public:
  size_t print(const char*);
  size_t print(unsigned int);
  size_t println(const char*);
  size_t println(unsigned int);
};
class SerialUSB : public Print {
 public:
  void begin(unsigned long baud);
};
extern SerialUSB Serial;
class RP2040 {
 public:
  void wdt_begin(uint32_t delay_ms);
  void wdt_reset();
};
extern RP2040 rp2040;
