// User interface: home screen, menu system, gestures -> actions, display
// power management. Runs on core 0. Pure C++ apart from the Painter it draws
// through, so the whole UI can be exercised by host tests.
#pragma once
#include <stdint.h>

#include "engine.h"
#include "input.h"
#include "painter.h"
#include "settings.h"

// What core 1 reports back about the light actually being produced.
struct LampStatus {
  float lin[kCh];  // delivered linear drive per channel
  float mA;        // estimated LED current
  float masterL;   // smoothed master lightness
  bool limited;    // power budget active
};

enum class Fmt : uint8_t { Permille, Kelvin, Degree, Deci, Ms, Int, MilliAmp, Hz, Pct, MinDuty, Sec };
void formatValue(Fmt f, uint16_t v, char* buf, int n);

class Ui;
struct Menu;
using Builder = void (*)(Ui&, Menu&, int arg);
using Action = void (*)(Ui&, int arg);

struct Item {
  enum Kind : uint8_t { Back, Sub, Act, Num, Enum };
  enum Flag : uint8_t {
    F_EPOCH = 1,    // changing it restarts the effect with a crossfade
    F_REBUILD = 2,  // menu contents depend on it: rebuild after editing
    F_WRAP = 4,     // value wraps around (hue)
    F_NOSAVE = 8,   // runtime-only value, do not persist
  };
  Kind kind;
  uint8_t flags;
  char label[18];
  char info[10];  // value text shown right of Sub/Act items
  // Num
  uint16_t* v16;
  uint16_t lo, hi, step;
  Fmt fmt;
  // Enum
  uint8_t* v8;
  const char* const* names;
  uint8_t count;
  // Sub / Act / change hook
  Builder sub;
  Action act;
  Action change;  // called after the value changed
  int16_t arg;
};

constexpr int kMaxItems = 14;
constexpr int kRowsVisible = 6;

struct Menu {
  char title[24];
  Item items[kMaxItems];
  uint8_t n;
  int8_t focus;          // initial selection when first opened, -1 = top
  uint16_t* previewLvl;  // colour to show on the lamp while this menu is open
  int8_t calCh;          // channel being calibrated (raw preview), -1 = none

  void reset();
  Item& add(Item::Kind k, const char* label);
  Item& num(const char* label, uint16_t* v, uint16_t lo, uint16_t hi, uint16_t step, Fmt f,
            uint8_t flags = 0);
  Item& enm(const char* label, uint8_t* v, const char* const* names, uint8_t count,
            uint8_t flags = 0);
  Item& sub(const char* label, Builder b, int arg = 0, const char* info = nullptr);
  Item& act(const char* label, Action a, int arg = 0, const char* info = nullptr);
  Item& back(const char* label = "< Back");
};

class Ui {
 public:
  void begin(Settings* s, Runtime* rt, uint32_t nowMs);
  void handle(const InputEvent& e, uint32_t nowMs);
  void update(uint32_t nowMs, const LampStatus& st);
  void draw(Painter& p);

  // ---- queries for the application loop ----
  bool takeRedraw() { bool r = redraw_; redraw_ = false; return r; }
  bool takeSettingsChanged() { bool r = settingsChanged_; settingsChanged_ = false; return r; }
  bool takeRuntimeChanged() { bool r = runtimeChanged_; runtimeChanged_ = false; return r; }
  bool wantDoubleClick() const { return screen_ == Screen::Home; }
  bool displayAsleep() const { return asleep_; }
  float backlight() const;      // 0..1 linear
  uint32_t knobGlow() const;    // 0xRRGGBB for the encoder NeoPixel
  void setEncoderMissing(bool m) { if (m != encMissing_) { encMissing_ = m; redraw_ = true; } }
  void toast(const char* msg);

  // ---- used by menu builders / actions (ui.cpp) ----
  enum class Screen : uint8_t { Home, Menu };
  void push(Builder b, int arg = 0);
  void pop();
  void goHome();
  void rebuild();
  void settingsChanged() { settingsChanged_ = true; redraw_ = true; }
  void bumpEpoch() { rt->epoch++; runtimeChanged_ = true; }
  void setPower(bool on);
  void refreshPreview();

  Settings* s = nullptr;
  Runtime* rt = nullptr;
  uint32_t now = 0;
  uint8_t sleepSel = 0;    // index into the sleep timer choices
  uint16_t calTest = 1;    // test level used while calibrating a channel

 private:
  struct Frame {
    Builder b;
    int16_t arg;
    uint8_t sel, top;
  };
  struct Quick {
    const char* label;
    uint16_t* v;
    uint16_t lo, hi, step;
    Fmt fmt;
    bool wrap;
  };

  void homeEvent(const InputEvent& e);
  void menuEvent(const InputEvent& e);
  void adjust(Item& it, int delta, int accel);
  void valueChanged(Item& it);
  bool quickParam(Quick& q);
  void nextFavorite();
  void drawHome(Painter& p);
  void drawMenu(Painter& p);
  void itemValue(const Item& it, char* buf, int n) const;

  Screen screen_ = Screen::Home;
  Menu menu_{};
  Frame stack_[6]{};
  uint8_t depth_ = 0;
  bool editing_ = false;
  uint16_t editOrig_ = 0;
  bool quickActive_ = false;
  uint8_t favIdx_ = kFavorites - 1;  // last favourite recalled by double-click

  LampStatus st_{};
  float drawnLin_[kCh] = {};
  float drawnmA_ = -1;
  bool drawnLimited_ = false;
  uint32_t lastLive_ = 0;
  int32_t drawnSleepMin_ = -1;

  uint32_t lastInput_ = 0;
  bool dimmed_ = false, asleep_ = false;
  bool encMissing_ = false;

  char toast_[20] = {};
  uint32_t toastUntil_ = 0;

  bool redraw_ = true, settingsChanged_ = false, runtimeChanged_ = false;
};
