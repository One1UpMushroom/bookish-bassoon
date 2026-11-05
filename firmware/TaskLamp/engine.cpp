#include "engine.h"

#include <math.h>

static constexpr float kTwoPi = 6.2831853f;
static constexpr float kMasterTauMs = 60.f;     // knob smoothing time constant
static constexpr uint32_t kMinFlashPeriodMs = 40;  // caps strobe rate at 25 Hz

static inline float absf(float x) { return x < 0 ? -x : x; }

void LightEngine::begin(const EngineInput& in, uint32_t nowMs) {
  in_ = in;
  lastTick_ = nowMs;
  fxStart_ = nowMs;
  Lmaster_ = in.s.scene.bright * 0.001f;
  power_ = 0.f;  // soft start: ramps up over fadeMs, no inrush current step
  xfade_ = 1.f;
  from_ = last_ = Rgbww::zero();
  candle_ = candleTarget_ = 1.f;
  candleNext_ = 0;
  busy_ = true;
}

void LightEngine::apply(const EngineInput& in, uint32_t nowMs) {
  bool restart = in.rt.epoch != in_.rt.epoch || in.rt.preview != in_.rt.preview ||
                 in.s.scene.mode != in_.s.scene.mode;
  in_ = in;
  if (restart) {
    from_ = last_;  // crossfade from whatever is on the LEDs right now
    xfade_ = 0.f;
    fxStart_ = nowMs;
    candle_ = candleTarget_ = 1.f;
    candleNext_ = 0;
  }
  busy_ = true;
}

uint32_t LightEngine::rand32() {  // xorshift32: tiny, fast, good enough for flicker
  rng_ ^= rng_ << 13;
  rng_ ^= rng_ >> 17;
  rng_ ^= rng_ << 5;
  return rng_;
}

Rgbww hsvColor(const Settings& s, float hue, float sat) {
  float rgb[3];
  color::hsv(hue, sat, rgb);
  Rgbww c = Rgbww::zero();
  if (s.hw.pastelWhite) {
    // The "white part" of a pastel is produced far more efficiently (and with
    // better colour rendering) by the white LEDs than by mixing R+G+B.
    float w = rgb[0] < rgb[1] ? rgb[0] : rgb[1];
    if (rgb[2] < w) w = rgb[2];
    for (int i = 0; i < 3; i++) rgb[i] -= w;
    float ww, cw;
    color::cctSplit(s.scene.cct, s.hw.warmK, s.hw.coolK, false, ww, cw);
    c.v[CH_WW] = w * ww;
    c.v[CH_CW] = w * cw;
  }
  c.v[CH_R] = rgb[0];
  c.v[CH_G] = rgb[1];
  c.v[CH_B] = rgb[2];
  return c;
}

Rgbww sceneBaseColor(const Settings& s, Mode m) {
  const Scene& sc = s.scene;
  switch (m) {
    case Mode::Color:
      return hsvColor(s, sc.hue, sc.sat * 0.001f);
    case Mode::Mixer:
      return color::fromLevels(sc.mix);
    case Mode::White:
    default: {
      Rgbww c = Rgbww::zero();
      color::cctSplit(sc.cct, s.hw.warmK, s.hw.coolK, s.hw.whiteBoost,
                      c.v[CH_WW], c.v[CH_CW]);
      return c;
    }
  }
}

static inline uint32_t scaleTime(uint32_t ms, uint16_t speedPct) {
  return ms * 100u / (speedPct ? speedPct : 100u);
}

Rgbww LightEngine::sweepColor(uint32_t t, bool& animated) const {
  const SweepCfg& sw = in_.s.sweep;
  int n = sw.count;
  if (n <= 1) return color::fromLevels(sw.step[0].lvl);

  // A sweep is a list of segments: hold step A, then fade A -> B.
  int segs = (sw.loop == LOOP_PINGPONG) ? 2 * (n - 1) : n;
  auto seq = [&](int k) { return (sw.loop == LOOP_PINGPONG && k >= n) ? 2 * (n - 1) - k : k; };
  auto hold = [&](int i) { return scaleTime(sw.step[i].holdDs * 100u, sw.speed); };
  auto fade = [&](int i) { return scaleTime(sw.step[i].fadeDs * 100u, sw.speed); };

  uint32_t total = 0;
  int lastSeg = (sw.loop == LOOP_ONCE) ? n - 1 : segs;  // ONCE stops on the last step
  for (int k = 0; k < lastSeg; k++) total += hold(seq(k)) + fade(seq(k));
  if (total == 0) return color::fromLevels(sw.step[0].lvl);

  if (sw.loop == LOOP_ONCE) {
    if (t >= total) return color::fromLevels(sw.step[n - 1].lvl);  // finished: steady
  } else {
    t %= total;
  }
  animated = true;

  for (int k = 0; k < lastSeg; k++) {
    int a = seq(k);
    uint32_t h = hold(a), f = fade(a);
    if (t < h) return color::fromLevels(sw.step[a].lvl);
    t -= h;
    if (t < f) {
      int b = seq((k + 1) % segs);
      float x = (float)t / (float)f;
      if (sw.ease == EASE_SMOOTH) x = color::smoothstep(x);
      return color::lerp(color::fromLevels(sw.step[a].lvl), color::fromLevels(sw.step[b].lvl), x);
    }
    t -= f;
  }
  return color::fromLevels(sw.step[0].lvl);  // not reached
}

Rgbww LightEngine::flashColor(uint32_t t) const {
  const FlashCfg& f = in_.s.flash;
  uint32_t on = scaleTime(f.onMs, f.speed);
  uint32_t off = scaleTime(f.offMs, f.speed);
  uint32_t gap = scaleTime(f.gapMs, f.speed);
  if (on + off < kMinFlashPeriodMs) {  // hard cap on strobe frequency
    uint32_t p = on + off;
    on = on * kMinFlashPeriodMs / p;
    off = kMinFlashPeriodMs - on;
  }
  uint32_t burstLen = (on + off) * f.burst;
  t %= (burstLen + gap);
  bool lit = t < burstLen && (t % (on + off)) < on;
  return color::fromLevels(lit ? f.a : f.b);
}

float LightEngine::candleGain(uint32_t t, uint32_t dt) {
  const FxCfg& fx = in_.s.fx;
  uint16_t spd = fx.candleSpeed ? fx.candleSpeed : 100;
  if ((int32_t)(t - candleNext_) >= 0) {
    float r = (rand32() >> 8) * (1.f / 16777216.f);
    // r^2 makes small wobbles common and deep gutters rare, like a real flame.
    candleTarget_ = 1.f - fx.candleIntensity * 0.001f * r * r;
    float r2 = (rand32() >> 8) * (1.f / 16777216.f);
    candleNext_ = t + (uint32_t)((30.f + 150.f * r2) * 100.f / spd);
  }
  float tau = 50.f * 100.f / spd;
  candle_ += (candleTarget_ - candle_) * (dt / (tau + dt));
  return candle_;
}

Rgbww LightEngine::modeColor(Mode m, uint32_t t, uint32_t dt, bool& animated) {
  const FxCfg& fx = in_.s.fx;
  switch (m) {
    case Mode::Sweep:
      return sweepColor(t, animated);
    case Mode::Flash:
      animated = true;
      return flashColor(t);
    case Mode::Breathe: {
      animated = true;
      uint32_t period = fx.breathePeriodDs * 100u;
      float ph = (float)(t % period) / (float)period;
      float wave = 0.5f + 0.5f * cosf(kTwoPi * ph);  // starts at the top: seamless entry
      float lo = fx.breatheFloor * 0.001f;
      // Breathing in the lightness domain looks natural; linear would look "stuck bright".
      return sceneBaseColor(in_.s, (Mode)in_.s.scene.baseMode).scaled(color::lToY(lo + (1.f - lo) * wave));
    }
    case Mode::Rainbow: {
      animated = true;
      uint32_t period = fx.rainbowPeriodDs * 100u;
      float hue = 360.f * (float)(t % period) / (float)period;
      return hsvColor(in_.s, hue, fx.rainbowSat * 0.001f);
    }
    case Mode::Candle:
      animated = true;
      return sceneBaseColor(in_.s, (Mode)in_.s.scene.baseMode).scaled(candleGain(t, dt));
    default:
      return sceneBaseColor(in_.s, m);
  }
}

void LightEngine::tick(uint32_t nowMs, Rgbww& out) {
  uint32_t dt = nowMs - lastTick_;
  if (dt > 100) dt = 100;
  lastTick_ = nowMs;

  const Runtime& rt = in_.rt;
  bool previewing = rt.preview != PREVIEW_NONE;
  uint16_t fadeMs = in_.s.hw.fadeMs;
  float step = fadeMs ? (float)dt / fadeMs : 1.f;

  // On/off ramp (in lightness, so fades look even from start to finish).
  float powerTarget = (rt.on || previewing) ? 1.f : 0.f;
  if (power_ < powerTarget) power_ = power_ + step > powerTarget ? powerTarget : power_ + step;
  else if (power_ > powerTarget) power_ = power_ - step < powerTarget ? powerTarget : power_ - step;

  // Master brightness smoothing: knob detents become a smooth glide.
  float Ltarget = in_.s.scene.bright * 0.001f;
  Lmaster_ += (Ltarget - Lmaster_) * ((float)dt / (kMasterTauMs + dt));
  if (absf(Ltarget - Lmaster_) < 0.0005f) Lmaster_ = Ltarget;

  if (xfade_ < 1.f) xfade_ = xfade_ + step > 1.f ? 1.f : xfade_ + step;

  bool animated = false;
  Rgbww c = previewing ? color::fromLevels(rt.previewLvl)
                       : modeColor((Mode)in_.s.scene.mode, nowMs - fxStart_, dt, animated);
  if (xfade_ < 1.f) c = color::lerp(from_, c, color::smoothstep(xfade_));
  last_ = c;

  float L = (rt.preview == PREVIEW_RAW) ? 1.f : Lmaster_;
  L *= power_;

  bool sleepFading = false;
  if (rt.sleepEndMs && !previewing) {
    int32_t remain = (int32_t)(rt.sleepEndMs - nowMs);
    if (remain <= 0) {
      L = 0.f;
    } else if (rt.sleepFadeMs && (uint32_t)remain < rt.sleepFadeMs) {
      L *= (float)remain / (float)rt.sleepFadeMs;
      sleepFading = true;
    }
  }

  out = c.scaled(color::lToY(L));
  busy_ = animated || sleepFading || power_ != powerTarget || xfade_ < 1.f || Lmaster_ != Ltarget;
}
