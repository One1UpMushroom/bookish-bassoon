#include "input.h"

void Gestures::push(Ev t, int16_t d, uint8_t accel) {
  if (count_ == sizeof(q_) / sizeof(q_[0])) return;  // drop on overflow
  InputEvent& e = q_[(head_ + count_) % (sizeof(q_) / sizeof(q_[0]))];
  e.type = t;
  e.src = src_;
  e.delta = d;
  e.accel = accel;
  count_++;
}

bool Gestures::next(InputEvent& e) {
  if (!count_) return false;
  e = q_[head_];
  head_ = (head_ + 1) % (sizeof(q_) / sizeof(q_[0]));
  count_--;
  return true;
}

uint8_t Gestures::accel(uint32_t nowMs, int32_t detents) {
  uint32_t dt = nowMs - lastTurn_;
  lastTurn_ = nowMs;
  if (detents < 0) detents = -detents;
  if (dt > 250) {
    rate_ = 0;  // a pause resets to fine control
    return 1;
  }
  float inst = detents * 1000.f / (dt ? dt : 1);
  rate_ = rate_ * 0.6f + inst * 0.4f;
  if (rate_ < 8) return 1;
  if (rate_ < 18) return 4;
  if (rate_ < 35) return 10;
  return 25;
}

void Gestures::update(uint32_t nowMs, bool pressed, int32_t delta) {
  // Debounce: accept a new switch state only after two identical samples.
  bool stable = (pressed == raw_);
  raw_ = pressed;

  if (stable && pressed && !down_) {  // press edge
    down_ = true;
    downAt_ = nowMs;
    longFired_ = false;
    turnedWhileDown_ = false;
    if (clickPending_ && nowMs - upAt_ <= kDoubleMs) secondPress_ = true;
  } else if (stable && !pressed && down_) {  // release edge
    down_ = false;
    upAt_ = nowMs;
    if (longFired_ || turnedWhileDown_) {
      clickPending_ = secondPress_ = false;
    } else if (secondPress_) {
      push(Ev::DoubleClick);
      clickPending_ = secondPress_ = false;
    } else if (dblEnabled_) {
      clickPending_ = true;  // wait to see whether a second click follows
    } else {
      push(Ev::Click);
    }
  }

  if (delta != 0) {
    if (delta > 32767) delta = 32767;
    if (delta < -32767) delta = -32767;
    uint8_t a = accel(nowMs, delta);
    if (down_) {
      turnedWhileDown_ = true;
      push(Ev::PressTurn, (int16_t)delta, a);
    } else {
      push(Ev::Turn, (int16_t)delta, a);
    }
  }

  if (down_ && !longFired_ && !turnedWhileDown_ && nowMs - downAt_ >= kLongMs) {
    longFired_ = true;
    clickPending_ = secondPress_ = false;
    push(Ev::LongPress);
  }

  if (clickPending_ && !down_ && nowMs - upAt_ > kDoubleMs) {
    clickPending_ = false;
    push(Ev::Click);
  }
}
