// Gesture decoding for a rotary encoder with a push switch. Pure C++.
//
// Raw samples (switch state + detent delta) go in, high-level events come out:
//   Turn        - knob rotated (with an acceleration multiplier)
//   PressTurn   - knob rotated while the switch is held (no click is emitted)
//   Click       - short press
//   DoubleClick - two short presses (only when enabled, to keep clicks snappy)
//   LongPress   - held >= kLongMs; fires while still held for instant feedback
#pragma once
#include <stdint.h>

enum class Ev : uint8_t { None, Turn, PressTurn, Click, DoubleClick, LongPress };

struct InputEvent {
  Ev type;
  uint8_t src;    // 0 = main knob, 1 = optional second knob
  int16_t delta;  // detents (signed) for Turn / PressTurn
  uint8_t accel;  // multiplier for numeric adjustments (1 = fine)
};

class Gestures {
 public:
  static constexpr uint32_t kLongMs = 600;
  static constexpr uint32_t kDoubleMs = 300;

  explicit Gestures(uint8_t src = 0) : src_(src) {}
  void enableDoubleClick(bool en) { dblEnabled_ = en; }
  // Feed one sample. `pressed` is the raw (possibly bouncy) switch state.
  void update(uint32_t nowMs, bool pressed, int32_t delta);
  bool next(InputEvent& e);
  bool held() const { return down_; }

 private:
  void push(Ev t, int16_t d = 0, uint8_t accel = 1);
  uint8_t accel(uint32_t nowMs, int32_t detents);

  uint8_t src_;
  bool dblEnabled_ = false;
  bool raw_ = false, down_ = false;
  bool longFired_ = false, turnedWhileDown_ = false;
  bool clickPending_ = false, secondPress_ = false;
  uint32_t downAt_ = 0, upAt_ = 0;
  uint32_t lastTurn_ = 0;
  float rate_ = 0;  // detents per second, smoothed

  InputEvent q_[8];
  uint8_t head_ = 0, count_ = 0;
};
