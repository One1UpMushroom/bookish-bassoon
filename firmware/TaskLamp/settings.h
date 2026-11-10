// Persistent settings. Plain-old-data so it can be CRC'd, copied between the
// two cores, and written to flash as one blob. Pure C++ (host-testable).
#pragma once
#include <stddef.h>
#include <stdint.h>

#include "color.h"

enum class Mode : uint8_t {
  White = 0,  // colour temperature + brightness (warm/cool channels)
  Color,      // hue / saturation + brightness (RGB, pastels via white LEDs)
  Mixer,      // all five channels set independently
  Sweep,      // user-programmed sequence of colours with fades and holds
  Flash,      // programmable flash / strobe between two colours
  Breathe,    // slow brightness "breathing" of the base colour
  Rainbow,    // continuous hue rotation
  Candle,     // flickering candle effect on the base colour
  Count
};
const char* modeName(Mode m);
inline bool isBaseMode(Mode m) { return m <= Mode::Mixer; }

enum SweepLoop : uint8_t { LOOP_REPEAT = 0, LOOP_PINGPONG, LOOP_ONCE, LOOP_COUNT };
enum SweepEase : uint8_t { EASE_LINEAR = 0, EASE_SMOOTH, EASE_COUNT };

constexpr int kMaxSweepSteps = 8;
constexpr int kFavorites = 6;

// Everything needed to reproduce "the current look" (what a favourite stores).
struct Scene {
  uint8_t mode;      // Mode
  uint8_t baseMode;  // White/Color/Mixer: colour used by Breathe and Candle
  uint16_t bright;   // master brightness, perceptual permille (1..1000)
  uint16_t cct;      // White mode colour temperature, Kelvin
  uint16_t hue;      // Color mode hue, degrees 0..359
  uint16_t sat;      // Color mode saturation, permille
  uint16_t mix[kCh]; // Mixer mode per-channel levels, perceptual permille
};

struct SweepStep {
  uint16_t lvl[kCh];  // perceptual permille per channel
  uint16_t holdDs;    // hold time, 0.1 s units
  uint16_t fadeDs;    // fade time to the next step, 0.1 s units
};

struct SweepCfg {
  uint8_t count;   // number of active steps, 1..kMaxSweepSteps
  uint8_t loop;    // SweepLoop
  uint8_t ease;    // SweepEase
  uint8_t pad;
  uint16_t speed;  // percent, 25..400 (scales all times)
  SweepStep step[kMaxSweepSteps];
};

struct FlashCfg {
  uint16_t a[kCh];  // "on" colour
  uint16_t b[kCh];  // "off"/background colour (all zero = dark)
  uint16_t onMs, offMs, gapMs;
  uint16_t speed;   // percent, 25..400
  uint16_t burst;   // flashes per burst, 1..10
};

struct FxCfg {
  uint16_t breathePeriodDs;  // 0.1 s units
  uint16_t breatheFloor;     // permille of lightness at the bottom of a breath
  uint16_t rainbowPeriodDs;  // 0.1 s per full hue revolution
  uint16_t rainbowSat;       // permille
  uint16_t candleIntensity;  // permille
  uint16_t candleSpeed;      // percent
};

// Hardware calibration: describes your drivers, LEDs and power supply.
struct HwCfg {
  uint16_t pwmHz;        // PWM carrier frequency (match your driver's DIM spec)
  uint16_t budgetmA;     // total LED current budget, 0 = no limit
  uint16_t chmA[kCh];    // current drawn by each channel at 100% duty, 0 = unknown
  uint16_t chMin[kCh];   // duty floor in 0.001% units (removes the dead band)
  uint16_t chTrim[kCh];  // per-channel ceiling, permille (white balance)
  uint8_t chInvert[kCh]; // 1 = active-low driver input
  uint8_t whiteBoost;    // White mode: 1 = max output, 0 = constant flux
  uint8_t pastelWhite;   // Color mode: route the white part of pastels to W LEDs
  uint8_t knobReverse;
  uint8_t pad;
  uint16_t warmK, coolK; // colour temperature of the warm and cool LEDs
  uint16_t fadeMs;       // transition time for on/off and mode changes
};

struct UiCfg {
  uint16_t dispBright;   // display backlight, perceptual permille
  uint16_t dispTimeoutS; // dim/sleep the display after this long idle, 0 = never
  uint8_t dispFollow;    // backlight follows lamp brightness (less glare at night)
  uint8_t knobGlow;      // encoder NeoPixel glows faintly while lamp is off
  uint16_t pad;
};

constexpr uint32_t kSettingsMagic = 0x4C414D50;  // "LAMP"
constexpr uint16_t kSettingsVersion = 1;

struct Settings {
  uint32_t magic;
  uint16_t version;
  uint16_t size;
  Scene scene;
  Scene fav[kFavorites];
  uint8_t favUsed;  // bitmask of favourite slots that hold a scene
  uint8_t pad[3];
  SweepCfg sweep;
  FlashCfg flash;
  FxCfg fx;
  HwCfg hw;
  UiCfg ui;
  uint32_t crc;  // must stay last
};

namespace settings {

void defaults(Settings& s);
// Clamp every field into its legal range. Run after loading so that a blob
// from an older firmware or a bit-flip can never produce dangerous output.
void sanitize(Settings& s);
uint32_t crc32(const void* data, size_t len);
uint32_t computeCrc(const Settings& s);
void seal(Settings& s);  // fills in crc
bool valid(const Settings& s);

// Delays flash writes until the user has stopped fiddling and skips writes
// whose content is identical to what is already stored (flash wear).
class SaveScheduler {
 public:
  void markSaved(uint32_t crc) { savedCrc_ = crc; pending_ = false; }
  void touch(uint32_t nowMs) { lastChange_ = nowMs; pending_ = true; }
  // Cheap test to run first: has the waiting time passed? (No CRC needed.)
  bool waited(uint32_t nowMs, uint32_t delayMs) const {
    return pending_ && (uint32_t)(nowMs - lastChange_) >= delayMs;
  }
  // Returns true when a write should happen now.
  bool due(uint32_t nowMs, uint32_t currentCrc, uint32_t delayMs);
  bool pending() const { return pending_; }

 private:
  uint32_t savedCrc_ = 0;
  uint32_t lastChange_ = 0;
  bool pending_ = false;
};

}  // namespace settings
