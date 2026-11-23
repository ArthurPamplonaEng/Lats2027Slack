"""STM32 supervisor of the RV02A board over the ST-Link virtual COM port ($TEL firmware).

Protocol (from the D&T Monitor, legacy_link.py, validated on the bench in Nov 2026):
  * the firmware prints `$TEL,K,v,K,v,...*CS` four times per second at 125000 baud (CS = XOR of the
    characters between '$' and '*'): Vc (PMIC core voltage, V), Vi (input, V), Io (core current, A),
    Is (shunt current, A), Mc (latch-up current limit, A), Et (PMIC temperature), Mt (MCU), Sq (count)
  * FUNC_V sets the PMIC core voltage: 0x03, the voltage as 4 ASCII characters ("0.85"), CRC16-Modbus
    (low byte first). The firmware answers 3 bytes: (0x03 | err), CRC16 of that byte; err 0 = applied.
    The PMIC moves in 10 mV steps; the SYSMON reads ~25-30 mV above the commanded Vc.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from functools import reduce

import serial

FUNC_V = 0x03
RESP_ERRORS = {0x00: "applied", 0x10: "incomplete frame", 0x20: "bad CRC", 0x30: "bad length"}

# Bench limits for this experiment (PMIC command, not SYSMON). 0.92 V -> ~0.95 V on die, below the
# 1.00 V absolute maximum of DS931; 0.70 V -> ~0.73 V on die, above the configuration-retention level.
VC_MIN_V = 0.70
VC_MAX_V = 0.92


def crc16_modbus(data: bytes, crc: int = 0xFFFF) -> int:
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def func_v_frame(volts: float) -> bytes:
    text = f"{volts:.2f}"
    body = bytes([FUNC_V]) + text.encode("ascii")
    crc = crc16_modbus(body)
    return body + bytes([crc & 0xFF, crc >> 8])


def _response(code: int) -> bytes:
    crc = crc16_modbus(bytes([code]))
    return bytes([code, crc & 0xFF, crc >> 8])


RESPONSES = {_response(FUNC_V | e): e for e in RESP_ERRORS}


def parse_tel(line: str) -> dict[str, str] | None:
    line = line.strip()
    if not line.startswith("$TEL,") or "*" not in line:
        return None
    body, cs = line[1:].rsplit("*", 1)
    try:
        if reduce(lambda a, b: a ^ b, body.encode("ascii", "replace"), 0) != int(cs[:2], 16):
            return None
    except ValueError:
        return None
    items = body.split(",")[1:]
    return {items[i]: items[i + 1] for i in range(0, len(items) - 1, 2)}


@dataclass
class Telemetry:
    t: float = 0.0
    fields: dict = field(default_factory=dict)

    def f(self, key: str) -> float | None:
        try:
            return float(self.fields[key])
        except (KeyError, ValueError):
            return None


class Stm32Link:
    def __init__(self, port: str = "/dev/ttyACM1", baud: int = 125000, log=print):
        self.log = log
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baud
        self.ser.timeout = 0.05
        self.ser.dtr = False
        self.ser.rts = False
        self.ser.open()
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._acks: list[tuple[float, int]] = []
        self.tel = Telemetry()
        self.tel_count = 0
        self.other_lines: list[str] = []
        self._stop = False
        self._th = threading.Thread(target=self._reader, daemon=True)
        self._th.start()

    # ------------------------------------------------------------------ reader
    def _reader(self):
        while not self._stop:
            try:
                data = self.ser.read(4096)
            except (serial.SerialException, OSError) as e:
                self.log(f"STM32: read error {e}")
                time.sleep(0.5)
                continue
            if not data:
                continue
            now = time.time()
            with self._lock:
                self._buf.extend(data)
                # binary FUNC_V answers can sit anywhere in the text stream
                for resp, err in RESPONSES.items():
                    i = self._buf.find(resp)
                    while i >= 0:
                        self._acks.append((now, err))
                        del self._buf[i:i + 3]
                        i = self._buf.find(resp)
                while b"\n" in self._buf:
                    i = self._buf.index(b"\n")
                    line = self._buf[:i].decode("ascii", "replace").strip()
                    del self._buf[:i + 1]
                    if not line:
                        continue
                    tel = parse_tel(line)
                    if tel is not None:
                        self.tel = Telemetry(now, tel)
                        self.tel_count += 1
                    elif line.startswith("$"):
                        self.other_lines.append(line)
                        if line.startswith("$LEVT"):
                            self.log(f"STM32 !!! latch-up event line: {line}")
                if len(self._buf) > 65536:
                    del self._buf[:-4096]

    def close(self):
        self._stop = True
        self._th.join(timeout=1.0)
        self.ser.close()

    # ------------------------------------------------------------------ telemetry
    def wait_tel(self, timeout: float = 3.0) -> Telemetry:
        n0 = self.tel_count
        t0 = time.time()
        while self.tel_count == n0:
            if time.time() - t0 > timeout:
                raise TimeoutError("no $TEL line from the STM32")
            time.sleep(0.02)
        return self.tel

    # ------------------------------------------------------------------ core voltage
    def set_vcore(self, volts: float, tries: int = 3) -> float:
        v = round(volts, 2)
        if not VC_MIN_V <= v <= VC_MAX_V:
            raise ValueError(f"Vcore {v:.2f} V outside the bench limits {VC_MIN_V}-{VC_MAX_V} V")
        frame = func_v_frame(v)
        for k in range(tries):
            with self._lock:
                self._acks.clear()
            t_sent = time.time()
            self.ser.write(frame)
            ack = None
            while time.time() - t_sent < 1.5:
                with self._lock:
                    if self._acks:
                        ack = self._acks[-1][1]
                        break
                time.sleep(0.01)
            if ack is None:
                self.log(f"STM32: no answer to Vcore {v:.2f} V (try {k + 1})")
                continue
            if ack != 0:
                self.log(f"STM32: Vcore {v:.2f} V refused ({RESP_ERRORS.get(ack, hex(ack))})")
                continue
            # confirm on the PMIC readback of the next telemetry lines
            t0 = time.time()
            while time.time() - t0 < 2.5:
                tel = self.wait_tel(3.0)
                vc = tel.f("Vc")
                if tel.t > t_sent + 0.3 and vc is not None and abs(vc - v) <= 0.025:
                    return vc
            self.log(f"STM32: PMIC reads Vc={self.tel.f('Vc')} after Vcore {v:.2f} V (try {k + 1})")
        raise RuntimeError(f"Vcore {v:.2f} V not confirmed after {tries} tries")
