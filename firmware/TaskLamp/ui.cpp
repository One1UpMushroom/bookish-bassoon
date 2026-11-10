#include "ui.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "color.h"
#include "config.h"

// ===========================================================================
// Look & feel
// ===========================================================================
namespace {
constexpr uint16_t C_BG = 0x0000;
constexpr uint16_t C_HDR = rgb565(24, 28, 36);
constexpr uint16_t C_TEXT = rgb565(235, 235, 235);
constexpr uint16_t C_DIM = rgb565(110, 110, 120);
constexpr uint16_t C_SEL = rgb565(36, 64, 112);
constexpr uint16_t C_EDIT = rgb565(140, 84, 0);
constexpr uint16_t C_ACCENT = rgb565(255, 176, 64);
constexpr uint16_t C_WARN = rgb565(255, 70, 50);
constexpr uint16_t C_CH[kCh] = {rgb565(255, 40, 40), rgb565(40, 220, 60), rgb565(70, 120, 255),
                                rgb565(255, 165, 40), rgb565(200, 230, 255)};

const char* const kChShort[kCh] = {"R", "G", "B", "WW", "CW"};
const char* const kChLong[kCh] = {"Red", "Green", "Blue", "Warm", "Cool"};
const char* const kOffOn[] = {"Off", "On"};
const char* const kLoopNames[] = {"Repeat", "PingPong", "Once"};
const char* const kEaseNames[] = {"Linear", "Smooth"};
const char* const kBaseNames[] = {"White", "Color", "Mixer"};
const char* const kDirNames[] = {"Normal", "Reverse"};
const char* const kSleepNames[] = {"Off", "5 min", "15 min", "30 min", "60 min", "90 min", "2 hr"};
const uint16_t kSleepMin[] = {0, 5, 15, 30, 60, 90, 120};
constexpr uint8_t kSleepCount = sizeof(kSleepMin) / sizeof(kSleepMin[0]);

constexpr int kRowY0 = 34;
constexpr int kRowH = 34;

// Approximate on-screen colour of what the LEDs are producing.
uint16_t lampSwatch(const float* lin) {
  float r = lin[CH_R] + lin[CH_WW] * 1.0f + lin[CH_CW] * 0.75f;
  float g = lin[CH_G] + lin[CH_WW] * 0.55f + lin[CH_CW] * 0.8f;
  float b = lin[CH_B] + lin[CH_WW] * 0.08f + lin[CH_CW] * 0.9f;
  float m = r > g ? (r > b ? r : b) : (g > b ? g : b);
  if (m <= 0.0005f) return rgb565(20, 20, 20);
  auto ch = [&](float v) { return (uint8_t)(color::yToL(v / m) * 255.f); };
  return rgb565(ch(r), ch(g), ch(b));
}
}  // namespace

void formatValue(Fmt f, uint16_t v, char* buf, int n) {
  switch (f) {
    case Fmt::Permille: snprintf(buf, n, "%u.%u%%", v / 10, v % 10); break;
    case Fmt::Kelvin: snprintf(buf, n, "%uK", v); break;
    case Fmt::Degree: snprintf(buf, n, "%u\xF8", v); break;  // cp437 degree sign
    case Fmt::Deci: snprintf(buf, n, "%u.%us", v / 10, v % 10); break;
    case Fmt::Ms: snprintf(buf, n, "%ums", v); break;
    case Fmt::Int: snprintf(buf, n, "%u", v); break;
    case Fmt::MilliAmp:
      if (v == 0) snprintf(buf, n, "--");
      else if (v >= 1000) snprintf(buf, n, "%u.%02uA", v / 1000, (v % 1000) / 10);
      else snprintf(buf, n, "%umA", v);
      break;
    case Fmt::Hz:
      if (v >= 1000) snprintf(buf, n, "%u.%ukHz", v / 1000, (v % 1000) / 100);
      else snprintf(buf, n, "%uHz", v);
      break;
    case Fmt::Pct: snprintf(buf, n, "%u%%", v); break;
    case Fmt::MinDuty: snprintf(buf, n, "%u.%03u%%", v / 1000, v % 1000); break;
    case Fmt::Sec:
      if (v == 0) snprintf(buf, n, "Never");
      else snprintf(buf, n, "%us", v);
      break;
  }
}

// ===========================================================================
// Menu container
// ===========================================================================
void Menu::reset() {
  memset(this, 0, sizeof(*this));
  focus = -1;
  calCh = -1;
}

Item& Menu::add(Item::Kind k, const char* label) {
  static Item overflow;  // absorbs writes if a builder ever exceeds kMaxItems
  Item& it = n < kMaxItems ? items[n++] : overflow;
  memset(&it, 0, sizeof(it));
  it.kind = k;
  strncpy(it.label, label, sizeof(it.label) - 1);
  return it;
}

Item& Menu::num(const char* label, uint16_t* v, uint16_t lo, uint16_t hi, uint16_t step, Fmt f,
                uint8_t flags) {
  Item& it = add(Item::Num, label);
  it.v16 = v;
  it.lo = lo;
  it.hi = hi;
  it.step = step;
  it.fmt = f;
  it.flags = flags;
  return it;
}

Item& Menu::enm(const char* label, uint8_t* v, const char* const* names, uint8_t count,
                uint8_t flags) {
  Item& it = add(Item::Enum, label);
  it.v8 = v;
  it.names = names;
  it.count = count;
  it.flags = flags;
  return it;
}

Item& Menu::sub(const char* label, Builder b, int arg, const char* info) {
  Item& it = add(Item::Sub, label);
  it.sub = b;
  it.arg = (int16_t)arg;
  if (info) strncpy(it.info, info, sizeof(it.info) - 1);
  return it;
}

Item& Menu::act(const char* label, Action a, int arg, const char* info) {
  Item& it = add(Item::Act, label);
  it.act = a;
  it.arg = (int16_t)arg;
  if (info) strncpy(it.info, info, sizeof(it.info) - 1);
  return it;
}

Item& Menu::back(const char* label) { return add(Item::Back, label); }

// ===========================================================================
// Menu builders and actions
// ===========================================================================
namespace {

void mainMenu(Ui& ui, Menu& m, int);
void modeMenu(Ui& ui, Menu& m, int);
void adjustMenu(Ui& ui, Menu& m, int);
void sweepStepsMenu(Ui& ui, Menu& m, int);
void sweepStepMenu(Ui& ui, Menu& m, int i);
void flashColorMenu(Ui& ui, Menu& m, int which);
void favoritesMenu(Ui& ui, Menu& m, int);
void favSaveMenu(Ui& ui, Menu& m, int);
void settingsMenu(Ui& ui, Menu& m, int);
void whiteMenu(Ui& ui, Menu& m, int);
void displayMenu(Ui& ui, Menu& m, int);
void powerMenu(Ui& ui, Menu& m, int);
void channelsMenu(Ui& ui, Menu& m, int);
void channelMenu(Ui& ui, Menu& m, int ch);
void resetMenu(Ui& ui, Menu& m, int);

void levelItems(Menu& m, uint16_t* lvl) {
  for (int i = 0; i < kCh; i++) m.num(kChLong[i], &lvl[i], 0, 1000, 5, Fmt::Permille);
}

// Base colour parameters (used by Breathe and Candle).
void baseItems(Ui& ui, Menu& m) {
  Scene& sc = ui.s->scene;
  m.enm("Base color", &sc.baseMode, kBaseNames, 3, Item::F_REBUILD);
  switch ((Mode)sc.baseMode) {
    case Mode::Color:
      m.num("Hue", &sc.hue, 0, 359, 1, Fmt::Degree, Item::F_WRAP);
      m.num("Saturation", &sc.sat, 0, 1000, 5, Fmt::Permille);
      break;
    case Mode::Mixer:
      levelItems(m, sc.mix);
      break;
    default:
      m.num("Temp", &sc.cct, ui.s->hw.warmK, ui.s->hw.coolK, 50, Fmt::Kelvin);
      break;
  }
}

// --- actions ---------------------------------------------------------------
void actSelectMode(Ui& ui, int mode) {
  Scene& sc = ui.s->scene;
  sc.mode = (uint8_t)mode;
  if (isBaseMode((Mode)mode)) sc.baseMode = (uint8_t)mode;
  ui.bumpEpoch();
  ui.settingsChanged();
  ui.goHome();
}

void actApplySleep(Ui& ui, int) {
  uint32_t min = kSleepMin[ui.sleepSel < kSleepCount ? ui.sleepSel : 0];
  if (min == 0) {
    ui.rt->sleepEndMs = 0;
  } else {
    uint32_t total = min * 60000u;
    ui.rt->sleepEndMs = (ui.now + total) | 1u;  // never 0
    ui.rt->sleepFadeMs = total < 300000u ? total : 300000u;  // fade over the last 5 min
  }
  ui.runtimeChanged();  // not bumpEpoch(): a running sweep must not start over
}

void actCaptureInto(Ui& ui, uint16_t* lvl) {
  Mode m = (Mode)ui.s->scene.mode;
  if (!isBaseMode(m)) m = (Mode)ui.s->scene.baseMode;
  color::toLevels(sceneBaseColor(*ui.s, m), lvl);
  ui.settingsChanged();
  ui.refreshPreview();
  ui.toast("Captured");
}

void actCaptureStep(Ui& ui, int i) { actCaptureInto(ui, ui.s->sweep.step[i].lvl); }
void actCaptureFlash(Ui& ui, int which) {
  actCaptureInto(ui, which ? ui.s->flash.b : ui.s->flash.a);
}
void actClearFlash(Ui& ui, int which) {
  memset(which ? ui.s->flash.b : ui.s->flash.a, 0, sizeof(uint16_t) * kCh);
  ui.settingsChanged();
  ui.refreshPreview();
}

void actAddStep(Ui& ui, int) {
  SweepCfg& sw = ui.s->sweep;
  if (sw.count >= kMaxSweepSteps) return;
  sw.step[sw.count] = sw.step[sw.count - 1];
  sw.count++;
  ui.settingsChanged();
  ui.push(sweepStepMenu, sw.count - 1);  // straight into editing the new step
}

void actDeleteStep(Ui& ui, int i) {
  SweepCfg& sw = ui.s->sweep;
  if (sw.count <= 1) return;
  for (int k = i; k < sw.count - 1; k++) sw.step[k] = sw.step[k + 1];
  sw.count--;
  ui.settingsChanged();
  ui.pop();
}

void actRecallFav(Ui& ui, int i) {
  if (!(ui.s->favUsed & (1u << i))) {
    ui.toast("Empty slot");
    return;
  }
  ui.s->scene = ui.s->fav[i];
  ui.bumpEpoch();
  ui.settingsChanged();
  ui.goHome();
  char t[24];
  snprintf(t, sizeof t, "Favorite %d", i + 1);
  ui.toast(t);
}

void actSaveFav(Ui& ui, int i) {
  ui.s->fav[i] = ui.s->scene;
  ui.s->favUsed |= (uint8_t)(1u << i);
  ui.settingsChanged();
  ui.pop();
  char t[24];
  snprintf(t, sizeof t, "Saved to %d", i + 1);
  ui.toast(t);
}

void actClampCct(Ui& ui, int) {
  // Keep the scene and every favourite inside the new white-LED range.
  for (int i = -1; i < kFavorites; i++) {
    Scene& sc = i < 0 ? ui.s->scene : ui.s->fav[i];
    if (sc.cct < ui.s->hw.warmK) sc.cct = ui.s->hw.warmK;
    if (sc.cct > ui.s->hw.coolK) sc.cct = ui.s->hw.coolK;
  }
}

void actFactoryReset(Ui& ui, int) {
  settings::defaults(*ui.s);
  ui.bumpEpoch();
  ui.settingsChanged();
  ui.goHome();
  ui.toast("Reset done");
}

void sceneLabel(const Scene& sc, int slot, char* buf, int n) {
  snprintf(buf, n, "%d %s %u%%", slot + 1, modeName((Mode)sc.mode), (sc.bright + 5) / 10);
}

// --- builders --------------------------------------------------------------
void mainMenu(Ui& ui, Menu& m, int) {
  strcpy(m.title, "Menu");
  m.sub("Mode", modeMenu, 0, modeName((Mode)ui.s->scene.mode));
  m.sub("Adjust", adjustMenu);
  m.sub("Favorites", favoritesMenu);
  Item& sl = m.enm("Sleep", &ui.sleepSel, kSleepNames, kSleepCount, Item::F_NOSAVE);
  sl.change = actApplySleep;
  m.sub("Settings", settingsMenu);
  m.back();
}

void modeMenu(Ui& ui, Menu& m, int) {
  strcpy(m.title, "Mode");
  for (int i = 0; i < (int)Mode::Count; i++)
    m.act(modeName((Mode)i), actSelectMode, i, i == ui.s->scene.mode ? "*" : nullptr);
  m.back();
  m.focus = (int8_t)ui.s->scene.mode;
}

void adjustMenu(Ui& ui, Menu& m, int) {
  Settings& s = *ui.s;
  Scene& sc = s.scene;
  snprintf(m.title, sizeof m.title, "%s", modeName((Mode)sc.mode));
  m.num("Brightness", &sc.bright, 1, 1000, 5, Fmt::Permille);
  switch ((Mode)sc.mode) {
    case Mode::White:
      m.num("Temp", &sc.cct, s.hw.warmK, s.hw.coolK, 50, Fmt::Kelvin);
      break;
    case Mode::Color:
      m.num("Hue", &sc.hue, 0, 359, 1, Fmt::Degree, Item::F_WRAP);
      m.num("Saturation", &sc.sat, 0, 1000, 5, Fmt::Permille);
      break;
    case Mode::Mixer:
      levelItems(m, sc.mix);
      break;
    case Mode::Sweep:
      m.num("Speed", &s.sweep.speed, 25, 400, 5, Fmt::Pct);
      m.enm("Loop", &s.sweep.loop, kLoopNames, LOOP_COUNT, Item::F_EPOCH);
      m.enm("Easing", &s.sweep.ease, kEaseNames, EASE_COUNT);
      m.sub("Steps", sweepStepsMenu);
      break;
    case Mode::Flash:
      m.num("Speed", &s.flash.speed, 25, 400, 5, Fmt::Pct);
      m.num("On time", &s.flash.onMs, 20, 2000, 10, Fmt::Ms);
      m.num("Off time", &s.flash.offMs, 20, 2000, 10, Fmt::Ms);
      m.num("Flashes", &s.flash.burst, 1, 10, 1, Fmt::Int);
      m.num("Pause", &s.flash.gapMs, 0, 10000, 50, Fmt::Ms);
      m.sub("Color A", flashColorMenu, 0);
      m.sub("Color B", flashColorMenu, 1);
      break;
    case Mode::Breathe:
      m.num("Period", &s.fx.breathePeriodDs, 10, 600, 1, Fmt::Deci);
      m.num("Low level", &s.fx.breatheFloor, 0, 900, 10, Fmt::Permille);
      baseItems(ui, m);
      break;
    case Mode::Rainbow:
      m.num("Period", &s.fx.rainbowPeriodDs, 10, 6000, 5, Fmt::Deci);
      m.num("Saturation", &s.fx.rainbowSat, 0, 1000, 10, Fmt::Permille);
      break;
    case Mode::Candle:
      m.num("Flicker", &s.fx.candleIntensity, 0, 1000, 10, Fmt::Permille);
      m.num("Speed", &s.fx.candleSpeed, 25, 400, 5, Fmt::Pct);
      baseItems(ui, m);
      break;
    default:
      break;
  }
  m.back();
}

void sweepStepsMenu(Ui& ui, Menu& m, int) {
  SweepCfg& sw = ui.s->sweep;
  strcpy(m.title, "Sweep steps");
  for (int i = 0; i < sw.count; i++) {
    char label[18], info[10];
    snprintf(label, sizeof label, "Step %d", i + 1);
    uint32_t ds = sw.step[i].holdDs + sw.step[i].fadeDs;
    snprintf(info, sizeof info, "%lu.%lus", (unsigned long)(ds / 10), (unsigned long)(ds % 10));
    m.sub(label, sweepStepMenu, i, info);
  }
  if (sw.count < kMaxSweepSteps) m.act("+ Add step", actAddStep);
  m.back();
}

void sweepStepMenu(Ui& ui, Menu& m, int i) {
  SweepCfg& sw = ui.s->sweep;
  if (i >= sw.count) i = sw.count - 1;
  SweepStep& st = sw.step[i];
  snprintf(m.title, sizeof m.title, "Step %d of %d", i + 1, sw.count);
  m.previewLvl = st.lvl;  // the lamp shows this step while you edit it
  levelItems(m, st.lvl);
  m.num("Hold", &st.holdDs, 0, 3000, 1, Fmt::Deci);
  m.num("Fade", &st.fadeDs, 0, 3000, 1, Fmt::Deci);
  m.act("Capture light", actCaptureStep, i);
  if (sw.count > 1) m.act("Delete step", actDeleteStep, i);
  m.back();
}

void flashColorMenu(Ui& ui, Menu& m, int which) {
  uint16_t* lvl = which ? ui.s->flash.b : ui.s->flash.a;
  strcpy(m.title, which ? "Color B (off)" : "Color A (on)");
  m.previewLvl = lvl;
  levelItems(m, lvl);
  m.act("Capture light", actCaptureFlash, which);
  m.act("All dark", actClearFlash, which);
  m.back();
}

void favoritesMenu(Ui& ui, Menu& m, int) {
  strcpy(m.title, "Favorites");
  for (int i = 0; i < kFavorites; i++) {
    char label[18];
    if (ui.s->favUsed & (1u << i)) sceneLabel(ui.s->fav[i], i, label, sizeof label);
    else snprintf(label, sizeof label, "%c (empty)", (char)('1' + i));
    m.act(label, actRecallFav, i);
  }
  m.sub("Save current", favSaveMenu);
  m.back();
}

void favSaveMenu(Ui& ui, Menu& m, int) {
  strcpy(m.title, "Save to slot");
  for (int i = 0; i < kFavorites; i++) {
    char label[18];
    if (ui.s->favUsed & (1u << i)) sceneLabel(ui.s->fav[i], i, label, sizeof label);
    else snprintf(label, sizeof label, "%c (empty)", (char)('1' + i));
    m.act(label, actSaveFav, i);
  }
  m.back("< Cancel");
}

void settingsMenu(Ui& ui, Menu& m, int) {
  HwCfg& hw = ui.s->hw;
  strcpy(m.title, "Settings");
  m.num("Transition", &hw.fadeMs, 0, 5000, 50, Fmt::Ms);
  m.sub("White LEDs", whiteMenu);
  m.sub("Display", displayMenu);
  m.enm("Knob dir", &hw.knobReverse, kDirNames, 2);
  m.sub("Power", powerMenu);
  m.sub("Channels", channelsMenu);
  m.num("PWM freq", &hw.pwmHz, 200, 20000, 100, Fmt::Hz);
  m.sub("Factory reset", resetMenu);
  m.act("Firmware", nullptr, 0, TASKLAMP_VERSION);
  m.back();
}

void whiteMenu(Ui& ui, Menu& m, int) {
  HwCfg& hw = ui.s->hw;
  strcpy(m.title, "White LEDs");
  m.num("Warm LED", &hw.warmK, 1500, 4000, 50, Fmt::Kelvin).change = actClampCct;
  m.num("Cool LED", &hw.coolK, 4500, 10000, 50, Fmt::Kelvin).change = actClampCct;
  m.enm("Max output", &hw.whiteBoost, kOffOn, 2);
  m.enm("Pastel->W", &hw.pastelWhite, kOffOn, 2);
  m.back();
}

void displayMenu(Ui& ui, Menu& m, int) {
  UiCfg& u = ui.s->ui;
  strcpy(m.title, "Display");
  m.num("Brightness", &u.dispBright, 50, 1000, 10, Fmt::Permille);
  m.enm("Follow lamp", &u.dispFollow, kOffOn, 2);
  m.num("Timeout", &u.dispTimeoutS, 0, 600, 5, Fmt::Sec);
  m.enm("Knob glow", &u.knobGlow, kOffOn, 2);
  m.back();
}

void powerMenu(Ui& ui, Menu& m, int) {
  HwCfg& hw = ui.s->hw;
  strcpy(m.title, "Power");
  m.num("Budget", &hw.budgetmA, 0, 30000, 50, Fmt::MilliAmp);
  for (int i = 0; i < kCh; i++) {
    char label[18];
    snprintf(label, sizeof label, "%s @100%%", kChShort[i]);
    m.num(label, &hw.chmA[i], 0, 10000, 10, Fmt::MilliAmp);
  }
  m.back();
}

void channelsMenu(Ui&, Menu& m, int) {
  strcpy(m.title, "Channels");
  for (int i = 0; i < kCh; i++) m.sub(kChLong[i], channelMenu, i);
  m.back();
}

void refreshCal(Ui& ui, int) { ui.refreshPreview(); }

void channelMenu(Ui& ui, Menu& m, int ch) {
  HwCfg& hw = ui.s->hw;
  snprintf(m.title, sizeof m.title, "%s channel", kChLong[ch]);
  m.calCh = (int8_t)ch;  // lamp shows only this channel at the test level
  m.num("Test level", &ui.calTest, 0, 1000, 1, Fmt::Permille, Item::F_NOSAVE).change = refreshCal;
  m.num("Min duty", &hw.chMin[ch], 0, 5000, 1, Fmt::MinDuty);
  m.num("Trim", &hw.chTrim[ch], 100, 1000, 5, Fmt::Permille);
  m.enm("Invert", &hw.chInvert[ch], kOffOn, 2);
  m.back();
}

void resetMenu(Ui&, Menu& m, int) {
  strcpy(m.title, "Reset all?");
  m.back("< Cancel");
  m.act("Yes, reset", actFactoryReset);
}

}  // namespace

// ===========================================================================
// Ui
// ===========================================================================
void Ui::begin(Settings* settings, Runtime* runtime, uint32_t nowMs) {
  s = settings;
  rt = runtime;
  now = nowMs;
  lastInput_ = nowMs;
  screen_ = Screen::Home;
  redraw_ = true;
}

void Ui::toast(const char* msg) {
  strncpy(toast_, msg, sizeof(toast_) - 1);
  toast_[sizeof(toast_) - 1] = 0;
  toastUntil_ = now + 1500;
  redraw_ = true;
}

void Ui::setPower(bool on) {
  if ((rt->on != 0) == on) return;
  rt->on = on;
  // Keep a running sleep fade in place while switching off (no brightness
  // jump); a fresh "on" always starts without a timer.
  if (on) rt->sleepEndMs = 0;
  sleepSel = 0;
  runtimeChanged_ = true;
  redraw_ = true;
}

void Ui::push(Builder b, int arg) {
  if (depth_ >= sizeof(stack_) / sizeof(stack_[0])) return;
  editing_ = false;
  stack_[depth_++] = Frame{b, (int16_t)arg, 0, 0};
  screen_ = Screen::Menu;
  rebuild();
  Frame& f = stack_[depth_ - 1];
  if (menu_.focus >= 0 && menu_.focus < menu_.n) {
    f.sel = (uint8_t)menu_.focus;
    f.top = f.sel >= kRowsVisible ? (uint8_t)(f.sel - kRowsVisible + 1) : 0;
  }
}

void Ui::rebuild() {
  if (!depth_) return;
  Frame& f = stack_[depth_ - 1];
  menu_.reset();
  f.b(*this, menu_, f.arg);
  if (menu_.n == 0) menu_.back();
  if (f.sel >= menu_.n) f.sel = menu_.n - 1;
  if (f.top > f.sel) f.top = f.sel;
  refreshPreview();
  redraw_ = true;
}

void Ui::pop() {
  editing_ = false;
  if (depth_ > 1) {
    depth_--;
    rebuild();
  } else {
    goHome();
  }
}

void Ui::goHome() {
  depth_ = 0;
  editing_ = false;
  screen_ = Screen::Home;
  menu_.reset();
  refreshPreview();
  redraw_ = true;
}

void Ui::refreshPreview() {
  uint8_t mode = PREVIEW_NONE;
  uint16_t lv[kCh] = {0, 0, 0, 0, 0};
  if (screen_ == Screen::Menu) {
    if (menu_.calCh >= 0) {
      mode = PREVIEW_RAW;
      lv[menu_.calCh] = calTest;
    } else if (menu_.previewLvl) {
      mode = PREVIEW_COLOR;
      memcpy(lv, menu_.previewLvl, sizeof lv);
    }
  }
  if (mode != rt->preview || memcmp(lv, rt->previewLvl, sizeof lv) != 0) {
    rt->preview = mode;
    memcpy(rt->previewLvl, lv, sizeof lv);
    runtimeChanged_ = true;
  }
}

bool Ui::quickParam(Quick& q) {
  Settings& st = *s;
  switch ((Mode)st.scene.mode) {
    case Mode::White: q = {"Temp", &st.scene.cct, st.hw.warmK, st.hw.coolK, 50, Fmt::Kelvin, false}; return true;
    case Mode::Color: q = {"Hue", &st.scene.hue, 0, 359, 2, Fmt::Degree, true}; return true;
    case Mode::Sweep: q = {"Speed", &st.sweep.speed, 25, 400, 5, Fmt::Pct, false}; return true;
    case Mode::Flash: q = {"Speed", &st.flash.speed, 25, 400, 5, Fmt::Pct, false}; return true;
    case Mode::Breathe: q = {"Period", &st.fx.breathePeriodDs, 10, 600, 1, Fmt::Deci, false}; return true;
    case Mode::Rainbow: q = {"Period", &st.fx.rainbowPeriodDs, 10, 6000, 5, Fmt::Deci, false}; return true;
    case Mode::Candle: q = {"Flicker", &st.fx.candleIntensity, 0, 1000, 10, Fmt::Permille, false}; return true;
    default: return false;
  }
}

static int32_t stepValue(int32_t v, int32_t delta, int32_t lo, int32_t hi, bool wrap) {
  v += delta;
  if (wrap) {
    int32_t span = hi - lo + 1;
    v = lo + ((v - lo) % span + span) % span;
  } else {
    if (v < lo) v = lo;
    if (v > hi) v = hi;
  }
  return v;
}

void Ui::nextFavorite() {
  if (!s->favUsed) {
    toast("No favorites");
    return;
  }
  for (int k = 1; k <= kFavorites; k++) {
    int i = (favIdx_ + k) % kFavorites;
    if (s->favUsed & (1u << i)) {
      favIdx_ = (uint8_t)i;
      actRecallFav(*this, i);
      return;
    }
  }
}

void Ui::handle(const InputEvent& e, uint32_t nowMs) {
  now = nowMs;
  bool wasAsleep = asleep_;
  lastInput_ = nowMs;
  if (asleep_ || dimmed_) {
    asleep_ = dimmed_ = false;
    redraw_ = true;
  }

  if (e.src == 1) {  // optional second knob: dedicated brightness + power
    if ((e.type == Ev::Turn || e.type == Ev::PressTurn) && rt->on) {
      int step = s->scene.bright <= 50 ? 1 : 5;
      int32_t v = stepValue(s->scene.bright, (int32_t)e.delta * step * e.accel, 1, 1000, false);
      if (v != s->scene.bright) { s->scene.bright = (uint16_t)v; settingsChanged(); }
    } else if (e.type == Ev::Click) {
      setPower(!rt->on);
    } else if (e.type == Ev::LongPress) {
      goHome();
    }
    return;
  }

  if (wasAsleep && e.type == Ev::Click) return;  // a click only wakes the screen
  if (screen_ == Screen::Home) homeEvent(e);
  else menuEvent(e);
}

void Ui::homeEvent(const InputEvent& e) {
  switch (e.type) {
    case Ev::Turn: {
      if (!rt->on) return;
      // Finer steps near the bottom, where small changes are most visible.
      int step = s->scene.bright <= 50 ? 1 : 5;
      int32_t v = stepValue(s->scene.bright, (int32_t)e.delta * step * e.accel, 1, 1000, false);
      if (v != s->scene.bright) { s->scene.bright = (uint16_t)v; settingsChanged(); }
      break;
    }
    case Ev::PressTurn: {
      if (!rt->on) return;
      Quick q;
      if (!quickParam(q)) { toast("Use Menu>Adjust"); return; }
      int32_t v = stepValue(*q.v, (int32_t)e.delta * q.step * e.accel, q.lo, q.hi, q.wrap);
      if (v != *q.v) { *q.v = (uint16_t)v; settingsChanged(); }
      quickActive_ = true;
      redraw_ = true;
      break;
    }
    case Ev::Click:
      if (!rt->on) setPower(true);
      else push(mainMenu);
      break;
    case Ev::DoubleClick:
      if (!rt->on) setPower(true);
      else nextFavorite();
      break;
    case Ev::LongPress:
      setPower(!rt->on);
      break;
    default:
      break;
  }
}

void Ui::menuEvent(const InputEvent& e) {
  if (!depth_) { goHome(); return; }
  Frame& f = stack_[depth_ - 1];
  Item& it = menu_.items[f.sel];

  if (editing_) {
    switch (e.type) {
      case Ev::Turn:
      case Ev::PressTurn:
        adjust(it, e.delta, e.accel);
        break;
      case Ev::Click:
        editing_ = false;
        redraw_ = true;
        if (it.flags & Item::F_REBUILD) rebuild();
        break;
      case Ev::LongPress:  // cancel: restore the value from before editing
        if (it.kind == Item::Num) *it.v16 = editOrig_;
        else *it.v8 = (uint8_t)editOrig_;
        editing_ = false;
        valueChanged(it);
        break;
      default:
        break;
    }
    return;
  }

  switch (e.type) {
    case Ev::Turn:
    case Ev::PressTurn: {
      int32_t sel = stepValue(f.sel, e.delta, 0, menu_.n - 1, false);
      f.sel = (uint8_t)sel;
      if (f.sel < f.top) f.top = f.sel;
      if (f.sel >= f.top + kRowsVisible) f.top = (uint8_t)(f.sel - kRowsVisible + 1);
      redraw_ = true;
      break;
    }
    case Ev::Click:
      switch (it.kind) {
        case Item::Back: pop(); break;
        case Item::Sub: push(it.sub, it.arg); break;
        case Item::Act: if (it.act) it.act(*this, it.arg); break;
        case Item::Num: editing_ = true; editOrig_ = *it.v16; redraw_ = true; break;
        case Item::Enum: editing_ = true; editOrig_ = *it.v8; redraw_ = true; break;
      }
      break;
    case Ev::LongPress:
      pop();
      break;
    default:
      break;
  }
}

void Ui::adjust(Item& it, int delta, int accel) {
  if (it.kind == Item::Num) {
    int32_t v = stepValue(*it.v16, (int32_t)delta * it.step * accel, it.lo, it.hi,
                          it.flags & Item::F_WRAP);
    if (v != *it.v16) { *it.v16 = (uint16_t)v; valueChanged(it); }
  } else if (it.kind == Item::Enum) {
    int32_t v = stepValue(*it.v8, delta, 0, it.count - 1, false);
    if (v != *it.v8) { *it.v8 = (uint8_t)v; valueChanged(it); }
  }
}

void Ui::valueChanged(Item& it) {
  if (!(it.flags & Item::F_NOSAVE)) settingsChanged_ = true;
  if (it.flags & Item::F_EPOCH) bumpEpoch();
  if (it.change) it.change(*this, it.arg);
  refreshPreview();
  redraw_ = true;
}

void Ui::update(uint32_t nowMs, const LampStatus& st) {
  now = nowMs;
  st_ = st;
  uint32_t idle = nowMs - lastInput_;

  // Sleep timer reached its end: the engine has already faded to black.
  if (rt->on && rt->sleepEndMs && (int32_t)(nowMs - rt->sleepEndMs) >= 0) {
    rt->on = 0;
    sleepSel = 0;
    runtimeChanged_ = true;
    redraw_ = true;
  }
  if (quickActive_ && idle > 1500) { quickActive_ = false; redraw_ = true; }
  if (toast_[0] && (int32_t)(nowMs - toastUntil_) >= 0) { toast_[0] = 0; redraw_ = true; }
  // A screen that is showing a test or preview light holds on for longer.
  bool hold = screen_ == Screen::Menu && (menu_.calCh >= 0 || menu_.previewLvl);
  if (screen_ == Screen::Menu && idle > (hold ? cfg::kMenuHoldMs : cfg::kMenuTimeoutMs)) goHome();

  // Display power: dim after the timeout, sleep 10 s later. With the lamp
  // off there is nothing to look at, so the screen goes dark sooner.
  uint32_t timeout = s->ui.dispTimeoutS * 1000u;
  if (!rt->on && (timeout == 0 || timeout > 15000u)) timeout = 15000u;
  if (timeout) {
    if (!asleep_ && idle >= timeout + 10000u) {
      asleep_ = true;
      if (screen_ != Screen::Home && !hold) goHome();
    } else if (!dimmed_ && idle >= timeout) {
      dimmed_ = true;
    }
  }

  // Home screen live data: redraw only when something visibly changed.
  if (screen_ == Screen::Home && !asleep_ && nowMs - lastLive_ >= cfg::kUiLiveMs) {
    lastLive_ = nowMs;
    bool changed = st.limited != drawnLimited_ || fabsf(st.mA - drawnmA_) > 5.f;
    for (int i = 0; i < kCh; i++)
      if (fabsf(st.lin[i] - drawnLin_[i]) > 0.002f) changed = true;
    int32_t sleepMin = -1;
    if (rt->on && rt->sleepEndMs) sleepMin = (int32_t)(rt->sleepEndMs - nowMs) / 60000;
    if (sleepMin != drawnSleepMin_) changed = true;
    if (changed) redraw_ = true;
  }
}

float Ui::backlight() const {
  if (asleep_) return 0.f;
  float L = s->ui.dispBright * 0.001f;
  if (s->ui.dispFollow) {
    // Bright lamp -> bright screen; dim lamp at night -> dim screen.
    float lamp = rt->on ? st_.masterL : 0.3f;
    L *= 0.35f + 0.65f * lamp;
  }
  if (dimmed_) L *= 0.4f;
  return color::lToY(L);
}

uint32_t Ui::knobGlow() const {
  // A faint amber locator so the knob can be found in the dark.
  return (s->ui.knobGlow && !rt->on) ? 0x060200u : 0u;
}

// ===========================================================================
// Drawing
// ===========================================================================
void Ui::draw(Painter& p) {
  if (screen_ == Screen::Home) drawHome(p);
  else drawMenu(p);
  if (toast_[0]) {
    int w = Painter::textWidth(toast_, 2) + 24;
    int x = (kScreenW - w) / 2;
    p.fill(x, 104, w, 34, C_HDR);
    p.frame(x, 104, w, 34, C_ACCENT);
    p.textCenter(kScreenW / 2, 113, toast_, 2, C_TEXT);
  }
}

void Ui::drawHome(Painter& p) {
  const Scene& sc = s->scene;
  bool on = rt->on;
  char buf[16];

  // Header: swatch of the actual light, mode, status.
  p.fill(0, 0, kScreenW, 30, C_HDR);
  uint16_t sw = lampSwatch(st_.lin);
  p.fill(8, 7, 16, 16, sw);
  p.frame(8, 7, 16, 16, C_DIM);
  p.text(32, 8, modeName((Mode)sc.mode), 2, C_TEXT);
  buf[0] = 0;
  uint16_t statusColor = C_DIM;
  int32_t sleepMin = -1;
  if (!on) {
    strcpy(buf, "OFF");
  } else if (st_.limited) {
    strcpy(buf, "LIMIT");
    statusColor = C_WARN;
  } else if (rt->sleepEndMs) {
    sleepMin = (int32_t)(rt->sleepEndMs - now) / 60000;
    snprintf(buf, sizeof buf, "Zz%ldm", (long)sleepMin + 1);
    statusColor = C_ACCENT;
  } else if (st_.mA >= 1.f) {
    formatValue(Fmt::MilliAmp, (uint16_t)(st_.mA + 0.5f), buf, sizeof buf);
  }
  p.textRight(232, 8, buf, 2, statusColor);

  // Master brightness, big.
  formatValue(Fmt::Permille, sc.bright, buf, sizeof buf);
  p.textCenter(kScreenW / 2, 44, buf, 5, on ? C_TEXT : C_DIM);
  p.frame(10, 94, 220, 10, C_DIM);
  p.fill(11, 95, 218 * sc.bright / 1000, 8, on ? C_ACCENT : C_DIM);

  // Quick parameter (press + turn).
  Quick q;
  if (!on) {
    p.textCenter(kScreenW / 2, 116, "Click to turn on", 2, C_DIM);
  } else if (quickParam(q)) {
    if (quickActive_) p.fill(0, 110, kScreenW, 26, C_SEL);
    p.text(10, 116, q.label, 2, C_DIM);
    formatValue(q.fmt, *q.v, buf, sizeof buf);
    p.textRight(230, 116, buf, 2, C_TEXT);
  } else {
    p.text(10, 116, "Mix: Menu>Adjust", 2, C_DIM);
  }

  // Channel bars: what each driver is actually receiving (perceptual scale).
  const int top = 146, H = 62;
  for (int i = 0; i < kCh; i++) {
    int x = 12 + i * 46;
    p.frame(x, top, 36, H, C_DIM);
    int h = (int)(color::yToL(st_.lin[i]) * (H - 2) + 0.5f);
    if (h > 0) p.fill(x + 1, top + H - 1 - h, 34, h, C_CH[i]);
    p.textCenter(x + 18, top + H + 6, kChShort[i], 2, C_DIM);
    drawnLin_[i] = st_.lin[i];
  }
  drawnmA_ = st_.mA;
  drawnLimited_ = st_.limited;
  drawnSleepMin_ = sleepMin;

  // One warning line; a missing encoder matters most.
  if (encMissing_) p.textCenter(kScreenW / 2, 231, "Encoder not found - check cable", 1, C_WARN);
  else if (storeMissing_) p.textCenter(kScreenW / 2, 231, "No flash FS: settings not saved", 1, C_WARN);
}

void Ui::itemValue(const Item& it, char* buf, int n) const {
  buf[0] = 0;
  switch (it.kind) {
    case Item::Num: formatValue(it.fmt, *it.v16, buf, n); break;
    case Item::Enum: snprintf(buf, n, "%s", *it.v8 < it.count ? it.names[*it.v8] : "?"); break;
    case Item::Sub: snprintf(buf, n, it.info[0] ? "%s >" : ">", it.info); break;
    case Item::Act: snprintf(buf, n, "%s", it.info); break;
    default: break;
  }
}

void Ui::drawMenu(Painter& p) {
  if (!depth_) return;
  const Frame& f = stack_[depth_ - 1];
  p.fill(0, 0, kScreenW, 30, C_HDR);
  p.text(8, 8, menu_.title, 2, C_ACCENT);

  char v[16];
  for (int r = 0; r < kRowsVisible; r++) {
    int idx = f.top + r;
    if (idx >= menu_.n) break;
    const Item& it = menu_.items[idx];
    int y = kRowY0 + r * kRowH;
    bool sel = idx == f.sel;
    if (sel) p.fill(0, y, 234, kRowH - 2, editing_ ? C_EDIT : C_SEL);
    p.text(8, y + 9, it.label, 2, it.kind == Item::Back ? C_DIM : C_TEXT);
    itemValue(it, v, sizeof v);
    if (v[0]) p.textRight(226, y + 9, v, 2, sel && editing_ ? C_TEXT : C_ACCENT);
    if (sel && editing_ && it.kind == Item::Num && it.hi > it.lo) {
      int w = 218 * (*it.v16 - it.lo) / (it.hi - it.lo);
      p.fill(8, y + kRowH - 6, w, 2, C_TEXT);
    }
  }
  if (menu_.n > kRowsVisible) {  // scroll bar
    int track = kRowsVisible * kRowH;
    int h = track * kRowsVisible / menu_.n;
    int y = kRowY0 + (track - h) * f.top / (menu_.n - kRowsVisible);
    p.fill(236, y, 3, h, C_DIM);
  }
}
