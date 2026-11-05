#pragma once
#include "Adafruit_GFX.h"
#include "SPI.h"
class Adafruit_SPITFT : public Adafruit_GFX {
 public:
  Adafruit_SPITFT(uint16_t w, uint16_t h);
  void drawRGBBitmap(int16_t x, int16_t y, uint16_t* pcolors, int16_t w, int16_t h);
  void setSPISpeed(uint32_t freq);
};
class Adafruit_ST77xx : public Adafruit_SPITFT {
 public:
  Adafruit_ST77xx(uint16_t w, uint16_t h);
  void enableSleep(bool enable);
  void enableDisplay(bool enable);
};
class Adafruit_ST7789 : public Adafruit_ST77xx {
 public:
  Adafruit_ST7789(SPIClass* spiClass, int8_t cs, int8_t dc, int8_t rst);
  void init(uint16_t width, uint16_t height, uint8_t spiMode = SPI_MODE0);
  void setRotation(uint8_t m);
};
