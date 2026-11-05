// Minimal drawing interface used by the UI. The firmware implementation draws
// into an off-screen band buffer (display.cpp); host tests use a recorder.
#pragma once
#include <stdint.h>
#include <string.h>

constexpr int kScreenW = 240;
constexpr int kScreenH = 240;

constexpr uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return (uint16_t)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
}

class Painter {
 public:
  virtual ~Painter() {}
  virtual void fill(int x, int y, int w, int h, uint16_t color) = 0;
  // Built-in 5x7 font scaled by `size` (char cell = 6*size x 8*size px).
  virtual void text(int x, int y, const char* s, uint8_t size, uint16_t color) = 0;

  void frame(int x, int y, int w, int h, uint16_t c) {
    fill(x, y, w, 1, c);
    fill(x, y + h - 1, w, 1, c);
    fill(x, y, 1, h, c);
    fill(x + w - 1, y, 1, h, c);
  }
  static int textWidth(const char* s, uint8_t size) {
    int n = (int)strlen(s);
    return n ? n * 6 * size - size : 0;
  }
  void textRight(int xr, int y, const char* s, uint8_t size, uint16_t c) {
    text(xr - textWidth(s, size), y, s, size, c);
  }
  void textCenter(int cx, int y, const char* s, uint8_t size, uint16_t c) {
    text(cx - textWidth(s, size) / 2, y, s, size, c);
  }
};
