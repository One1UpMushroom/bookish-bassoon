# Host-side tests for the task lamp firmware.
#   make -C test          build + run unit tests (with ASan/UBSan)
#   make -C test check    also compile the hardware layer against API stubs
FW := ../firmware/TaskLamp
CXX ?= g++
CXXFLAGS := -std=gnu++17 -O1 -g -Wall -Wextra -Wno-unused-parameter \
            -fsanitize=address,undefined -fno-omit-frame-pointer -I$(FW)
PURE := $(FW)/color.cpp $(FW)/settings.cpp $(FW)/engine.cpp $(FW)/output.cpp \
        $(FW)/input.cpp $(FW)/ui.cpp

.PHONY: test check clean
test: host_tests
	./host_tests

host_tests: host_tests.cpp $(PURE) $(wildcard $(FW)/*.h)
	$(CXX) $(CXXFLAGS) -o $@ host_tests.cpp $(PURE)

# Syntax/type check of the Arduino-facing files against minimal stubs of the
# arduino-pico / Adafruit APIs they use. Not a substitute for a real build.
check: test
	for f in $(FW)/display.cpp $(FW)/pwm_hw.cpp $(FW)/storage.cpp; do \
	  $(CXX) -std=gnu++17 -Wall -Wextra -fsyntax-only -Istubs -I$(FW) $$f || exit 1; done
	$(CXX) -std=gnu++17 -Wall -Wextra -fsyntax-only -Istubs -I$(FW) -x c++ $(FW)/TaskLamp.ino
	@echo "hardware layer: syntax OK"

clean:
	rm -f host_tests
