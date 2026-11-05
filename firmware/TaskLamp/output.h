// Output stage: calibration, power budget and duty-floor mapping.
// Converts linear channel drive (0..1) into PWM compare levels. Pure C++.
#pragma once
#include <stdint.h>

#include "color.h"
#include "settings.h"

struct OutputResult {
  uint16_t level[kCh];  // PWM compare value, 0..top+1 (top+1 = 100%)
  float lin[kCh];       // linear drive actually delivered (after trim + cap)
  float mA;             // estimated total LED current (0 if channels uncalibrated)
  bool limited;         // power budget is currently clamping the output
};

class OutputStage {
 public:
  void configure(const HwCfg& hw, uint16_t pwmTop);
  void process(const Rgbww& in, OutputResult& r) const;

 private:
  float trim_[kCh] = {1, 1, 1, 1, 1};
  float mA_[kCh] = {0, 0, 0, 0, 0};
  float minDuty_[kCh] = {0, 0, 0, 0, 0};
  float budget_ = 0;
  uint32_t full_ = 65535;  // top + 1
};
