# Thin wrapper around ESP-IDF's idf.py for the prober firmware.
#
# Run from a shell where C:\esp\esp-idf\export.ps1 has been sourced, so that
# idf.py and the ESP32 toolchain are on PATH. Set PORT to the board's COM port
# for flashing, e.g. `mingw32-make flash PORT=COM3`.

PORT ?= COM3

.PHONY: all flash monitor clean

all:
	idf.py build

flash:
	idf.py -p $(PORT) flash

monitor:
	idf.py -p $(PORT) monitor

clean:
	idf.py fullclean
