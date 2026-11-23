#!/usr/bin/env python3
"""Oven controller (Arduino Nano 33 IoT, PID firmware of SBCCI 2026) for the tap bench.

    python3 -I bench/oven.py status
    python3 -I bench/oven.py hold --sp 60 --minutes 240      # runs the PID, logs every 2 s
    python3 -I bench/oven.py stop

Protocol (115200 baud, one line per command): GET_CONFIG, SET_SP,<int degC>, START_TEST,
GET_DATA -> DATA,<temp>,<ramp setpoint>,<output %>, STOP_TEST. The firmware only re-reads its NTC
during a test. `hold` ALWAYS ends with STOP_TEST (normal end, error, Ctrl+C, SIGTERM) and refuses
setpoints above 90 C; it stops by itself if the air passes setpoint + 15 C or 110 C.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import signal
import sys
import time

import serial

PORT = "/dev/serial/by-id/usb-Arduino_LLC_Arduino_NANO_33_IoT_40C381DB51544C3954202020FF082015-if00"
BAUD = 115200
SP_MAX = 90
AIR_LIMIT = 110.0
LOGDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "au15p_tap")


class Oven:
    def __init__(self, port: str = PORT):
        self.ser = serial.Serial(port, BAUD, timeout=2, write_timeout=1)
        time.sleep(0.2)

    def cmd(self, c: str) -> str:
        self.ser.reset_input_buffer()
        self.ser.write(f"{c}\n".encode())
        return self.ser.readline().decode("ascii", "ignore").strip()

    def data(self):
        line = self.cmd("GET_DATA")
        if not line.startswith("DATA,"):
            return None
        p = line.split(",")
        try:
            return float(p[1]), float(p[2]), float(p[3])
        except (IndexError, ValueError):
            return None

    def stop(self) -> str:
        for _ in range(3):
            try:
                return self.cmd("STOP_TEST")
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        return ""

    def close(self):
        try:
            self.ser.close()
        except Exception:  # noqa: BLE001
            pass


def _sig(signum, _frame):
    raise KeyboardInterrupt(f"signal {signum}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "hold", "stop"])
    ap.add_argument("--sp", type=float, default=25.0)
    ap.add_argument("--minutes", type=float, default=60.0)
    ap.add_argument("--port", default=PORT)
    a = ap.parse_args()
    ov = Oven(a.port)
    try:
        if a.cmd == "status":
            print("CONFIG:", ov.cmd("GET_CONFIG"))
            print("DATA:", ov.cmd("GET_DATA"), "(outside a test this is the boot reading)")
        elif a.cmd == "stop":
            print("STOP_TEST:", ov.stop())
        else:
            if a.sp > SP_MAX:
                sys.exit(f"setpoint {a.sp} above the bench limit {SP_MAX} C")
            signal.signal(signal.SIGTERM, _sig)
            signal.signal(signal.SIGHUP, _sig)
            os.makedirs(LOGDIR, exist_ok=True)
            path = os.path.join(LOGDIR, f"oven_{dt.datetime.now():%Y%m%d_%H%M%S}_sp{a.sp:.0f}.csv")
            with open(path, "w") as f:
                f.write("pc_time,t_s,air_c,ramp_sp_c,output_pct\n")
                print("CONFIG:", ov.cmd("GET_CONFIG"), flush=True)
                print("SET_SP:", ov.cmd(f"SET_SP,{int(round(a.sp))}"), flush=True)
                print("START_TEST:", ov.cmd("START_TEST"), flush=True)
                t0 = time.time()
                try:
                    while time.time() - t0 < a.minutes * 60:
                        d = ov.data()
                        if d is not None:
                            f.write(f"{dt.datetime.now().isoformat(timespec='seconds')},"
                                    f"{time.time() - t0:.1f},{d[0]:.2f},{d[1]:.2f},{d[2]:.2f}\n")
                            f.flush()
                            if d[0] > min(AIR_LIMIT, a.sp + 15.0):
                                print(f"!!! air {d[0]:.1f} C: stopping", flush=True)
                                break
                        time.sleep(2.0)
                finally:
                    print("STOP_TEST:", ov.stop(), flush=True)
            print("log:", path)
    finally:
        ov.close()


if __name__ == "__main__":
    main()
