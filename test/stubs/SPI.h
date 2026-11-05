#pragma once
#include "Arduino.h"
#define SPI_MODE0 0
class SPIClass {
 public:
  bool setSCK(pin_size_t pin);
  bool setTX(pin_size_t pin);
  void begin(bool hwCS = false);
};
extern SPIClass SPI;
