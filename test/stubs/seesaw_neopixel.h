#pragma once
#include "Adafruit_seesaw.h"
#define NEO_GRB ((1 << 6) | (1 << 4) | (0 << 2) | (2))
#define NEO_KHZ800 0x0000
typedef uint16_t neoPixelType;
class seesaw_NeoPixel : public Adafruit_seesaw {
 public:
  seesaw_NeoPixel(uint16_t n, uint16_t p = 6, neoPixelType t = NEO_GRB + NEO_KHZ800,
                  TwoWire* Wi = &Wire);
  bool begin(uint8_t addr = SEESAW_ADDRESS, int8_t flow = -1);
  void setPixelColor(uint16_t n, uint32_t c);
  void show(void);
};
