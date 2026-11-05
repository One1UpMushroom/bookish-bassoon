// RP2040 hardware PWM for the five LED channels and the TFT backlight.
// Owned exclusively by core 1.
#pragma once
#include <stdint.h>

#include "color.h"

class PwmBank {
 public:
  // (Re)configures all slices for `hz`. Returns the counter top; a channel
  // level of top+1 means 100 % duty. Resolution = log2(top+1) bits.
  uint16_t begin(uint32_t hz, const uint8_t invert[kCh]);
  void write(const uint16_t level[kCh]);   // only touches registers that changed
  void setBacklight(float fraction);       // 0..1 linear
  void allOff();
  uint16_t top() const { return top_; }
  uint32_t actualHz() const { return actualHz_; }

 private:
  void writeChannel(int ch, uint16_t level);

  uint16_t top_ = 0;
  uint32_t actualHz_ = 0;
  // 32-bit caches: a 100 % level can itself be 0xFFFF, so "unknown" must be
  // a value no 16-bit level can take.
  static constexpr uint32_t kUnknown = 0xFFFFFFFFu;
  uint32_t last_[kCh] = {kUnknown, kUnknown, kUnknown, kUnknown, kUnknown};
  bool endAligned_[kCh] = {};
  uint32_t lastBl_ = kUnknown;
};
