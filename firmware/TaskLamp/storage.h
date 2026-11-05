// Settings persistence on the QT Py's flash (LittleFS, wear-levelled and
// power-loss safe). Runs on core 0.
#pragma once
#include "settings.h"

namespace storage {
bool begin();
bool load(Settings& s);        // false -> caller keeps defaults
bool save(const Settings& s);  // write-to-temp + atomic rename
}  // namespace storage
