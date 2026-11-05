#include "pwm_hw.h"

#include <Arduino.h>
#include <hardware/clocks.h>
#include <hardware/pwm.h>

#include "config.h"

// Tricks used here:
//  * Resolution is maximised for the requested frequency: the clock divider is
//    the smallest integer that lets the 16-bit counter cover one period.
//  * The LED slices are started with staggered counters, and the second
//    channel of each shared slice is "end-aligned" (inverted polarity with a
//    complemented compare value). Channels therefore switch on at different
//    moments instead of all at once, which spreads the current draw over the
//    PWM period: lower peak current, less PSU ripple and less EMI.
//  * Compare registers are double-buffered by the RP2040, so updates never
//    produce runt pulses, and unchanged values are not rewritten at all.

uint16_t PwmBank::begin(uint32_t hz, const uint8_t invert[kCh]) {
  uint32_t sys = clock_get_hz(clk_sys);
  if (hz < 100) hz = 100;
  uint32_t cycles = sys / hz;
  uint32_t div = (cycles + 65534u) / 65535u;  // keep top+1 <= 65535 so 100 % fits in 16 bits
  if (div < 1) div = 1;
  if (div > 255) div = 255;
  uint32_t top = cycles / div - 1u;
  if (top > 65534u) top = 65534u;
  top_ = (uint16_t)top;
  actualHz_ = sys / (div * (top + 1u));

  bool ledOnA[8] = {};
  for (int i = 0; i < kCh; i++) {
    uint8_t pin = cfg::kLedPins[i];
    if (pwm_gpio_to_channel(pin) == PWM_CHAN_A) ledOnA[pwm_gpio_to_slice_num(pin)] = true;
  }

  bool polA[8] = {}, polB[8] = {};
  uint32_t sliceMask = 0;
  uint8_t ledSlices[8];
  int nLedSlices = 0;
  for (int i = 0; i < kCh; i++) {
    uint8_t pin = cfg::kLedPins[i];
    uint slice = pwm_gpio_to_slice_num(pin);
    bool chanB = pwm_gpio_to_channel(pin) == PWM_CHAN_B;
    endAligned_[i] = chanB && ledOnA[slice];
    bool hwInvert = endAligned_[i] != (invert[i] != 0);
    (chanB ? polB : polA)[slice] = hwInvert;
    if (!(sliceMask & (1u << slice))) ledSlices[nLedSlices++] = (uint8_t)slice;
    sliceMask |= 1u << slice;
  }
  if (cfg::kTftBacklight >= 0) sliceMask |= 1u << pwm_gpio_to_slice_num(cfg::kTftBacklight);

  // Stop the slices we own, reconfigure, preset compare values, then start
  // them together with staggered phases.
  pwm_set_mask_enabled(pwm_hw->en & ~sliceMask);
  for (uint slice = 0; slice < 8; slice++) {
    if (!(sliceMask & (1u << slice))) continue;
    pwm_config c = pwm_get_default_config();
    pwm_config_set_clkdiv_int(&c, div);
    pwm_config_set_wrap(&c, top_);
    pwm_config_set_output_polarity(&c, polA[slice], polB[slice]);
    pwm_init(slice, &c, false);
  }
  for (int i = 0; i < kCh; i++) {
    last_[i] = kUnknown;
    writeChannel(i, 0);
    gpio_set_function(cfg::kLedPins[i], GPIO_FUNC_PWM);
  }
  if (cfg::kTftBacklight >= 0) {
    lastBl_ = kUnknown;  // the next setBacklight() call restores the level
    pwm_set_gpio_level(cfg::kTftBacklight, 0);
    gpio_set_function(cfg::kTftBacklight, GPIO_FUNC_PWM);
  }
  for (int k = 0; k < nLedSlices; k++)
    pwm_set_counter(ledSlices[k], (uint16_t)((uint32_t)k * (top_ + 1u) / nLedSlices));
  pwm_set_mask_enabled(pwm_hw->en | sliceMask);
  return top_;
}

void PwmBank::writeChannel(int ch, uint16_t level) {
  if (level == last_[ch]) return;
  last_[ch] = level;
  uint32_t full = (uint32_t)top_ + 1u;
  if (level > full) level = (uint16_t)full;
  uint16_t hw = endAligned_[ch] ? (uint16_t)(full - level) : level;
  pwm_set_gpio_level(cfg::kLedPins[ch], hw);
}

void PwmBank::write(const uint16_t level[kCh]) {
  for (int i = 0; i < kCh; i++) writeChannel(i, level[i]);
}

void PwmBank::allOff() {
  for (int i = 0; i < kCh; i++) writeChannel(i, 0);
}

void PwmBank::setBacklight(float fraction) {
  if (cfg::kTftBacklight < 0) return;
  if (fraction < 0) fraction = 0;
  if (fraction > 1) fraction = 1;
  uint16_t lvl = (uint16_t)(fraction * ((uint32_t)top_ + 1u));
  if (lvl == lastBl_) return;
  lastBl_ = lvl;
  pwm_set_gpio_level(cfg::kTftBacklight, lvl);
}
