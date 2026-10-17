"""Read CSI lines from the RX ESP32 (or from a recorded log file) and parse them.

Line formats are documented at the top of sensing/firmware/main/csi_main.c.
"""

from __future__ import annotations

import glob
import time
from dataclasses import dataclass
from typing import Iterator

import numpy as np

BAUD = 921600

# The classic ESP32 LLTF buffer holds 64 subcarriers in FFT order:
# index 0..31 = subcarriers 0..+31, index 32..63 = subcarriers -32..-1.
# Only -26..-1 and +1..+26 carry signal; the DC carrier (0) and the guard band
# edges are always ~0, so we drop them. We also skip +1 because the first
# 4 bytes of the buffer are sometimes invalid (hardware quirk), which covers
# subcarriers 0 and +1.
VALID_SUBCARRIERS = np.r_[2:27, 38:64]  # 25 + 26 = 51 subcarriers


@dataclass
class CsiFrame:
    host_time: float  # time.monotonic() when the line was read (seconds)
    seq: int  # 802.11 sequence number, wraps at 4096
    rssi: int  # dBm
    noise_floor: int  # dBm
    esp_time_us: int  # ESP32 receive timestamp, wraps at 2^32 us (~71 min)
    csi: np.ndarray  # complex64, one value per subcarrier (all 64)

    @property
    def amplitude(self) -> np.ndarray:
        """|H| for the 51 subcarriers that carry signal."""
        return np.abs(self.csi[VALID_SUBCARRIERS]).astype(np.float32)


def parse_line(line: str, host_time: float | None = None) -> CsiFrame | None:
    """Parse one `CSI,...` line. Returns None for any other or corrupted line."""
    line = line.strip()
    if not line.startswith("CSI,"):
        return None
    parts = line.split(",")
    if len(parts) != 7:
        return None
    try:
        seq, rssi, noise, ts, length = (int(p) for p in parts[1:6])
        raw = bytes.fromhex(parts[6])
    except ValueError:
        return None
    if len(raw) != length or length < 128:
        return None  # truncated line (serial hiccup)

    # Bytes are signed int8 pairs: (imaginary, real) per subcarrier.
    iq = np.frombuffer(raw[:128], dtype=np.int8).astype(np.float32).reshape(64, 2)
    csi = (iq[:, 1] + 1j * iq[:, 0]).astype(np.complex64)
    return CsiFrame(
        host_time=time.monotonic() if host_time is None else host_time,
        seq=seq,
        rssi=rssi,
        noise_floor=noise,
        esp_time_us=ts,
        csi=csi,
    )


def find_serial_ports() -> list[str]:
    """USB-serial ports that look like an ESP32 dev board on macOS/Linux."""
    patterns = [
        "/dev/cu.usbserial*",  # CP2102 / CH340 on macOS
        "/dev/cu.SLAB_USBtoUART*",  # CP2102 with the old Silicon Labs driver
        "/dev/cu.wchusbserial*",  # CH340 with the WCH driver
        "/dev/cu.usbmodem*",  # boards with native USB (ESP32-S3)
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
    ]
    ports: list[str] = []
    for pattern in patterns:
        ports.extend(sorted(glob.glob(pattern)))
    return ports


def resolve_port(port: str | None) -> str:
    if port:
        return port
    ports = find_serial_ports()
    if not ports:
        raise SystemExit(
            "No ESP32 serial port found. Plug the RX board in with a DATA USB cable "
            "(charge-only cables are common) and run `ls /dev/cu.*`."
        )
    if len(ports) > 1:
        print(f"Several ports found {ports}; using {ports[0]}. Pass --port to choose.")
    return ports[0]


def iter_lines(port: str | None = None, replay: str | None = None) -> Iterator[tuple[float, str]]:
    """Yield (host_time, line) from the serial port, or from a recorded file.

    Recorded files (from record.py) store `host_time<TAB>line` so replays keep
    the original timing.
    """
    if replay:
        with open(replay) as f:
            for row in f:
                if row.startswith("#") or "\t" not in row:
                    continue
                t, line = row.rstrip("\n").split("\t", 1)
                yield float(t), line
        return

    import serial  # pyserial; imported here so replay/tests don't need it

    with serial.Serial(resolve_port(port), BAUD, timeout=1) as ser:
        ser.reset_input_buffer()
        while True:
            # readline() returns b"" after the 1 s timeout; we still yield it so
            # callers can notice "no data" and stop waiting.
            raw = ser.readline()
            yield time.monotonic(), raw.decode("ascii", errors="replace")


def iter_frames(port: str | None = None, replay: str | None = None) -> Iterator[CsiFrame]:
    for t, line in iter_lines(port, replay):
        frame = parse_line(line, host_time=t)
        if frame is not None:
            yield frame


def add_port_args(parser) -> None:
    parser.add_argument("--port", help="serial port of the RX board (default: auto-detect)")
    parser.add_argument("--replay", help="read a file saved by record.py instead of the board")


def collect(frames: Iterator[CsiFrame], seconds: float) -> tuple[np.ndarray, np.ndarray]:
    """Read frames for `seconds`; return (host_times, amplitudes frames x subcarriers)."""
    times, amps = [], []
    start = None
    for frame in frames:
        if start is None:
            start = frame.host_time
        if frame.host_time - start >= seconds:
            break
        times.append(frame.host_time)
        amps.append(frame.amplitude)
    if not amps:
        raise SystemExit("No CSI frames received. Run check_link.py first.")
    return np.array(times), np.array(amps)
