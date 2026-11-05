#pragma once
#include "Arduino.h"
#include "Wire.h"
#define SEESAW_ADDRESS (0x49)
enum { SEESAW_STATUS_BASE = 0x00, SEESAW_GPIO_BASE = 0x01, SEESAW_ENCODER_BASE = 0x11 };
enum { SEESAW_GPIO_BULK = 0x04 };
enum { SEESAW_ENCODER_POSITION = 0x30, SEESAW_ENCODER_DELTA = 0x40 };
class Adafruit_seesaw : public Print {
 public:
  Adafruit_seesaw(TwoWire* Wi = NULL);
  bool begin(uint8_t addr = SEESAW_ADDRESS, int8_t flow = -1, bool reset = true);
  uint32_t getVersion();
  void pinMode(uint8_t pin, uint8_t mode);
  bool digitalRead(uint8_t pin);
  int32_t getEncoderDelta(uint8_t encoder = 0);

 protected:
  bool read(uint8_t regHigh, uint8_t regLow, uint8_t* buf, uint8_t num, uint16_t delay = 250);
};
