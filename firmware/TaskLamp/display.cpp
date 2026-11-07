#include "display.h"

#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>

#include "config.h"

// The frame is rendered in five 240x48 bands through one 23 KB canvas instead
// of a 115 KB full frame buffer. Each band is hashed after drawing; unchanged
// bands are never sent. A typical home-screen update (moving the brightness
// number) therefore pushes 1-2 bands (~5 ms) instead of the full screen
// (~25 ms), keeping SPI traffic, CPU time and power low, and because pixels
// are composed off-screen first there is no clear-then-draw flicker.
static constexpr int kBandH = 48;
static constexpr int kBands = kScreenH / kBandH;
static constexpr uint16_t kBg = 0x0000;

static Adafruit_ST7789 tft(&SPI, cfg::kTftCs, cfg::kTftDc, cfg::kTftRst);
static GFXcanvas16 band(kScreenW, kBandH);

namespace {
class CanvasPainter : public Painter {
 public:
  CanvasPainter(GFXcanvas16& c, int yOff) : c_(c), yOff_(yOff) {}
  void fill(int x, int y, int w, int h, uint16_t color) override {
    if (y + h <= yOff_ || y >= yOff_ + kBandH) return;  // not in this band
    c_.fillRect(x, y - yOff_, w, h, color);
  }
  void text(int x, int y, const char* s, uint8_t size, uint16_t color) override {
    if (y + 8 * size <= yOff_ || y >= yOff_ + kBandH) return;
    c_.setTextSize(size);
    c_.setTextColor(color);
    c_.setCursor(x, y - yOff_);
    c_.print(s);
  }

 private:
  GFXcanvas16& c_;
  int yOff_;
};

uint32_t hashBuffer(const uint16_t* p, size_t n) {  // FNV-1a over pixel pairs
  const uint32_t* w = (const uint32_t*)p;
  uint32_t h = 2166136261u;
  for (size_t i = 0; i < n / 2; i++) h = (h ^ w[i]) * 16777619u;
  return h;
}
}  // namespace

bool Display::begin() {
  SPI.setSCK(cfg::kSpiSck);
  SPI.setTX(cfg::kSpiMosi);
  tft.init(kScreenW, kScreenH);
  tft.setSPISpeed(cfg::kTftSpiHz);
  tft.setRotation(cfg::kTftRotation);
  tft.fillScreen(kBg);
  // The breakout resets itself at power-up, so no RST line is used (the
  // library sends a software reset instead). Note that SPI.begin() also
  // claims the MI pad (GP4) as SPI0 RX; the display is write-only, and
  // setup() reassigns that pad to the encoder INT input after this returns.
  band.setTextWrap(false);
  band.cp437(true);  // enables the degree sign (0xF8)
  invalidate();
  return band.getBuffer() != nullptr;
}

void Display::invalidate() {
  for (int b = 0; b < kBands; b++) valid_[b] = false;
}

int Display::render(DrawFn fn, void* ctx) {
  if (asleep_ || !band.getBuffer()) return 0;
  int pushed = 0;
  for (int b = 0; b < kBands; b++) {
    band.fillScreen(kBg);
    CanvasPainter p(band, b * kBandH);
    fn(p, ctx);
    uint32_t h = hashBuffer(band.getBuffer(), (size_t)kScreenW * kBandH);
    if (valid_[b] && h == hash_[b]) continue;
    tft.drawRGBBitmap(0, b * kBandH, band.getBuffer(), kScreenW, kBandH);
    hash_[b] = h;
    valid_[b] = true;
    pushed++;
  }
  return pushed;
}

void Display::setSleep(bool sleep) {
  if (sleep == asleep_) return;
  asleep_ = sleep;
  // Sleep-in cuts the controller to a few uA; GRAM is retained, but we redraw
  // anyway on wake because the UI usually changed (it returns to home).
  tft.enableSleep(sleep);
  if (!sleep) invalidate();
}
