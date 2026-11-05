#pragma once
#include "Arduino.h"
class TwoWire {
 public:
  bool setSDA(pin_size_t sda);
  bool setSCL(pin_size_t scl);
  void begin();
  void setClock(uint32_t freq);
};
extern TwoWire Wire;
extern TwoWire Wire1;
