#include "color.h"

#include <math.h>

namespace color {

// CIE L* uses a linear toe below L* = 8 so that very deep dimming stays smooth
// instead of collapsing into the first few PWM counts.
static constexpr float kKappa = 9.03296f;     // 903.3 / 100
static constexpr float kEpsilon = 0.0088565f; // (6/29)^3

float lToY(float L) {
  if (L <= 0.f) return 0.f;
  if (L >= 1.f) return 1.f;
  if (L <= 0.08f) return L / kKappa;
  float t = (L + 0.16f) / 1.16f;
  return t * t * t;
}

float yToL(float Y) {
  if (Y <= 0.f) return 0.f;
  if (Y >= 1.f) return 1.f;
  if (Y <= kEpsilon) return Y * kKappa;
  return 1.16f * cbrtf(Y) - 0.16f;
}

Rgbww fromLevels(const uint16_t lvl[kCh]) {
  Rgbww c;
  for (int i = 0; i < kCh; i++) c.v[i] = lToY(lvl[i] * 0.001f);
  return c;
}

void toLevels(const Rgbww& c, uint16_t lvl[kCh]) {
  for (int i = 0; i < kCh; i++) {
    float L = yToL(c.v[i]);
    lvl[i] = (uint16_t)lroundf(L * 1000.f);
  }
}

void hsv(float hueDeg, float sat, float rgb[3]) {
  float h = fmodf(hueDeg, 360.f);
  if (h < 0) h += 360.f;
  sat = clamp01(sat);
  float hp = h / 60.f;
  int sector = (int)hp;
  float f = hp - sector;
  float p = 1.f - sat;
  float q = 1.f - sat * f;
  float t = 1.f - sat * (1.f - f);
  switch (sector) {
    case 0: rgb[0] = 1; rgb[1] = t; rgb[2] = p; break;
    case 1: rgb[0] = q; rgb[1] = 1; rgb[2] = p; break;
    case 2: rgb[0] = p; rgb[1] = 1; rgb[2] = t; break;
    case 3: rgb[0] = p; rgb[1] = q; rgb[2] = 1; break;
    case 4: rgb[0] = t; rgb[1] = p; rgb[2] = 1; break;
    default: rgb[0] = 1; rgb[1] = p; rgb[2] = q; break;
  }
}

void cctSplit(uint16_t kelvin, uint16_t warmK, uint16_t coolK, bool boost,
              float& ww, float& cw) {
  if (warmK >= coolK) {  // misconfigured range: just use the warm channel
    ww = 1.f;
    cw = 0.f;
    return;
  }
  float mk = 1e6f / (float)kelvin;
  float mw = 1e6f / (float)warmK;
  float mc = 1e6f / (float)coolK;
  float t = clamp01((mw - mk) / (mw - mc));  // 0 = warm, 1 = cool
  ww = 1.f - t;
  cw = t;
  if (boost) {
    float m = ww > cw ? ww : cw;
    ww /= m;
    cw /= m;
  }
}

Rgbww lerp(const Rgbww& a, const Rgbww& b, float t) {
  Rgbww o;
  for (int i = 0; i < kCh; i++) o.v[i] = a.v[i] + (b.v[i] - a.v[i]) * t;
  return o;
}

float smoothstep(float t) {
  t = clamp01(t);
  return t * t * (3.f - 2.f * t);
}

}  // namespace color
