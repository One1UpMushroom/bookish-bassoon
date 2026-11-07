// LED Task Lamp controller
// ------------------------
// Adafruit QT Py RP2040 + STEMMA QT rotary encoder + 240x240 ST7789 TFT
// driving five LED channels (R, G, B, warm/amber white, cool white).
//
// Core 0: encoder polling, UI, display, settings persistence.
// Core 1: light engine + PWM output. Keeps fades and effects perfectly smooth
//         no matter what the display or flash is doing.
//
// The two cores share one EngineInput snapshot (core 0 -> core 1) and one
// LampStatus (core 1 -> core 0), each guarded by a mutex that is only held for
// a memcpy. Core 1 never blocks on it.
//
// Build: arduino-pico core ("Raspberry Pi Pico/RP2040" by Earle Philhower),
// board "Adafruit QT Py RP2040", Flash Size with at least 64 KB FS.
// Libraries: Adafruit seesaw, Adafruit ST7735 and ST7789, Adafruit GFX.

#include <Adafruit_seesaw.h>
#include <Arduino.h>
#include <Wire.h>
#include <pico/mutex.h>
#include <seesaw_neopixel.h>

#include "color.h"
#include "config.h"
#include "display.h"
#include "engine.h"
#include "input.h"
#include "output.h"
#include "pwm_hw.h"
#include "settings.h"
#include "storage.h"
#include "ui.h"

// ===========================================================================
// Shared between cores
// ===========================================================================
auto_init_mutex(gLock);
static EngineInput gShared;           // core0 -> core1, under gLock
static volatile uint32_t gSharedGen;  // bumped after each publish
static LampStatus gStatus;            // core1 -> core0, under gLock
static volatile float gBacklight;     // desired TFT backlight 0..1 (linear)
static volatile bool gCore0Ready;
static volatile uint32_t gCore1Beat;  // core 1 heartbeat for the watchdog

// ===========================================================================
// Core 0
// ===========================================================================
// Thin subclass so we can use seesaw's error-checked register reads.
class Knob : public Adafruit_seesaw {
 public:
  explicit Knob(TwoWire* w) : Adafruit_seesaw(w) {}
  // Returns false on any I2C error, so a loose cable can never be mistaken
  // for a held button (which would toggle the lamp).
  bool sample(int32_t& delta, bool& pressed) {
    uint8_t b[4];
    if (!read(SEESAW_ENCODER_BASE, SEESAW_ENCODER_DELTA, b, 4)) return false;
    delta = (int32_t)(((uint32_t)b[0] << 24) | ((uint32_t)b[1] << 16) | ((uint32_t)b[2] << 8) | b[3]);
    if (!read(SEESAW_GPIO_BASE, SEESAW_GPIO_BULK, b, 4)) return false;
    uint32_t pins = ((uint32_t)b[0] << 24) | ((uint32_t)b[1] << 16) | ((uint32_t)b[2] << 8) | b[3];
    pressed = !(pins & (1ul << cfg::kEncSwitchPin));  // switch pulls to GND
    return true;
  }
  // Reading the GPIO interrupt flags releases INT after a switch change
  // (reading the encoder delta already releases it after rotation).
  void clearIntFlags() {
    uint8_t b[4];
    read(SEESAW_GPIO_BASE, SEESAW_GPIO_INTFLAG, b, 4);
  }
  bool connect(uint8_t addr) {
    if (!begin(addr, -1, false)) return false;
    // PID 4991 = encoder breakout, 5880 = same board with the encoder
    // pre-soldered. Anything else that answered is still a seesaw with an
    // encoder input, so warn instead of refusing it.
    uint16_t pid = (getVersion() >> 16) & 0xFFFF;
    if (pid != 4991 && pid != 5880) {
      Serial.print("seesaw: unexpected product id ");
      Serial.println(pid);
    }
    pinMode(cfg::kEncSwitchPin, INPUT_PULLUP);
    if (cfg::kEncIntPin >= 0) {  // drive INT on rotation and on switch changes
      setGPIOInterrupts(1ul << cfg::kEncSwitchPin, true);
      enableEncoderInterrupt();
    }
    int32_t d;
    bool p;
    bool ok = sample(d, p);  // also clears any stale delta
    clearIntFlags();
    return ok;
  }
};

static Settings gSettings;
static Runtime gRuntime;
static Ui gUi;
static Display gDisplay;
static Knob gKnob(&Wire1), gKnob2(&Wire1);
static seesaw_NeoPixel gKnobPixel(1, cfg::kEncPixelPin, NEO_GRB + NEO_KHZ800, &Wire1);
static Gestures gGest(0), gGest2(1);
static bool gKnobOk, gKnob2Ok;
static uint8_t gKnobErrors;
static uint32_t gKnobRetryAt;
static uint32_t gLastGlow = 0xFFFFFFFF;
static settings::SaveScheduler gSaver;
static bool gStorageOk;
static IntGate gGate(cfg::kEncIntPin >= 0);
static bool gLastPressed;
static volatile bool gIntFlag;  // latched by the INT edge, so short pulses aren't missed

static void onEncoderInt() { gIntFlag = true; }

// The breakout mounts its encoder at 45 degrees, which makes it count
// negative for clockwise turns (Adafruit guide). Flip it so clockwise means
// "more"; the Knob dir setting is a further user override.
static int32_t orient(int32_t d) { return gSettings.hw.knobReverse ? d : -d; }

static void publish() {
  mutex_enter_blocking(&gLock);
  gShared.s = gSettings;
  gShared.rt = gRuntime;
  gSharedGen = gSharedGen + 1;
  mutex_exit(&gLock);
}

static void connectKnobs() {
  // The NeoPixel driver's begin() resets the seesaw chip, so it goes first.
  gKnobOk = gKnobPixel.begin(cfg::kEncAddr) && gKnob.connect(cfg::kEncAddr);
  if (gKnobOk) gLastGlow = 0xFFFFFFFF;  // force the glow colour to be re-sent
  gKnob2Ok = gKnob2.connect(cfg::kEnc2Addr);  // optional brightness/power knob
  gKnobErrors = 0;
  gUi.setEncoderMissing(!gKnobOk);
}

static void pollKnobs(uint32_t now) {
  if (!gKnobOk) {
    if ((int32_t)(now - gKnobRetryAt) >= 0) {  // hot-plug: retry every 2 s
      gKnobRetryAt = now + 2000;
      connectKnobs();
    }
    return;
  }
  int32_t d = 0;
  bool pressed = false;
  gGest.enableDoubleClick(gUi.wantDoubleClick());
  bool intAsserted =
      cfg::kEncIntPin >= 0 && (gIntFlag || digitalRead(cfg::kEncIntPin) == LOW);
  bool held = gLastPressed || gGest.held();
  if (!gGate.shouldRead(now, intAsserted, held)) {
    gGest.update(now, gLastPressed, 0);  // nothing new: keep gesture timers running
  } else {
    gIntFlag = false;  // cleared before the read, so an edge during it is kept
    if (gKnob.sample(d, pressed)) {
      if (intAsserted) gKnob.clearIntFlags();
      gKnobErrors = 0;
      d = orient(d);
      gGate.afterRead(now, intAsserted, held, d != 0 || pressed != gLastPressed);
      gLastPressed = pressed;
      gGest.update(now, pressed, d);
    } else if (++gKnobErrors >= 3) {
      gKnobOk = false;
      gLastPressed = false;
      gGest.update(now, false, 0);
      gGest.update(now, false, 0);  // two samples: debounced release
      gUi.setEncoderMissing(true);
    }
  }
  // The optional second knob has no INT wire, so it is simply polled.
  if (gKnob2Ok && gKnob2.sample(d, pressed)) gGest2.update(now, pressed, orient(d));
}

static void drawUi(Painter& p, void*) { gUi.draw(p); }

void setup() {
  // The TFT breakout pulls its backlight (Lite) high, which would show the
  // display's power-up garbage at full brightness. Hold it dark until core 1
  // takes the pin over as PWM and fades it in.
  if (cfg::kTftBacklight >= 0) {
    pinMode(cfg::kTftBacklight, OUTPUT);
    digitalWrite(cfg::kTftBacklight, LOW);
  }
  Serial.begin(115200);

  // Unpowered on-board NeoPixel: saves current, and its light is useless here.
  pinMode(cfg::kBoardPixelPower, OUTPUT);
  digitalWrite(cfg::kBoardPixelPower, LOW);

  settings::defaults(gSettings);
  // Fails when the board was built with "Flash Size: ... (no FS)", which is
  // the Arduino IDE default for this board: then warn on screen, don't save.
  gStorageOk = storage::begin();
  if (!(gStorageOk && storage::load(gSettings))) settings::defaults(gSettings);
  gSaver.markSaved(settings::computeCrc(gSettings));

  memset(&gRuntime, 0, sizeof(gRuntime));
  gRuntime.on = 1;  // a lamp switched on at the wall should light up

  // GP22/GP23 (the STEMMA QT port) can only be routed to the RP2040's I2C1
  // block, which arduino-pico exposes as Wire1. (The QT Py guide names the
  // port inconsistently; the hardware mapping is what counts.)
  Wire1.setSDA(cfg::kI2cSda);
  Wire1.setSCL(cfg::kI2cScl);
  Wire1.begin();
  Wire1.setClock(cfg::kI2cHz);

  gDisplay.begin();
  gUi.begin(&gSettings, &gRuntime, millis());
  gUi.setStorageMissing(!gStorageOk);
  if (cfg::kEncIntPin >= 0) {
    pinMode(cfg::kEncIntPin, INPUT_PULLUP);  // seesaw INT is active low
    attachInterrupt(digitalPinToInterrupt(cfg::kEncIntPin), onEncoderInt, FALLING);
  }
  connectKnobs();
  publish();
  gCore0Ready = true;

  rp2040.wdt_begin(4000);  // reboot if either core ever hangs
}

void loop() {
  static uint32_t lastFrame = 0, lastBeat = 0;
  uint32_t now = millis();

  pollKnobs(now);
  InputEvent e;
  while (gGest.next(e) || gGest2.next(e)) gUi.handle(e, now);

  LampStatus st;
  mutex_enter_blocking(&gLock);
  st = gStatus;
  mutex_exit(&gLock);
  gUi.update(now, st);

  bool sChanged = gUi.takeSettingsChanged();
  bool rChanged = gUi.takeRuntimeChanged();
  if (sChanged) gSaver.touch(now);
  if (sChanged || rChanged) publish();

  gDisplay.setSleep(gUi.displayAsleep());
  gBacklight = gUi.backlight();
  if (!gDisplay.asleep() && now - lastFrame >= cfg::kUiFrameMs && gUi.takeRedraw()) {
    gDisplay.render(drawUi, nullptr);
    lastFrame = now;
  }

  uint32_t glow = gUi.knobGlow();
  if (gKnobOk && glow != gLastGlow) {
    gKnobPixel.setPixelColor(0, glow);
    gKnobPixel.show();
    gLastGlow = glow;
  }

  // Flash wear: only write after 5 s without changes, and only if different.
  if (gStorageOk && gSaver.pending() && gSaver.due(now, settings::computeCrc(gSettings), cfg::kSaveDelayMs)) {
    settings::seal(gSettings);
    if (storage::save(gSettings)) gSaver.markSaved(gSettings.crc);
    else gSaver.touch(now);  // try again later
  }

  // Feed the watchdog only while core 1 is alive too.
  if (gCore1Beat != lastBeat) {
    lastBeat = gCore1Beat;
    rp2040.wdt_reset();
  }

  delay(gUi.displayAsleep() ? cfg::kInputPollIdleMs : cfg::kInputPollMs);
}

// ===========================================================================
// Core 1
// ===========================================================================
static LightEngine gEngine;
static OutputStage gOut;
static PwmBank gPwm;
static EngineInput gIn1;  // core 1's private copy (static: core 1 stack is small)
static uint32_t gGen1;
static uint16_t gAppliedHz;
static uint8_t gAppliedInvert[kCh];

static void applyHw(const HwCfg& hw, bool force) {
  if (force || hw.pwmHz != gAppliedHz || memcmp(hw.chInvert, gAppliedInvert, kCh) != 0) {
    gPwm.begin(hw.pwmHz, hw.chInvert);
    gAppliedHz = hw.pwmHz;
    memcpy(gAppliedInvert, hw.chInvert, kCh);
  }
  gOut.configure(hw, gPwm.top());
}

void setup1() {
  while (!gCore0Ready) delay(1);
  mutex_enter_blocking(&gLock);
  gIn1 = gShared;
  gGen1 = gSharedGen;
  mutex_exit(&gLock);
  applyHw(gIn1.s.hw, true);
  gEngine.begin(gIn1, millis());
}

void loop1() {
  static float blCur = 0.f;
  static uint32_t last = millis();
  uint32_t now = millis();
  uint32_t dt = now - last;
  last = now;

  if (gSharedGen != gGen1) {
    mutex_enter_blocking(&gLock);
    gIn1 = gShared;
    gGen1 = gSharedGen;
    mutex_exit(&gLock);
    applyHw(gIn1.s.hw, false);
    gEngine.apply(gIn1, now);
  }

  Rgbww lin;
  gEngine.tick(now, lin);
  OutputResult r;
  gOut.process(lin, r);
  gPwm.write(r.level);

  if (mutex_try_enter(&gLock, nullptr)) {  // never stall the light for the UI
    for (int i = 0; i < kCh; i++) gStatus.lin[i] = r.lin[i];
    gStatus.mA = r.mA;
    gStatus.limited = r.limited;
    gStatus.masterL = gEngine.masterL();
    mutex_exit(&gLock);
  }

  // Backlight glides instead of jumping when the screen dims or wakes.
  float target = gBacklight;
  float k = dt >= 150 ? 1.f : dt / 150.f;
  blCur += (target - blCur) * k;
  if (fabsf(target - blCur) < 0.001f) blCur = target;
  gPwm.setBacklight(blCur);

  gCore1Beat = gCore1Beat + 1;
  bool busy = gEngine.busy() || blCur != target;
  delay(busy ? cfg::kEngineFastMs : cfg::kEngineIdleMs);
}
