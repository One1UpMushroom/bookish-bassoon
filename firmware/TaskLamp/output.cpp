#include "output.h"

#include <math.h>

void OutputStage::configure(const HwCfg& hw, uint16_t pwmTop) {
  for (int i = 0; i < kCh; i++) {
    trim_[i] = hw.chTrim[i] * 0.001f;
    mA_[i] = hw.chmA[i];
    minDuty_[i] = hw.chMin[i] * 0.00001f;  // stored in 0.001 % units
  }
  budget_ = hw.budgetmA;
  full_ = (uint32_t)pwmTop + 1u;
}

void OutputStage::process(const Rgbww& in, OutputResult& r) const {
  float y[kCh];
  float demand = 0.f;
  for (int i = 0; i < kCh; i++) {
    y[i] = color::clamp01(in.v[i]) * trim_[i];
    demand += y[i] * mA_[i];
  }

  // Power budget: scale every channel by the same factor so the colour is kept
  // and only the brightness is limited. Protects the PSU, drivers and LEDs.
  r.limited = false;
  if (budget_ > 0.f && demand > budget_) {
    float k = budget_ / demand;
    for (int i = 0; i < kCh; i++) y[i] *= k;
    r.limited = true;
  }

  r.mA = 0.f;
  for (int i = 0; i < kCh; i++) {
    float duty = 0.f;
    uint32_t lvl = 0;
    if (y[i] > 0.f) {
      // Map (0, 1] onto (minDuty, 1]: the bottom of the knob starts exactly
      // where this LED/driver combination begins to emit light.
      duty = minDuty_[i] + (1.f - minDuty_[i]) * y[i];
      lvl = (uint32_t)lroundf(duty * (float)full_);
      if (lvl == 0) lvl = 1;
      if (lvl > full_) lvl = full_;
    }
    r.level[i] = (uint16_t)lvl;
    r.lin[i] = y[i];
    r.mA += duty * mA_[i];
  }
}
