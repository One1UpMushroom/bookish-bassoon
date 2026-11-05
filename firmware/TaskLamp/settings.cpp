#include "settings.h"

#include <string.h>

static const char* const kModeNames[] = {"White",   "Color",   "Mixer",  "Sweep",
                                         "Flash",   "Breathe", "Rainbow", "Candle"};

const char* modeName(Mode m) {
  uint8_t i = (uint8_t)m;
  return i < (uint8_t)Mode::Count ? kModeNames[i] : "?";
}

namespace settings {

static void setLv(uint16_t* d, uint16_t r, uint16_t g, uint16_t b, uint16_t ww, uint16_t cw) {
  d[0] = r; d[1] = g; d[2] = b; d[3] = ww; d[4] = cw;
}

void defaults(Settings& s) {
  memset(&s, 0, sizeof(s));  // also zeroes padding so the CRC is deterministic
  s.magic = kSettingsMagic;
  s.version = kSettingsVersion;
  s.size = sizeof(Settings);

  Scene& sc = s.scene;
  sc.mode = (uint8_t)Mode::White;
  sc.baseMode = (uint8_t)Mode::White;
  sc.bright = 600;
  sc.cct = 4000;
  sc.hue = 30;
  sc.sat = 1000;
  setLv(sc.mix, 0, 0, 0, 600, 600);
  for (int i = 0; i < kFavorites; i++) s.fav[i] = sc;  // empty slots still hold a valid scene

  // Sweep: warm -> cool -> soft rose, looping.
  SweepCfg& sw = s.sweep;
  sw.count = 3;
  sw.loop = LOOP_REPEAT;
  sw.ease = EASE_SMOOTH;
  sw.speed = 100;
  setLv(sw.step[0].lvl, 0, 0, 0, 1000, 0);
  setLv(sw.step[1].lvl, 0, 0, 0, 200, 1000);
  setLv(sw.step[2].lvl, 900, 300, 600, 500, 0);
  for (int i = 0; i < kMaxSweepSteps; i++) {
    sw.step[i].holdDs = 50;
    sw.step[i].fadeDs = 30;
  }

  // Flash: white double-flash every second.
  FlashCfg& f = s.flash;
  setLv(f.a, 0, 0, 0, 1000, 1000);
  setLv(f.b, 0, 0, 0, 0, 0);
  f.onMs = 60;
  f.offMs = 120;
  f.gapMs = 800;
  f.burst = 2;
  f.speed = 100;

  FxCfg& fx = s.fx;
  fx.breathePeriodDs = 60;
  fx.breatheFloor = 250;
  fx.rainbowPeriodDs = 300;
  fx.rainbowSat = 1000;
  fx.candleIntensity = 450;
  fx.candleSpeed = 100;

  HwCfg& hw = s.hw;
  hw.pwmHz = 2000;
  hw.budgetmA = 0;
  for (int i = 0; i < kCh; i++) {
    hw.chmA[i] = 0;
    hw.chMin[i] = 0;
    hw.chTrim[i] = 1000;
    hw.chInvert[i] = 0;
  }
  hw.whiteBoost = 1;
  hw.pastelWhite = 1;
  hw.knobReverse = 0;
  hw.warmK = 2200;
  hw.coolK = 6500;
  hw.fadeMs = 500;

  s.ui.dispBright = 800;
  s.ui.dispTimeoutS = 60;
  s.ui.dispFollow = 1;
  s.ui.knobGlow = 1;

  seal(s);
}

template <typename T>
static void clampT(T& v, T lo, T hi) {
  if (v < lo) v = lo;
  if (v > hi) v = hi;
}

static void sanitizeLevels(uint16_t* l) {
  for (int i = 0; i < kCh; i++) clampT<uint16_t>(l[i], 0, 1000);
}

static void sanitizeScene(Scene& sc, const HwCfg& hw) {
  if (sc.mode >= (uint8_t)Mode::Count) sc.mode = (uint8_t)Mode::White;
  if (!isBaseMode((Mode)sc.baseMode)) sc.baseMode = (uint8_t)Mode::White;
  clampT<uint16_t>(sc.bright, 1, 1000);
  clampT<uint16_t>(sc.cct, hw.warmK, hw.coolK);
  sc.hue %= 360;
  clampT<uint16_t>(sc.sat, 0, 1000);
  sanitizeLevels(sc.mix);
}

void sanitize(Settings& s) {
  HwCfg& hw = s.hw;
  clampT<uint16_t>(hw.pwmHz, 200, 20000);
  clampT<uint16_t>(hw.budgetmA, 0, 30000);
  for (int i = 0; i < kCh; i++) {
    clampT<uint16_t>(hw.chmA[i], 0, 10000);
    clampT<uint16_t>(hw.chMin[i], 0, 5000);
    clampT<uint16_t>(hw.chTrim[i], 100, 1000);
    hw.chInvert[i] = hw.chInvert[i] ? 1 : 0;
  }
  hw.whiteBoost = hw.whiteBoost ? 1 : 0;
  hw.pastelWhite = hw.pastelWhite ? 1 : 0;
  hw.knobReverse = hw.knobReverse ? 1 : 0;
  clampT<uint16_t>(hw.warmK, 1500, 4000);
  clampT<uint16_t>(hw.coolK, 4500, 10000);
  clampT<uint16_t>(hw.fadeMs, 0, 5000);

  sanitizeScene(s.scene, hw);
  for (int i = 0; i < kFavorites; i++) sanitizeScene(s.fav[i], hw);
  s.favUsed &= (1u << kFavorites) - 1;

  SweepCfg& sw = s.sweep;
  clampT<uint8_t>(sw.count, 1, kMaxSweepSteps);
  if (sw.loop >= LOOP_COUNT) sw.loop = LOOP_REPEAT;
  if (sw.ease >= EASE_COUNT) sw.ease = EASE_SMOOTH;
  clampT<uint16_t>(sw.speed, 25, 400);
  for (int i = 0; i < kMaxSweepSteps; i++) {
    sanitizeLevels(sw.step[i].lvl);
    clampT<uint16_t>(sw.step[i].holdDs, 0, 3000);
    clampT<uint16_t>(sw.step[i].fadeDs, 0, 3000);
  }

  FlashCfg& f = s.flash;
  sanitizeLevels(f.a);
  sanitizeLevels(f.b);
  clampT<uint16_t>(f.onMs, 20, 2000);
  clampT<uint16_t>(f.offMs, 20, 2000);
  clampT<uint16_t>(f.gapMs, 0, 10000);
  clampT<uint16_t>(f.speed, 25, 400);
  clampT<uint16_t>(f.burst, 1, 10);

  FxCfg& fx = s.fx;
  clampT<uint16_t>(fx.breathePeriodDs, 10, 600);
  clampT<uint16_t>(fx.breatheFloor, 0, 900);
  clampT<uint16_t>(fx.rainbowPeriodDs, 10, 6000);
  clampT<uint16_t>(fx.rainbowSat, 0, 1000);
  clampT<uint16_t>(fx.candleIntensity, 0, 1000);
  clampT<uint16_t>(fx.candleSpeed, 25, 400);

  clampT<uint16_t>(s.ui.dispBright, 50, 1000);
  clampT<uint16_t>(s.ui.dispTimeoutS, 0, 600);
  s.ui.dispFollow = s.ui.dispFollow ? 1 : 0;
  s.ui.knobGlow = s.ui.knobGlow ? 1 : 0;
}

uint32_t crc32(const void* data, size_t len) {
  // Bitwise CRC-32 (IEEE). Only runs on load/save, so no table needed.
  const uint8_t* p = (const uint8_t*)data;
  uint32_t crc = 0xFFFFFFFFu;
  while (len--) {
    crc ^= *p++;
    for (int k = 0; k < 8; k++) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
  }
  return ~crc;
}

uint32_t computeCrc(const Settings& s) { return crc32(&s, offsetof(Settings, crc)); }

void seal(Settings& s) { s.crc = computeCrc(s); }

bool valid(const Settings& s) {
  return s.magic == kSettingsMagic && s.version == kSettingsVersion &&
         s.size == sizeof(Settings) && s.crc == computeCrc(s);
}

bool SaveScheduler::due(uint32_t nowMs, uint32_t currentCrc, uint32_t delayMs) {
  if (!pending_) return false;
  if ((uint32_t)(nowMs - lastChange_) < delayMs) return false;
  if (currentCrc == savedCrc_) {  // changed and changed back: nothing to write
    pending_ = false;
    return false;
  }
  return true;
}

}  // namespace settings
