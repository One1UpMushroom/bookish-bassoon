#pragma once
#include "Arduino.h"
class File {
 public:
  operator bool() const;
  size_t read(uint8_t* buf, size_t size);
  size_t write(const uint8_t* buf, size_t size);
  void close();
};
class FS {
 public:
  bool begin();
  File open(const char* path, const char* mode);
  bool rename(const char* from, const char* to);
};
extern FS LittleFS;
