#include "storage.h"

#include <LittleFS.h>

static const char* kPath = "/lamp.bin";
static const char* kTmpPath = "/lamp.tmp";

namespace storage {

bool begin() { return LittleFS.begin(); }  // formats automatically on first use

bool load(Settings& s) {
  File f = LittleFS.open(kPath, "r");
  if (!f) return false;
  static Settings tmp;  // static: keep ~1 KB off the stack
  size_t n = f.read((uint8_t*)&tmp, sizeof(tmp));
  f.close();
  if (n != sizeof(tmp) || !settings::valid(tmp)) return false;
  settings::sanitize(tmp);
  settings::seal(tmp);
  s = tmp;
  return true;
}

bool save(const Settings& s) {
  File f = LittleFS.open(kTmpPath, "w");
  if (!f) return false;
  size_t n = f.write((const uint8_t*)&s, sizeof(s));
  f.close();
  if (n != sizeof(s)) return false;
  // LittleFS renames are atomic: a power cut leaves either the old or the new file.
  return LittleFS.rename(kTmpPath, kPath);
}

}  // namespace storage
