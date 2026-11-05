// ST7789 240x240 TFT driver wrapper with flicker-free, change-only updates.
#pragma once
#include <stdint.h>

#include "painter.h"

class Display {
 public:
  using DrawFn = void (*)(Painter&, void*);

  bool begin();
  // Draws the whole frame band by band into a small RAM buffer and pushes a
  // band over SPI only if its pixels differ from what is already on the glass.
  // Returns the number of bands sent.
  int render(DrawFn fn, void* ctx);
  void invalidate();        // force the next render to push everything
  void setSleep(bool sleep);
  bool asleep() const { return asleep_; }

 private:
  uint32_t hash_[5] = {};
  bool valid_[5] = {};
  bool asleep_ = false;
};
