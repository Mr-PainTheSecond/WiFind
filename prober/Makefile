# Builds the prober sources with Espressif's ESP32 gcc.
#
# `make` compiles probe.cpp and main.cpp to object files in build/.
# Linking a flashable firmware image needs ESP-IDF's prebuilt libraries and
# startup code (an idf.py build), so `make link` is expected to fail with
# undefined references until those are available.

ROOT  := ..
IDF   := $(ROOT)/third_party/esp-idf/components
CXX   := $(ROOT)/third_party/toolchain/xtensa-esp-elf/bin/xtensa-esp32-elf-g++

INCLUDES := \
	-I. \
	-I$(ROOT)/third_party/esp-idf-config \
	-I$(IDF)/esp_wifi/include \
	-I$(IDF)/esp_wifi/include/local \
	-I$(IDF)/esp_common/include \
	-I$(IDF)/esp_event/include \
	-I$(IDF)/esp_hw_support/include \
	-I$(IDF)/esp_system/include \
	-I$(IDF)/esp_rom/include \
	-I$(IDF)/esp_netif/include \
	-I$(IDF)/heap/include \
	-I$(IDF)/newlib/platform_include \
	-I$(IDF)/soc/esp32/include \
	-I$(IDF)/xtensa/include \
	-I$(IDF)/xtensa/esp32/include \
	-I$(IDF)/freertos/FreeRTOS-Kernel/include \
	-I$(IDF)/freertos/FreeRTOS-Kernel/portable/xtensa/include/freertos \
	-I$(IDF)/freertos/config/include/freertos \
	-I$(IDF)/freertos/config/xtensa/include

CXXFLAGS := -std=gnu++2b -Os -Wall -Wextra -mlongcalls \
	-ffunction-sections -fdata-sections -fno-exceptions -fno-rtti

BUILD := build
SRCS  := probe.cpp main.cpp
OBJS  := $(SRCS:%.cpp=$(BUILD)/%.o)

.PHONY: all link clean

all: $(OBJS)

$(BUILD)/%.o: %.cpp probe.h | $(BUILD)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

$(BUILD):
	mkdir -p $(BUILD)

link: $(BUILD)/prober.elf

$(BUILD)/prober.elf: $(OBJS)
	$(CXX) $(OBJS) -o $@

clean:
	rm -rf $(BUILD)
