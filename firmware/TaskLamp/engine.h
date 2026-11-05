// Light engine: turns settings + elapsed time into five linear channel values.
// Pure C++ (host-testable). Runs on core 1 at 250 Hz while anything moves and
// 50 Hz while the light is steady.
#pragma once
#include <stdint.h>

#include "color.h"
#include "settings.h"

enum PreviewMode : uint8_t {
  PREVIEW_NONE = 0,
  PREVIEW_COLOR,  // show previewLvl scaled by master brightness (colour editors)
  PREVIEW_RAW,    // show previewLvl at face value (channel calibration)
};

// Volatile, non-persistent state owned by the UI.
struct Runtime {
  uint8_t on;
  uint8_t preview;           // PreviewMode
  uint16_t previewLvl[kCh];  // perceptual permille
  uint32_t epoch;            // bumped on mode change / favourite recall -> crossfade
  uint32_t sleepEndMs;       // sleep timer deadline (millis), 0 = none
  uint32_t sleepFadeMs;      // length of the fade-out that ends at sleepEndMs
};

struct EngineInput {
  Settings s;
  Runtime rt;
};

// Colour of a base mode (White / Color / Mixer) at full brightness, linear.
// Shared by the engine and the UI ("capture current light").
Rgbww sceneBaseColor(const Settings& s, Mode m);
Rgbww hsvColor(const Settings& s, float hueDeg, float sat);

class LightEngine {
 public:
  // Starts dark and fades in to the configured scene (soft start).
  void begin(const EngineInput& in, uint32_t nowMs);
  void apply(const EngineInput& in, uint32_t nowMs);
  // Produces linear 0..1 drive per channel (before calibration / power cap).
  void tick(uint32_t nowMs, Rgbww& out);
  // True while the output is changing and needs fast ticks.
  bool busy() const { return busy_; }
  // Current (smoothed) master lightness 0..1, for the UI.
  float masterL() const { return Lmaster_; }

 private:
  Rgbww modeColor(Mode m, uint32_t t, uint32_t dt, bool& animated);
  Rgbww sweepColor(uint32_t t, bool& animated) const;
  Rgbww flashColor(uint32_t t) const;
  float candleGain(uint32_t nowMs, uint32_t dt);
  uint32_t rand32();

  EngineInput in_{};
  uint32_t lastTick_ = 0;
  uint32_t fxStart_ = 0;
  float Lmaster_ = 0.f;  // smoothed master lightness
  float power_ = 0.f;    // on/off ramp, 0..1 in the lightness domain
  float xfade_ = 1.f;    // crossfade progress 0..1
  Rgbww from_ = Rgbww::zero();
  Rgbww last_ = Rgbww::zero();
  float candle_ = 1.f, candleTarget_ = 1.f;
  uint32_t candleNext_ = 0;
  uint32_t rng_ = 0x1234567u;
  bool busy_ = true;
};
