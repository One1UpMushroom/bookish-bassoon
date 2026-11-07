// Hardware configuration for the LED task lamp.
//
// Board: Adafruit QT Py RP2040 (arduino-pico core by Earle Philhower).
// All numbers below are RP2040 GPIO numbers, with the QT Py pad name beside them.
#pragma once
#include <stdint.h>

#define TASKLAMP_VERSION "1.0.0"

namespace cfg {

// ---------------------------------------------------------------------------
// LED channel outputs (hardware PWM). Order is R, G, B, Warm(amber), Cool.
//
// The pins are chosen so every LED channel gets its own PWM output and the
// pairs that share a PWM slice (R+G, B+WW) can be phase-shifted against each
// other (see pwm_hw.cpp). Do NOT reorder without checking the slice map:
//   GP29 = slice 6B, GP28 = 6A, GP27 = 5B, GP26 = 5A, GP20 = 2A, GP5 = 2B
// ---------------------------------------------------------------------------
constexpr uint8_t kLedPins[5] = {
    29,  // A0  -> Red driver
    28,  // A1  -> Green driver
    27,  // A2  -> Blue driver
    26,  // A3  -> Warm / amber white driver
    20,  // TX  -> Cool white driver
};

// ---------------------------------------------------------------------------
// 240x240 ST7789 TFT on hardware SPI0.
// ---------------------------------------------------------------------------
constexpr uint8_t kSpiSck = 6;   // SCK pad -> TFT SCK
constexpr uint8_t kSpiMosi = 3;  // MO  pad -> TFT MOSI (SI)
constexpr int8_t kTftCs = 24;    // SDA pad -> TFT TCS   (pad used as GPIO)
constexpr int8_t kTftDc = 25;    // SCL pad -> TFT D/C   (pad used as GPIO)
constexpr int8_t kTftRst = -1;   // not wired: the breakout has its own power-on reset chip
constexpr int8_t kTftBacklight = 5;     // RX  pad -> TFT Lite  (PWM 2B, dimmable)
constexpr uint32_t kTftSpiHz = 40000000;
constexpr uint8_t kTftRotation = 0;  // 0..3, rotate to suit the enclosure

// ---------------------------------------------------------------------------
// STEMMA QT port = I2C1 (Wire1) on GP22/GP23.
// ---------------------------------------------------------------------------
constexpr uint8_t kI2cSda = 22;
constexpr uint8_t kI2cScl = 23;
constexpr uint32_t kI2cHz = 400000;

constexpr uint8_t kEncAddr = 0x36;        // main encoder (default address)
constexpr uint8_t kEnc2Addr = 0x37;       // optional 2nd encoder (cut A0 jumper)
constexpr uint8_t kEncSwitchPin = 24;    // seesaw pin of the push switch
constexpr uint8_t kEncPixelPin = 6;   // seesaw pin of the on-board NeoPixel
// Encoder breakout INT pad -> QT Py MI pad (GP4). The seesaw pulls it low on
// rotation or a switch change, so idle polls cost a GPIO read instead of an
// I2C transaction. Optional: the firmware detects when it isn't wired and
// falls back to plain polling. Set to -1 to disable entirely.
constexpr int8_t kEncIntPin = 4;

// On-board QT Py NeoPixel: we keep it unpowered to save ~1 mA.
constexpr uint8_t kBoardPixelPower = 11;

// ---------------------------------------------------------------------------
// Timing
// ---------------------------------------------------------------------------
constexpr uint32_t kInputPollMs = 10;       // encoder poll while awake
constexpr uint32_t kInputPollIdleMs = 25;  // encoder poll while screen sleeps
constexpr uint32_t kEngineFastMs = 4;       // LED engine tick while animating (250 Hz)
constexpr uint32_t kEngineIdleMs = 20;      // LED engine tick while steady
constexpr uint32_t kUiFrameMs = 33;         // max display refresh (~30 fps)
constexpr uint32_t kUiLiveMs = 100;         // live-bar refresh on home screen
constexpr uint32_t kMenuTimeoutMs = 30000;  // menus fall back to home screen
constexpr uint32_t kSaveDelayMs = 5000;     // settings must be still this long before a flash write

}  // namespace cfg
