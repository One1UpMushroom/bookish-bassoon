Declaration-only stand-ins for the arduino-pico core, pico-sdk and Adafruit
library APIs used by the firmware's hardware layer. They let `make -C test check`
type-check `display.cpp`, `pwm_hw.cpp`, `storage.cpp` and `TaskLamp.ino` on a PC.
Signatures follow the real libraries; nothing here is linked or executed.
