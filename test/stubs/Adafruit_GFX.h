#pragma once
#include "Arduino.h"
class Adafruit_GFX : public Print {
 public:
  Adafruit_GFX(int16_t w, int16_t h);
  virtual void fillRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color);
  virtual void fillScreen(uint16_t color);
  void setTextSize(uint8_t s);
  void setTextColor(uint16_t c);
  void setCursor(int16_t x, int16_t y);
  void setTextWrap(bool w);
  void cp437(bool x = true);
  void setRotation(uint8_t r);
};
class GFXcanvas16 : public Adafruit_GFX {
 public:
  GFXcanvas16(uint16_t w, uint16_t h);
  uint16_t* getBuffer(void) const;
};
