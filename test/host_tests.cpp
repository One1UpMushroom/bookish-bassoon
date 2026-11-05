// Host-side unit tests for the hardware-independent firmware modules.
// Build & run:  make -C test
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <string>
#include <vector>

#include "color.h"
#include "engine.h"
#include "input.h"
#include "output.h"
#include "settings.h"
#include "ui.h"

static int gFails = 0, gChecks = 0;
#define CHECK(cond)                                                     \
  do {                                                                  \
    gChecks++;                                                          \
    if (!(cond)) {                                                      \
      gFails++;                                                         \
      printf("  FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);          \
    }                                                                   \
  } while (0)
#define NEAR(a, b, eps) CHECK(fabs((double)(a) - (double)(b)) <= (eps))
#define TEST(name) static void name()
#define RUN(name)              \
  do {                         \
    printf("%s\n", #name);     \
    name();                    \
  } while (0)

// ---------------------------------------------------------------------------
TEST(color_lightness) {
  NEAR(color::lToY(0), 0, 1e-9);
  NEAR(color::lToY(1), 1, 1e-6);
  NEAR(color::lToY(0.5f), 0.1842f, 1e-3);  // L*=50 -> Y=18.4 %
  // continuous at the toe
  NEAR(color::lToY(0.0799f), color::lToY(0.0801f), 1e-4);
  for (float L = 0; L <= 1.0f; L += 0.01f) NEAR(color::yToL(color::lToY(L)), L, 1e-4);
  // monotonic
  float prev = -1;
  for (int i = 0; i <= 1000; i++) {
    float y = color::lToY(i * 0.001f);
    CHECK(y >= prev);
    prev = y;
  }
  // deep dimming: the lowest knob step is a tiny but non-zero output
  float y1 = color::lToY(0.001f);
  CHECK(y1 > 0 && y1 < 0.0002f);
}

TEST(color_hsv_cct) {
  float rgb[3];
  color::hsv(0, 1, rgb);
  NEAR(rgb[0], 1, 1e-6); NEAR(rgb[1], 0, 1e-6); NEAR(rgb[2], 0, 1e-6);
  color::hsv(120, 1, rgb);
  NEAR(rgb[0], 0, 1e-6); NEAR(rgb[1], 1, 1e-6); NEAR(rgb[2], 0, 1e-6);
  color::hsv(240, 1, rgb);
  NEAR(rgb[0], 0, 1e-6); NEAR(rgb[1], 0, 1e-6); NEAR(rgb[2], 1, 1e-6);
  color::hsv(-120, 1, rgb);  // wraps
  NEAR(rgb[2], 1, 1e-6);
  color::hsv(77, 0, rgb);
  NEAR(rgb[0], 1, 1e-6); NEAR(rgb[1], 1, 1e-6); NEAR(rgb[2], 1, 1e-6);

  float ww, cw;
  color::cctSplit(2200, 2200, 6500, true, ww, cw);
  NEAR(ww, 1, 1e-6); NEAR(cw, 0, 1e-6);
  color::cctSplit(6500, 2200, 6500, true, ww, cw);
  NEAR(ww, 0, 1e-6); NEAR(cw, 1, 1e-6);
  color::cctSplit(3500, 2200, 6500, true, ww, cw);
  NEAR(ww > cw ? ww : cw, 1, 1e-6);
  color::cctSplit(3500, 2200, 6500, false, ww, cw);
  NEAR(ww + cw, 1, 1e-6);
  CHECK(ww > 0 && cw > 0);
  color::cctSplit(1000, 2200, 6500, false, ww, cw);  // out of range clamps
  NEAR(ww, 1, 1e-6);
}

// ---------------------------------------------------------------------------
TEST(settings_basics) {
  Settings s;
  settings::defaults(s);
  CHECK(settings::valid(s));
  uint32_t crc = s.crc;
  settings::sanitize(s);
  settings::seal(s);
  CHECK(s.crc == crc);  // defaults are already in range

  Settings t = s;
  ((uint8_t*)&t)[100] ^= 0x40;
  CHECK(!settings::valid(t));

  // Garbage in -> everything in range out.
  srand(7);
  for (int round = 0; round < 200; round++) {
    for (size_t i = 0; i < sizeof(t); i++) ((uint8_t*)&t)[i] = (uint8_t)rand();
    settings::sanitize(t);
    CHECK(t.scene.mode < (uint8_t)Mode::Count);
    CHECK(isBaseMode((Mode)t.scene.baseMode));
    CHECK(t.scene.bright >= 1 && t.scene.bright <= 1000);
    CHECK(t.scene.hue < 360);
    CHECK(t.sweep.count >= 1 && t.sweep.count <= kMaxSweepSteps);
    CHECK(t.hw.pwmHz >= 200 && t.hw.pwmHz <= 20000);
    CHECK(t.flash.onMs >= 20 && t.flash.burst >= 1);
    CHECK(t.hw.warmK < t.hw.coolK);
    CHECK(t.scene.cct >= t.hw.warmK && t.scene.cct <= t.hw.coolK);
    for (int c = 0; c < kCh; c++) CHECK(t.scene.mix[c] <= 1000 && t.hw.chTrim[c] >= 100);
  }
}

TEST(settings_save_scheduler) {
  settings::SaveScheduler sch;
  sch.markSaved(111);
  CHECK(!sch.due(0, 222, 5000));
  sch.touch(1000);
  CHECK(!sch.due(5999, 222, 5000));  // still being edited
  CHECK(sch.due(6000, 222, 5000));
  sch.markSaved(222);
  CHECK(!sch.pending());
  sch.touch(7000);  // changed, then changed back
  CHECK(!sch.due(13000, 222, 5000));
  CHECK(!sch.pending());
}

// ---------------------------------------------------------------------------
static EngineInput makeInput() {
  EngineInput in;
  memset(&in, 0, sizeof(in));
  settings::defaults(in.s);
  in.rt.on = 1;
  return in;
}

static Rgbww run(LightEngine& e, uint32_t from, uint32_t to, uint32_t step = 4) {
  Rgbww out = Rgbww::zero();
  for (uint32_t t = from; t <= to; t += step) e.tick(t, out);
  return out;
}

static float sum(const Rgbww& c) {
  float s = 0;
  for (int i = 0; i < kCh; i++) s += c.v[i];
  return s;
}

TEST(engine_soft_start_and_off) {
  EngineInput in = makeInput();
  in.s.scene.bright = 1000;
  in.s.scene.cct = 2200;  // pure warm
  LightEngine e;
  e.begin(in, 0);
  Rgbww out;
  e.tick(0, out);
  NEAR(sum(out), 0, 1e-6);  // starts dark
  out = run(e, 4, 200);
  CHECK(out.v[CH_WW] > 0.01f && out.v[CH_WW] < 0.95f);  // mid fade
  out = run(e, 204, 700);
  NEAR(out.v[CH_WW], 1, 1e-4);
  NEAR(out.v[CH_R] + out.v[CH_G] + out.v[CH_B] + out.v[CH_CW], 0, 1e-6);
  CHECK(!e.busy());

  in.rt.on = 0;
  e.apply(in, 704);
  out = run(e, 704, 1400);
  NEAR(sum(out), 0, 1e-6);
  CHECK(!e.busy());
}

TEST(engine_master_brightness_is_perceptual) {
  EngineInput in = makeInput();
  in.s.scene.bright = 500;
  in.s.scene.cct = 2200;
  LightEngine e;
  e.begin(in, 0);
  Rgbww out = run(e, 0, 1000);
  NEAR(out.v[CH_WW], color::lToY(0.5f), 1e-4);
}

TEST(engine_mode_crossfade) {
  EngineInput in = makeInput();
  in.s.scene.bright = 1000;
  in.s.scene.cct = 2200;
  LightEngine e;
  e.begin(in, 0);
  run(e, 0, 1000);
  in.s.scene.mode = (uint8_t)Mode::Color;
  in.s.scene.hue = 240;  // blue
  in.s.scene.sat = 1000;
  in.rt.epoch++;
  e.apply(in, 1000);
  Rgbww mid = run(e, 1000, 1250);
  CHECK(mid.v[CH_WW] > 0.1f && mid.v[CH_B] > 0.1f);  // both present mid-fade
  Rgbww end = run(e, 1250, 2000);
  NEAR(end.v[CH_WW], 0, 1e-5);
  NEAR(end.v[CH_B], 1, 1e-4);
}

TEST(engine_pastel_uses_white) {
  EngineInput in = makeInput();
  in.s.scene.mode = (uint8_t)Mode::Color;
  in.s.scene.hue = 0;
  in.s.scene.sat = 400;
  in.s.scene.bright = 1000;
  in.s.hw.pastelWhite = 1;
  LightEngine e;
  e.begin(in, 0);
  Rgbww out = run(e, 0, 1000);
  NEAR(out.v[CH_G], 0, 1e-5);  // white part removed from RGB...
  NEAR(out.v[CH_B], 0, 1e-5);
  CHECK(out.v[CH_WW] + out.v[CH_CW] > 0.5f);  // ...and moved to the W LEDs
  NEAR(out.v[CH_R], 0.4f, 1e-4);
}

TEST(engine_sweep) {
  EngineInput in = makeInput();
  in.s.hw.fadeMs = 0;
  in.s.scene.bright = 1000;
  in.s.scene.mode = (uint8_t)Mode::Sweep;
  SweepCfg& sw = in.s.sweep;
  sw.count = 3;
  sw.ease = EASE_LINEAR;
  sw.speed = 100;
  uint16_t lv[3][kCh] = {{1000, 0, 0, 0, 0}, {0, 1000, 0, 0, 0}, {0, 0, 1000, 0, 0}};
  for (int i = 0; i < 3; i++) {
    memcpy(sw.step[i].lvl, lv[i], sizeof lv[i]);
    sw.step[i].holdDs = 10;  // 1 s
    sw.step[i].fadeDs = 10;  // 1 s
  }
  // REPEAT: R(hold) R->G G(hold) G->B B(hold) B->R  = 6 s cycle
  sw.loop = LOOP_REPEAT;
  LightEngine e;
  e.begin(in, 0);
  Rgbww o = run(e, 0, 500);
  NEAR(o.v[CH_R], 1, 1e-4);
  o = run(e, 504, 1500);
  NEAR(o.v[CH_R], 0.5f, 0.01f);
  NEAR(o.v[CH_G], 0.5f, 0.01f);
  o = run(e, 1504, 2500);
  NEAR(o.v[CH_G], 1, 1e-4);
  o = run(e, 2504, 5500);  // B -> R fade
  NEAR(o.v[CH_B], 0.5f, 0.01f);
  NEAR(o.v[CH_R], 0.5f, 0.01f);
  o = run(e, 5504, 6500);  // wrapped to start
  NEAR(o.v[CH_R], 1, 1e-4);
  CHECK(e.busy());

  // PINGPONG: R G B G R ... ; at t=6.5 s we are holding G on the way back
  sw.loop = LOOP_PINGPONG;
  e.begin(in, 0);
  o = run(e, 0, 6500);
  NEAR(o.v[CH_G], 1, 1e-4);
  o = run(e, 6504, 8500);
  NEAR(o.v[CH_R], 1, 1e-4);  // cycle is 8 s -> back at R

  // ONCE: stops on the last step and the engine goes idle
  sw.loop = LOOP_ONCE;
  e.begin(in, 0);
  o = run(e, 0, 9000);
  NEAR(o.v[CH_B], 1, 1e-4);
  NEAR(o.v[CH_R], 0, 1e-5);
  CHECK(!e.busy());

  // speed 200 % halves all times
  sw.loop = LOOP_REPEAT;
  sw.speed = 200;
  e.begin(in, 0);
  o = run(e, 0, 1000);
  NEAR(o.v[CH_G], 1, 1e-4);
}

TEST(engine_flash) {
  EngineInput in = makeInput();
  in.s.hw.fadeMs = 0;
  in.s.scene.bright = 1000;
  in.s.scene.mode = (uint8_t)Mode::Flash;
  FlashCfg& f = in.s.flash;
  uint16_t a[kCh] = {0, 0, 0, 1000, 1000}, b[kCh] = {0, 0, 0, 0, 0};
  memcpy(f.a, a, sizeof a);
  memcpy(f.b, b, sizeof b);
  f.onMs = 100;
  f.offMs = 100;
  f.burst = 2;
  f.gapMs = 600;
  f.speed = 100;  // cycle = 2*(100+100) + 600 = 1000 ms
  LightEngine e;
  e.begin(in, 0);
  Rgbww o;
  e.tick(0, o);
  o = run(e, 0, 50);
  CHECK(o.v[CH_WW] > 0.99f);
  o = run(e, 52, 150);
  NEAR(sum(o), 0, 1e-6);
  o = run(e, 152, 250);
  CHECK(o.v[CH_WW] > 0.99f);  // second flash of the burst
  o = run(e, 252, 700);
  NEAR(sum(o), 0, 1e-6);       // gap
  o = run(e, 704, 1040);
  CHECK(o.v[CH_WW] > 0.99f);  // next burst

  // strobe-rate cap: even at 400 % with 20/20 ms the period stays >= 40 ms
  f.onMs = 20;
  f.offMs = 20;
  f.gapMs = 0;
  f.burst = 1;
  f.speed = 400;
  e.begin(in, 0);
  int transitions = 0;
  bool prev = false;
  for (uint32_t t = 0; t < 1000; t++) {
    e.tick(t, o);
    bool lit = o.v[CH_WW] > 0.5f;
    if (lit != prev) transitions++;
    prev = lit;
  }
  CHECK(transitions <= 50);  // <= 25 flashes per second
}

TEST(engine_breathe_candle_rainbow) {
  EngineInput in = makeInput();
  in.s.hw.fadeMs = 0;
  in.s.scene.bright = 1000;
  in.s.scene.cct = 2200;
  in.s.scene.baseMode = (uint8_t)Mode::White;
  in.s.scene.mode = (uint8_t)Mode::Breathe;
  in.s.fx.breathePeriodDs = 20;  // 2 s
  in.s.fx.breatheFloor = 200;
  LightEngine e;
  e.begin(in, 0);
  Rgbww o = run(e, 0, 1000);  // bottom of the breath
  NEAR(o.v[CH_WW], color::lToY(0.2f), 0.01f);
  o = run(e, 1004, 2000);  // top again
  NEAR(o.v[CH_WW], 1, 0.01f);

  in.s.scene.mode = (uint8_t)Mode::Candle;
  in.s.fx.candleIntensity = 600;
  e.begin(in, 0);
  float lo = 2, hi = -1;
  for (uint32_t t = 0; t < 20000; t += 4) {
    e.tick(t, o);
    if (t > 500) {
      lo = fminf(lo, o.v[CH_WW]);
      hi = fmaxf(hi, o.v[CH_WW]);
    }
  }
  CHECK(hi <= 1.0001f && lo >= 0.39f && hi - lo > 0.1f);  // flickers, within limits
  CHECK(e.busy());

  in.s.scene.mode = (uint8_t)Mode::Rainbow;
  in.s.fx.rainbowPeriodDs = 30;  // 3 s
  in.s.fx.rainbowSat = 1000;
  e.begin(in, 0);
  o = run(e, 0, 1000);  // 120 deg -> green
  NEAR(o.v[CH_G], 1, 0.02f);
  NEAR(o.v[CH_R], 0, 0.02f);
}

TEST(engine_sleep_timer_and_preview) {
  EngineInput in = makeInput();
  in.s.scene.bright = 1000;
  in.s.scene.cct = 2200;
  LightEngine e;
  e.begin(in, 0);
  run(e, 0, 1000);
  in.rt.sleepEndMs = 11000;
  in.rt.sleepFadeMs = 10000;
  e.apply(in, 1000);
  Rgbww o = run(e, 1000, 1000);
  NEAR(o.v[CH_WW], 1, 1e-3);
  o = run(e, 1004, 6000);
  CHECK(o.v[CH_WW] < 0.5f && o.v[CH_WW] > 0.05f);
  CHECK(e.busy());
  o = run(e, 6004, 11100);
  NEAR(sum(o), 0, 1e-6);

  // raw preview: ignores master brightness and power (channel calibration)
  in = makeInput();
  in.s.scene.bright = 100;
  in.rt.on = 0;
  in.rt.preview = PREVIEW_RAW;
  uint16_t pl[kCh] = {0, 0, 1000, 0, 0};
  memcpy(in.rt.previewLvl, pl, sizeof pl);
  e.begin(in, 0);
  o = run(e, 0, 2000);
  NEAR(o.v[CH_B], 1, 1e-4);
}

// ---------------------------------------------------------------------------
TEST(output_stage) {
  Settings s;
  settings::defaults(s);
  OutputStage os;
  os.configure(s.hw, 999);  // 1000 counts per period
  OutputResult r;
  os.process(Rgbww::zero(), r);
  for (int i = 0; i < kCh; i++) CHECK(r.level[i] == 0);
  os.process(Rgbww{{1, 1, 1, 1, 1}}, r);
  for (int i = 0; i < kCh; i++) CHECK(r.level[i] == 1000);
  os.process(Rgbww{{0.5f, 1e-7f, 0, 0, 0}}, r);
  CHECK(r.level[0] == 500);
  CHECK(r.level[1] == 1);  // any non-zero request produces at least one count

  // duty floor: tiny requests start at the floor, full stays full
  s.hw.chMin[0] = 2000;  // 2 %
  os.configure(s.hw, 9999);
  os.process(Rgbww{{1e-6f, 0, 0, 0, 0}}, r);
  CHECK(r.level[0] == 200);
  os.process(Rgbww{{1, 0, 0, 0, 0}}, r);
  CHECK(r.level[0] == 10000);

  // trim + power budget
  settings::defaults(s);
  for (int i = 0; i < kCh; i++) s.hw.chmA[i] = 1000;
  s.hw.chTrim[1] = 500;
  s.hw.budgetmA = 2000;
  os.configure(s.hw, 9999);
  os.process(Rgbww{{1, 1, 0, 0, 0}}, r);
  CHECK(!r.limited);
  NEAR(r.mA, 1500, 1);
  NEAR(r.lin[1], 0.5f, 1e-6);
  os.process(Rgbww{{1, 1, 1, 1, 1}}, r);  // 4.5 A demanded, 2 A allowed
  CHECK(r.limited);
  NEAR(r.mA, 2000, 2);
  NEAR(r.lin[0] / r.lin[1], 2.0f, 1e-4);  // colour ratios preserved
}

// ---------------------------------------------------------------------------
struct GestureRig {
  Gestures g;
  uint32_t t = 0;
  std::vector<InputEvent> ev;
  void step(bool pressed, int32_t delta = 0, int n = 1) {
    for (int i = 0; i < n; i++) {
      g.update(t, pressed, i == 0 ? delta : 0);
      t += 10;
      InputEvent e;
      while (g.next(e)) ev.push_back(e);
    }
  }
  int count(Ev type) const {
    int c = 0;
    for (auto& e : ev) c += e.type == type;
    return c;
  }
};

TEST(gestures) {
  {  // click
    GestureRig r;
    r.step(false, 0, 3);
    r.step(true, 0, 10);
    r.step(false, 0, 5);
    CHECK(r.count(Ev::Click) == 1 && r.ev.size() == 1);
  }
  {  // long press fires while held, no click on release
    GestureRig r;
    r.step(true, 0, 80);
    CHECK(r.count(Ev::LongPress) == 1);
    r.step(false, 0, 5);
    CHECK(r.count(Ev::Click) == 0);
  }
  {  // press + turn: no click, no long press
    GestureRig r;
    r.step(true, 0, 5);
    r.step(true, 2, 1);
    r.step(true, 0, 80);
    r.step(false, 0, 5);
    CHECK(r.count(Ev::PressTurn) == 1);
    CHECK(r.count(Ev::Click) == 0 && r.count(Ev::LongPress) == 0);
  }
  {  // double click only when enabled
    GestureRig r;
    r.g.enableDoubleClick(true);
    r.step(true, 0, 5);
    r.step(false, 0, 5);
    r.step(true, 0, 5);
    r.step(false, 0, 40);
    CHECK(r.count(Ev::DoubleClick) == 1 && r.count(Ev::Click) == 0);
    r.ev.clear();
    r.step(true, 0, 5);
    r.step(false, 0, 40);  // single click arrives after the double-click window
    CHECK(r.count(Ev::Click) == 1);
  }
  {  // single-sample glitch is debounced away
    GestureRig r;
    r.step(false, 0, 3);
    r.step(true, 0, 1);
    r.step(false, 0, 10);
    CHECK(r.ev.empty());
  }
  {  // acceleration: slow = 1, fast spin = bigger steps
    GestureRig r;
    for (int i = 0; i < 5; i++) r.step(false, 1, 30);  // 1 detent / 300 ms
    CHECK(r.ev.back().accel == 1);
    r.ev.clear();
    for (int i = 0; i < 20; i++) r.step(false, 1, 1);  // 100 detents / s
    CHECK(r.ev.back().accel >= 10);
  }
}

// ---------------------------------------------------------------------------
// UI tests use a painter that records the text drawn on screen.
struct TextPainter : Painter {
  std::string all;
  void fill(int, int, int, int, uint16_t) override {}
  void text(int, int, const char* s, uint8_t, uint16_t) override {
    all += s;
    all += "|";
  }
  bool has(const char* s) const { return all.find(s) != std::string::npos; }
};

struct UiRig {
  Settings s;
  Runtime rt;
  Ui ui;
  uint32_t t = 1000;
  LampStatus st{};
  UiRig() {
    settings::defaults(s);
    memset(&rt, 0, sizeof rt);
    rt.on = 1;
    ui.begin(&s, &rt, t);
  }
  void ev(Ev type, int delta = 0, uint8_t accel = 1, uint8_t src = 0) {
    t += 50;
    ui.handle(InputEvent{type, src, (int16_t)delta, accel}, t);
    ui.update(t, st);
  }
  void wait(uint32_t ms) {
    for (uint32_t k = 0; k < ms; k += 100) {
      t += 100;
      ui.update(t, st);
    }
  }
  std::string screen() {
    TextPainter p;
    ui.draw(p);
    return p.all;
  }
  bool shows(const char* s) { return screen().find(s) != std::string::npos; }
  // Select the menu row whose label is `label` and click it.
  bool open(const char* label) {
    for (int i = 0; i < 20; i++) ev(Ev::Turn, -1);  // to top
    for (int i = 0; i < kMaxItems; i++) {
      if (selectedLabel() == label) {
        ev(Ev::Click);
        return true;
      }
      ev(Ev::Turn, 1);
    }
    return false;
  }
  std::string selectedLabel();
};

// Draw with a painter that remembers the label written on the highlighted row.
struct SelPainter : Painter {
  int selY = -1;
  std::string label;
  void fill(int x, int y, int w, int h, uint16_t c) override {
    if (x == 0 && w == 234 && h == 32) selY = y;  // selection bar geometry
  }
  void text(int x, int y, const char* s, uint8_t, uint16_t) override {
    if (selY >= 0 && y == selY + 9 && x == 8 && label.empty()) label = s;
  }
};

std::string UiRig::selectedLabel() {
  SelPainter p;
  ui.draw(p);
  return p.label;
}

TEST(ui_home_and_power) {
  UiRig r;
  CHECK(r.shows("60.0%"));
  CHECK(r.shows("White"));
  r.ev(Ev::Turn, 2);
  CHECK(r.s.scene.bright == 610);
  CHECK(r.ui.takeSettingsChanged());
  r.ev(Ev::Turn, -1, 25);
  CHECK(r.s.scene.bright == 485);
  r.s.scene.bright = 20;  // fine steps near the bottom
  r.ev(Ev::Turn, -1);
  CHECK(r.s.scene.bright == 19);
  r.ev(Ev::Turn, -100, 25);
  CHECK(r.s.scene.bright == 1);  // never below the lowest step

  r.ev(Ev::PressTurn, 2);  // quick param = colour temperature
  CHECK(r.s.scene.cct == 4100);

  r.ev(Ev::LongPress);
  CHECK(r.rt.on == 0);
  CHECK(r.shows("OFF"));
  r.ev(Ev::Turn, 3);  // turning while off does nothing
  CHECK(r.s.scene.bright == 1);
  r.ev(Ev::Click);
  CHECK(r.rt.on == 1);
}

TEST(ui_menu_mode_select) {
  UiRig r;
  r.ev(Ev::Click);
  CHECK(r.shows("Menu"));
  CHECK(r.open("Mode"));
  uint32_t epoch = r.rt.epoch;
  CHECK(r.open("Color"));
  CHECK(r.s.scene.mode == (uint8_t)Mode::Color);
  CHECK(r.s.scene.baseMode == (uint8_t)Mode::Color);
  CHECK(r.rt.epoch == epoch + 1);
  CHECK(r.shows("Hue"));  // home quick param follows the mode

  // edit hue through Adjust, wrapping below 0
  r.ev(Ev::Click);
  CHECK(r.open("Adjust"));
  r.s.scene.hue = 1;
  CHECK(r.open("Hue"));
  r.ev(Ev::Turn, -3);
  CHECK(r.s.scene.hue == 358);
  r.ev(Ev::Click);  // commit
  // cancel restores the value from before editing
  r.ev(Ev::Click);
  r.ev(Ev::Turn, 10);
  CHECK(r.s.scene.hue == 8);
  r.ev(Ev::LongPress);
  CHECK(r.s.scene.hue == 358);
  r.ev(Ev::LongPress);  // back to main menu
  r.ev(Ev::LongPress);  // back to home
  CHECK(r.shows("Hue"));
}

TEST(ui_sweep_editor_preview) {
  UiRig r;
  r.s.scene.mode = (uint8_t)Mode::Sweep;
  r.ev(Ev::Click);
  CHECK(r.open("Adjust"));
  CHECK(r.open("Steps"));
  CHECK(r.open("Step 2"));
  CHECK(r.rt.preview == PREVIEW_COLOR);
  CHECK(memcmp(r.rt.previewLvl, r.s.sweep.step[1].lvl, sizeof r.rt.previewLvl) == 0);
  CHECK(r.open("Red"));
  r.ev(Ev::Turn, 4);
  CHECK(r.s.sweep.step[1].lvl[0] == 20);
  CHECK(r.rt.previewLvl[0] == 20);  // live preview follows the edit
  r.ev(Ev::Click);
  r.ev(Ev::LongPress);  // leave step editor
  CHECK(r.rt.preview == PREVIEW_NONE);
  CHECK(r.open("+ Add step"));
  CHECK(r.s.sweep.count == 4);
  CHECK(r.shows("Step 4 of 4"));
  CHECK(r.open("Delete step"));
  CHECK(r.s.sweep.count == 3);
}

TEST(ui_calibration_preview) {
  UiRig r;
  r.ev(Ev::Click);
  CHECK(r.open("Settings"));
  CHECK(r.open("Channels"));
  CHECK(r.open("Blue"));
  CHECK(r.rt.preview == PREVIEW_RAW);
  CHECK(r.rt.previewLvl[CH_B] == 1 && r.rt.previewLvl[CH_R] == 0);
  CHECK(r.open("Min duty"));
  r.ev(Ev::Turn, 50, 1);
  CHECK(r.s.hw.chMin[CH_B] == 50);
  CHECK(r.shows("0.050%"));
  r.wait(31000);  // menu times out back to home and the preview ends
  CHECK(r.rt.preview == PREVIEW_NONE);
}

TEST(ui_favorites_and_sleep) {
  UiRig r;
  r.ev(Ev::DoubleClick);
  CHECK(r.shows("No favorites"));
  r.ev(Ev::Click);
  CHECK(r.open("Favorites"));
  CHECK(r.open("Save current"));
  CHECK(r.open("3 (empty)"));
  CHECK(r.s.favUsed == (1u << 2));
  r.ev(Ev::LongPress);
  r.ev(Ev::LongPress);
  r.s.scene.bright = 100;
  r.ev(Ev::DoubleClick);
  CHECK(r.s.scene.bright == 600);  // recalled
  CHECK(r.shows("Favorite 3"));

  r.ev(Ev::Click);
  CHECK(r.open("Sleep"));
  r.ev(Ev::Turn, 1);  // 5 min
  r.ev(Ev::Click);
  CHECK(r.rt.sleepEndMs != 0);
  r.ev(Ev::LongPress);
  CHECK(r.shows("Zz5m"));
  r.wait(5 * 60000 + 200);
  CHECK(r.rt.on == 0);
  r.ev(Ev::LongPress);
  CHECK(r.rt.on == 1 && r.rt.sleepEndMs == 0);
}

TEST(ui_display_power) {
  UiRig r;
  r.s.ui.dispTimeoutS = 30;
  float full = r.ui.backlight();
  CHECK(full > 0);
  r.wait(31000);
  CHECK(r.ui.backlight() < full);  // dimmed
  r.wait(10000);
  CHECK(r.ui.displayAsleep());
  CHECK(r.ui.backlight() == 0);
  uint16_t b = r.s.scene.bright;
  r.ev(Ev::Click);  // wake only: must not open the menu
  CHECK(!r.ui.displayAsleep());
  CHECK(!r.shows("Menu"));
  r.wait(41000);
  r.ev(Ev::Turn, 1);  // turning while asleep adjusts right away
  CHECK(r.s.scene.bright == b + 5);
  // second knob: brightness + power everywhere
  r.ev(Ev::Turn, 1, 1, 1);
  CHECK(r.s.scene.bright == b + 10);
  r.ev(Ev::Click, 0, 1, 1);
  CHECK(r.rt.on == 0);
}

TEST(ui_fuzz) {
  // Random input for a long time: must never crash (ASan/UBSan) and must
  // never push settings out of their legal range.
  UiRig r;
  srand(1234);
  const Ev kinds[] = {Ev::Turn, Ev::Turn, Ev::Turn, Ev::PressTurn, Ev::Click,
                      Ev::Click, Ev::DoubleClick, Ev::LongPress};
  for (int i = 0; i < 200000; i++) {
    Ev k = kinds[rand() % 8];
    int d = (rand() % 7) - 3;
    if (d == 0) d = 1;
    uint8_t acc = (uint8_t)((rand() % 4 == 0) ? 25 : 1);
    r.ev(k, d, acc, (uint8_t)(rand() % 20 == 0));
    if (rand() % 500 == 0) r.wait(40000);
    if (i % 1000 == 0) {
      TextPainter p;
      r.ui.draw(p);
    }
    Settings c = r.s;
    settings::sanitize(c);
    if (memcmp(&c, &r.s, sizeof c) != 0) {
      CHECK(false);
      break;
    }
  }
}

int main() {
  RUN(color_lightness);
  RUN(color_hsv_cct);
  RUN(settings_basics);
  RUN(settings_save_scheduler);
  RUN(engine_soft_start_and_off);
  RUN(engine_master_brightness_is_perceptual);
  RUN(engine_mode_crossfade);
  RUN(engine_pastel_uses_white);
  RUN(engine_sweep);
  RUN(engine_flash);
  RUN(engine_breathe_candle_rainbow);
  RUN(engine_sleep_timer_and_preview);
  RUN(output_stage);
  RUN(gestures);
  RUN(ui_home_and_power);
  RUN(ui_menu_mode_select);
  RUN(ui_sweep_editor_preview);
  RUN(ui_calibration_preview);
  RUN(ui_favorites_and_sleep);
  RUN(ui_display_power);
  RUN(ui_fuzz);
  printf("\n%d checks, %d failures\n", gChecks, gFails);
  return gFails ? 1 : 0;
}
