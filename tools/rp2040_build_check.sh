#!/bin/bash
# Full build of firmware/TaskLamp outside the Arduino IDE: core + libraries +
# sketch, linked to an ELF, following the recipes in arduino-pico's platform.txt
# for "Adafruit QT Py RP2040", Flash Size 8MB (Sketch 7MB, FS 1MB), defaults.
# It proves the sketch builds against the real APIs; it does not replace the
# Arduino IDE for making the file you flash.
#
# Needs three things, all from GitHub:
#   PICO_CORE     unpacked arduino-pico release, e.g. rp2040-6.3.2/
#                 (github.com/earlephilhower/arduino-pico/releases, the rp2040-<ver>.zip asset)
#   PICO_GCC_BIN  bin/ of its compiler
#                 (github.com/earlephilhower/pico-quick-toolchain/releases, the arm-none-eabi tarball)
#   ARDUINO_LIBS  folder holding clones of adafruit/Adafruit_Seesaw,
#                 adafruit/Adafruit-ST7735-Library, adafruit/Adafruit-GFX-Library, adafruit/Adafruit_BusIO
#
#   PICO_CORE=... PICO_GCC_BIN=... ARDUINO_LIBS=... tools/rp2040_build_check.sh [out_dir]
set -u
: "${PICO_CORE:?set PICO_CORE}" "${PICO_GCC_BIN:?set PICO_GCC_BIN}" "${ARDUINO_LIBS:?set ARDUINO_LIBS}"
P=$PICO_CORE; BIN=$PICO_GCC_BIN; L=$ARDUINO_LIBS
SK="$(cd "$(dirname "$0")/.." && pwd)/firmware/TaskLamp"
OUT=${1:-$(mktemp -d)}
mkdir -p "$OUT"/{sketch,core,libs}
GFX="$L/Adafruit-GFX-Library"; [ -d "$GFX/src" ] && GFX="$GFX/src"   # sources moved to src/ in 1.13
DEFS=(-DUSBD_PID=0x80f7 -DUSBD_VID=0x239a -DUSBD_MAX_POWER_MA=250 '-DUSB_MANUFACTURER="Adafruit"' '-DUSB_PRODUCT="QT Py RP2040"'
  -DLWIP_IPV6=0 -DLWIP_IPV4=1 -DLWIP_IGMP=1 -DLWIP_CHECKSUM_CTRL_PER_NETIF=1
  -DFILE_COPY_CONSTRUCTOR_SELECT=FILE_COPY_CONSTRUCTOR_PUBLIC -DUSE_UTF8_LONG_NAMES=1 -DDISABLE_FS_H_WARNING=1
  '-DARDUINO_VARIANT="adafruit_qtpy"' -DPICO_FLASH_SIZE_BYTES=8388608 -DFS_START=275771392 -DFS_END=276819968
  "@$P/lib/platform_def.txt" "@$P/lib/rp2040/platform_def.txt")
LIBDIRS=("$P/libraries/SPI/src" "$P/libraries/Wire/src" "$P/libraries/LittleFS/src"
  "$L/Adafruit_Seesaw" "$L/Adafruit-ST7735-Library" "$GFX" "$L/Adafruit_BusIO")
INCS=("-iprefix$P/" "@$P/lib/rp2040/platform_inc.txt" "@$P/lib/core_inc.txt" "-I$P/include"
  "-I$P/cores/rp2040" "-I$P/variants/adafruit_qtpy")
for d in "${LIBDIRS[@]}"; do INCS+=("-I$d"); done
ARCH=(-march=armv6-m -mcpu=cortex-m0plus -mthumb)
ID=(-DF_CPU=200000000L -DARDUINO=10819 -DARDUINO_ADAFRUIT_QTPY_RP2040 '-DBOARD_NAME="ADAFRUIT_QTPY_RP2040"' -DARDUINO_ARCH_RP2040)
COMMON=(-Werror=return-type -Wno-psabi "${DEFS[@]}" "${ARCH[@]}" -ffunction-sections -fdata-sections -fno-exceptions "${ID[@]}" -Os)
CXXF=(-c "${COMMON[@]}" "${INCS[@]}" -fno-rtti -std=gnu++23 -g -pipe -Wno-volatile -DWIFICC=CYW43_COUNTRY_WORLDWIDE -I "$OUT/core")
CF=(-c "${COMMON[@]}" "${INCS[@]}" -std=gnu23 -g -pipe -I "$OUT/core")
SF=(-c -Werror=return-type -Wno-psabi "${DEFS[@]}" -g -x assembler-with-cpp "${INCS[@]}" "${ARCH[@]}" "${ID[@]}")

python3 -I "$P/tools/signing.py" --mode header --publickey "$SK/public.key" --out "$OUT/core/Updater_Signing.h" >/dev/null 2>&1 \
  || echo '#define ARDUINO_SIGNING 0' > "$OUT/core/Updater_Signing.h"

: > "$OUT/build.log"
cc() {  # cc <src> <obj> [extra flags]
  local src=$1 obj=$2; shift 2
  case "$src" in
    *.cpp) "$BIN/arm-none-eabi-g++" "${CXXF[@]}" "$@" "$src" -o "$obj" 2>>"$OUT/build.log" ;;
    *.c)   "$BIN/arm-none-eabi-gcc" "${CF[@]}" "$src" -o "$obj" 2>>"$OUT/build.log" ;;
    *.S)   "$BIN/arm-none-eabi-gcc" "${SF[@]}" "$src" -o "$obj" 2>>"$OUT/build.log" ;;
  esac || echo "FAIL $src" >> "$OUT/build.log"
}

# sketch, with warnings on
cp "$SK"/*.h "$SK"/*.cpp "$OUT/sketch/"
INO=$(ls "$SK"/*.ino | head -1)
{ echo '#include <Arduino.h>'; echo "#line 1 \"$(basename "$INO")\""; cat "$INO"; } > "$OUT/sketch/$(basename "$INO").cpp"
SK_OBJS=()
for f in "$OUT"/sketch/*.cpp; do cc "$f" "$f.o" -Wall -Wextra -Wno-type-limits & SK_OBJS+=("$f.o"); done; wait

LIB_OBJS=(); n=0
for d in "${LIBDIRS[@]}"; do
  for f in "$d"/*.cpp "$d"/*.c; do
    [ -f "$f" ] || continue
    o="$OUT/libs/$(echo "$d" | tr '/' '_')_$(basename "$f").o"
    cc "$f" "$o" & LIB_OBJS+=("$o"); n=$((n + 1)); [ $((n % 8)) -eq 0 ] && wait
  done
done; wait

CORE_OBJS=()
while IFS= read -r f; do
  o="$OUT/core/$(echo "${f#$P/cores/rp2040/}" | tr '/' '_').o"
  cc "$f" "$o" & CORE_OBJS+=("$o"); n=$((n + 1)); [ $((n % 8)) -eq 0 ] && wait
done < <(find "$P/cores/rp2040" -type f \( -name '*.cpp' -o -name '*.c' -o -name '*.S' \) | sort)
wait
"$BIN/arm-none-eabi-ar" rcs "$OUT/core.a" "${CORE_OBJS[@]}" 2>>"$OUT/build.log"

python3 -I "$P/tools/simplesub.py" --input "$P/lib/rp2040/memmap_default.ld" --out "$OUT/memmap_default.ld" \
  --sub __FLASH_LENGTH__ 7335936 --sub __EEPROM_START__ 276819968 --sub __FS_START__ 275771392 \
  --sub __FS_END__ 276819968 --sub __RAM_LENGTH__ 256k --sub __PSRAM_LENGTH__ 0 >>"$OUT/build.log" 2>&1
ELFF=(-Werror=return-type -Wno-psabi "${DEFS[@]}" "${ARCH[@]}" -ffunction-sections -fdata-sections -fno-exceptions -Os -u _printf_float -u _scanf_float)
"$BIN/arm-none-eabi-gcc" "${ELFF[@]}" -c "$P/boot2/rp2040/boot2_w25q080_2_padded_checksum.S" \
  "-I$P/pico-sdk/src/rp2040/hardware_regs/include/" "-I$P/pico-sdk/src/common/pico_binary_info/include" -o "$OUT/boot2.o" 2>>"$OUT/build.log"
WRAP=("@$P/lib/rp2040/platform_wrap.txt" "@$P/lib/core_wrap.txt")
for w in "$P"/cores/rp2040/lwip-wrappers/wrap_*_wraps.inc; do WRAP+=("@$w"); done
grep -o 'Wl,--undefined=[A-Za-z0-9_]*' "$P/platform.txt" | sort -u | sed 's/^/-/' > "$OUT/undef.txt"
"$BIN/arm-none-eabi-g++" "-L$OUT" "${ELFF[@]}" "${WRAP[@]}" -Wl,--cref -Wl,--check-sections -Wl,--gc-sections \
  -Wl,--unresolved-symbols=report-all -Wl,--warn-common "@$OUT/undef.txt" \
  "-Wl,--script=$OUT/memmap_default.ld" "-Wl,-Map,$OUT/TaskLamp.map" -o "$OUT/TaskLamp.elf" -Wl,--no-warn-rwx-segments \
  -Wl,--start-group "${SK_OBJS[@]}" "${LIB_OBJS[@]}" "$OUT/core.a" "$OUT/boot2.o" "$P/lib/rp2040/ota.o" \
  "$P/lib/rp2040/libpico.a" "$P/lib/rp2040/liblwip.a" "$P/lib/rp2040/libbearssl.a" -lm -lc -lstdc++ -lc -Wl,--end-group \
  2>>"$OUT/build.log"
rc=$?
fails=$(grep -c '^FAIL' "$OUT/build.log")
warns=$(grep -c 'sketch/.*warning:' "$OUT/build.log")
echo "compile failures: $fails   sketch warnings: $warns   link exit: $rc   (log: $OUT/build.log)"
[ $rc -eq 0 ] && [ "$fails" -eq 0 ] && "$BIN/arm-none-eabi-size" "$OUT/TaskLamp.elf"
[ $rc -eq 0 ] && [ "$fails" -eq 0 ]
