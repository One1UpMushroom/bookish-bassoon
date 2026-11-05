// Color math. Pure C++, no hardware dependencies (unit-tested on the host).
//
// Two "domains" are used throughout the firmware:
//   * perceptual  - what the user sets: 0..1000 permille of CIE lightness L*.
//                   Equal knob steps look like equal brightness steps.
//   * linear      - proportional to light output / LED current, 0.0 .. 1.0.
//                   All mixing and cross-fading happens here, because that is
//                   how light physically adds up.
#pragma once
#include <stdint.h>

constexpr int kCh = 5;
enum ChIdx : uint8_t { CH_R = 0, CH_G, CH_B, CH_WW, CH_CW };

struct Rgbww {
  float v[kCh];
  static Rgbww zero() { return Rgbww{{0, 0, 0, 0, 0}}; }
  Rgbww scaled(float k) const {
    Rgbww o;
    for (int i = 0; i < kCh; i++) o.v[i] = v[i] * k;
    return o;
  }
};

namespace color {

// CIE 1976 lightness <-> relative luminance, both normalised to 0..1.
float lToY(float L);
float yToL(float Y);

inline float clamp01(float x) { return x < 0.f ? 0.f : (x > 1.f ? 1.f : x); }

// Perceptual permille levels (0..1000) -> linear light.
Rgbww fromLevels(const uint16_t lvl[kCh]);
// Linear light -> perceptual permille levels (used by "capture current color").
void toLevels(const Rgbww& c, uint16_t lvl[kCh]);

// Hue in degrees (any value, wraps), saturation 0..1, value 1. Output linear RGB.
void hsv(float hueDeg, float sat, float rgb[3]);

// Split a colour temperature into warm/cool channel weights. Interpolates in
// mired space (perceptually even). boost=false keeps total flux constant
// (ww+cw = 1); boost=true scales so the stronger channel is at 1 (max output).
void cctSplit(uint16_t kelvin, uint16_t warmK, uint16_t coolK, bool boost,
              float& ww, float& cw);

Rgbww lerp(const Rgbww& a, const Rgbww& b, float t);
float smoothstep(float t);

}  // namespace color
