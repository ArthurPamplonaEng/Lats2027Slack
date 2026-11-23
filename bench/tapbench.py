#!/usr/bin/env python3
"""tapbench: the 16 nm failure-validation bench (tap_top on the RV02A / AU15P board).

    python3 -I bench/tapbench.py program            # program tap_top into the FPGA SRAM
    python3 -I bench/tapbench.py status             # one window, printed as a table
    python3 -I bench/tapbench.py monitor --windows 30
    python3 -I bench/tapbench.py shmoo --from 0.85 --to 0.72 --windows 10 --tag run1
    python3 -I bench/tapbench.py shmoo --list 0.85,0.80,0.85 --windows 5

The FPGA reports, per 1 s window and per tap: sweeps in which the sensor alarmed (got), the mean,
min and max reading (phase steps of 17.857 ps) and the clock cycles in which the tap's capture
flop held a wrong value (err). The core voltage is commanded through the STM32/PMIC (10 mV steps);
the die voltage and temperature come from the SYSMON over the JTAG.

Safety: commands are limited to 0.70-0.92 V (PMIC), the run stops and returns to 0.85 V if the
SYSMON reads VCCINT > 0.970 V, the die > 125 C (board B reads ~100 C at room temperature), the
shunt current passes 1.8 A, or the JTAG link fails three times in a row. The flash is never written.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from stm32_link import Stm32Link  # noqa: E402

VIVADO = os.environ.get("VIVADO_BIN", os.path.expanduser("~/2025.2/Vivado/bin/vivado"))
BUILD = os.environ.get("TAP_BUILD", os.path.join(ROOT, "hw", "au15p_tap", "build", "impl"))
BIT = os.path.join(BUILD, "tap_top.bit")
LTX = os.path.join(BUILD, "tap_top.ltx")
LOGDIR = os.path.join(ROOT, "data", "au15p_tap")

N_TAPS = 23
STAGES = [24, 48] + [70 + 4 * k for k in range(21)]
STEP_PS = 1000.0 / 56.0
NOMINAL_VC = 0.85
LIM_VCCINT = 0.970
LIM_TEMP = 125.0
LIM_IS = 1.8


def log(msg: str):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# =============================================================================== Vivado server
class Vivado:
    TAGS = ("TAPOK", "TAPDATA", "TAPERR")

    def __init__(self, transcript: str | None = None):
        self.tr = open(transcript, "a") if transcript else None
        self.p = subprocess.Popen(
            [VIVADO, "-mode", "tcl", "-nolog", "-nojournal"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, cwd=os.path.join(ROOT, "bench"))
        self.q: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()
        tag, msg = self.cmd(f"source -notrace {os.path.join(HERE, 'vivado_server.tcl')}", 180)
        if tag != "TAPOK":
            raise RuntimeError(f"Vivado server did not start: {msg}")

    def _pump(self):
        for line in self.p.stdout:
            if self.tr:
                self.tr.write(line)
                self.tr.flush()
            self.q.put(line.rstrip("\n"))
        self.q.put("TAPERR vivado exited")

    def expect(self, timeout: float) -> tuple[str, str]:
        t0 = time.time()
        while True:
            left = timeout - (time.time() - t0)
            if left <= 0:
                raise TimeoutError("no answer from Vivado")
            try:
                line = self.q.get(timeout=left)
            except queue.Empty:
                continue
            # a reply is a line that starts with its tag (after an optional "Vivado% " prompt);
            # echoed Tcl source lines start with '#' or contain the tag elsewhere
            ln = line
            while ln.startswith("Vivado% "):
                ln = ln[len("Vivado% "):]
            for tag in self.TAGS:
                if ln.startswith(tag + " "):
                    return tag, ln[len(tag) + 1:]

    def cmd(self, line: str, timeout: float = 60.0) -> tuple[str, str]:
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        return self.expect(timeout)

    def close(self):
        try:
            self.cmd("tap_close", 30)
            self.p.stdin.write("exit\n")
            self.p.stdin.flush()
            self.p.wait(timeout=30)
        except Exception:
            self.p.kill()


def parse_kv(s: str) -> dict[str, str]:
    out = {}
    for tok in s.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k] = v
    return out


def hexval(s: str) -> int:
    s = s.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    return int(s, 16)


def decode(d: dict[str, str]) -> dict:
    """TAPDATA fields -> window dict (global, per tap, SYSMON)."""
    g = hexval(d["p0"])
    w = {
        "t_ms": int(d["t_ms"]),
        "w_id": (g >> 96) & 0xFFFFFFFF,
        "sweeps": (g >> 64) & 0xFFFFFFFF,
        "sat": (g >> 32) & 0xFFFFFFFF,
        "tmo": (g >> 16) & 0xFFFF,
        "lock_loss": (g >> 8) & 0xFF,
        "flags": g & 0xFF,
        "temp_c": float(d["temperature"]),
        "vccint_v": float(d["vccint"]),
        "vccaux_v": float(d["vccaux"]),
        "vccbram_v": float(d["vccbram"]),
        "temp_raw": d.get("temp_raw", ""),
        "vccint_raw": d.get("vccint_raw", ""),
        "taps": [],
    }
    for j in range(N_TAPS):
        v = hexval(d[f"p{j + 1}"])
        got = v & 0xFFFFFFFF
        ssum = (v >> 32) & 0xFFFFFFFF
        mn = (v >> 64) & 0xFFFF
        mx = (v >> 80) & 0xFFFF
        err = (v >> 96) & 0xFFFFFFFF
        w["taps"].append({"got": got, "sum": ssum, "min": mn, "max": mx, "err": err,
                          "mean": (ssum / got) if got else None})
    return w


# =============================================================================== bench
class Bench:
    def __init__(self, stm_port: str, transcript: str):
        self.viv = Vivado(transcript)
        tag, msg = self.viv.cmd("tap_connect", 120)
        if tag != "TAPOK":
            raise RuntimeError(msg)
        log(f"JTAG: {msg}")
        self.info = parse_kv(msg)
        self.stm = Stm32Link(stm_port, log=log)
        tel = self.stm.wait_tel(5.0)
        log(f"STM32: Vc={tel.f('Vc')} V Vi={tel.f('Vi')} V Is={tel.f('Is')} A Io={tel.f('Io')} A")
        self.vc_cmd: float | None = None
        self.jtag_fail = 0

    def close(self):
        try:
            self.stm.close()
        finally:
            self.viv.close()

    def program(self):
        tag, msg = self.viv.cmd(f"tap_program {BIT} {LTX}", 300)
        if tag != "TAPOK":
            raise RuntimeError(msg)
        log(f"programmed: {msg}")

    def attach(self):
        tag, msg = self.viv.cmd(f"tap_attach {LTX}", 120)
        if tag != "TAPOK":
            raise RuntimeError(msg)
        log(f"attached: {msg}")

    def read(self) -> dict:
        tag, msg = self.viv.cmd("tap_read", 60)
        if tag != "TAPDATA":
            self.jtag_fail += 1
            raise RuntimeError(msg)
        self.jtag_fail = 0
        w = decode(parse_kv(msg))
        tel = self.stm.tel
        w.update({"pc_time": dt.datetime.now().isoformat(timespec="milliseconds"),
                  "vc_cmd": self.vc_cmd, "vc_pmic": tel.f("Vc"), "is_a": tel.f("Is"),
                  "io_a": tel.f("Io"), "vi_v": tel.f("Vi"), "pmic_c": tel.f("Et"),
                  "mcu_c": tel.f("Mt")})
        return w

    def next_window(self, last_id: int | None, timeout: float = 4.0) -> dict:
        t0 = time.time()
        while True:
            try:
                w = self.read()
            except RuntimeError as e:
                log(f"JTAG read failed ({e})")
                if self.jtag_fail >= 3:
                    raise
                time.sleep(0.5)
                continue
            self.check(w)
            if last_id is None or w["w_id"] != last_id:
                return w
            if time.time() - t0 > timeout:
                raise TimeoutError("the window counter stopped")
            time.sleep(0.25)

    def check(self, w: dict):
        bad = []
        if w["vccint_v"] > LIM_VCCINT:
            bad.append(f"VCCINT {w['vccint_v']:.3f} V")
        if w["temp_c"] > LIM_TEMP:
            bad.append(f"die {w['temp_c']:.1f} C")
        if w["is_a"] is not None and w["is_a"] > LIM_IS:
            bad.append(f"Is {w['is_a']:.2f} A")
        if bad:
            raise RuntimeError("safety limit: " + ", ".join(bad))

    def set_vc(self, vc: float):
        got = self.stm.set_vcore(vc)
        self.vc_cmd = round(vc, 2)
        log(f"Vcore {vc:.2f} V (PMIC reads {got:.3f} V)")

    def safe(self):
        try:
            self.set_vc(NOMINAL_VC)
        except Exception as e:  # noqa: BLE001
            log(f"!!! could not return to {NOMINAL_VC} V: {e}")


def tap_table(w: dict) -> str:
    rows = [f"window {w['w_id']}  sweeps {w['sweeps']}  sat {w['sat']}  tmo {w['tmo']}  "
            f"lock_loss {w['lock_loss']}  flags {w['flags']:08b}  die {w['temp_c']:.1f} C  "
            f"VCCINT {w['vccint_v']:.4f} V  Vc_pmic {w['vc_pmic']}  Is {w['is_a']}"]
    rows.append(" tap stage    got     mean   min   max        err")
    for j, t in enumerate(w["taps"]):
        mean = f"{t['mean']:8.2f}" if t["mean"] is not None else "       -"
        mn = t["min"] if t["got"] else "-"
        mx = t["max"] if t["got"] else "-"
        rows.append(f" {j:3d} {STAGES[j]:5d} {t['got']:6d} {mean} {mn!s:>5} {mx!s:>5} {t['err']:10d}")
    return "\n".join(rows)


CSV_FIELDS = (["pc_time", "t_ms", "tag", "phase", "vc_cmd", "vc_pmic", "is_a", "io_a", "vi_v",
               "pmic_c", "mcu_c", "temp_c", "vccint_v", "vccaux_v", "vccbram_v", "temp_raw",
               "vccint_raw", "w_id", "sweeps", "sat", "tmo", "lock_loss", "flags"]
              + [f"t{j}_{k}" for j in range(N_TAPS) for k in ("got", "mean", "min", "max", "err")])


def row_of(w: dict, tag: str, phase: str) -> dict:
    r = {k: w.get(k) for k in CSV_FIELDS if not k.startswith("t") or k in
         ("t_ms", "tag", "temp_c", "temp_raw", "tmo")}
    r.update({"tag": tag, "phase": phase})
    for j, t in enumerate(w["taps"]):
        r[f"t{j}_got"] = t["got"]
        r[f"t{j}_mean"] = f"{t['mean']:.4f}" if t["mean"] is not None else ""
        r[f"t{j}_min"] = t["min"] if t["got"] else ""
        r[f"t{j}_max"] = t["max"] if t["got"] else ""
        r[f"t{j}_err"] = t["err"]
    return r


def open_log(tag: str, bench: Bench, extra: dict) -> tuple[csv.DictWriter, object, str]:
    os.makedirs(LOGDIR, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LOGDIR, f"tap_{tag}_{stamp}.csv")
    meta = {"created": dt.datetime.now().isoformat(timespec="seconds"), "tag": tag,
            "bitstream": BIT, "bitstream_md5": md5(BIT) if os.path.exists(BIT) else None,
            "jtag": bench.info, "stages": STAGES, "step_ps": STEP_PS,
            "stm32_first_tel": bench.stm.tel.fields, **extra}
    with open(path + ".json", "w") as f:
        json.dump(meta, f, indent=1)
    fh = open(path, "w", newline="")
    wr = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
    wr.writeheader()
    return wr, fh, path


# =============================================================================== commands
def cmd_program(b: Bench, a):
    b.program()
    time.sleep(2.5)
    w = b.next_window(None)
    print(tap_table(w))


def cmd_status(b: Bench, a):
    b.attach()
    w0 = b.next_window(None)
    w = b.next_window(w0["w_id"])
    print(tap_table(w))


def cmd_monitor(b: Bench, a):
    b.attach()
    wr, fh, path = open_log(a.tag, b, {"mode": "monitor"})
    log(f"logging to {path}")
    last = None
    try:
        for _ in range(a.windows):
            w = b.next_window(last)
            last = w["w_id"]
            wr.writerow(row_of(w, a.tag, "monitor"))
            fh.flush()
            if a.verbose:
                print(tap_table(w))
    finally:
        fh.close()


def vc_schedule(a) -> list[float]:
    if a.list:
        return [round(float(x), 2) for x in a.list.split(",")]
    step = -abs(a.step) if a.to < a.frm else abs(a.step)
    out, v = [], a.frm
    while (step < 0 and v >= a.to - 1e-9) or (step > 0 and v <= a.to + 1e-9):
        out.append(round(v, 2))
        v += step
    if a.back:
        out += out[-2::-1]
    return out


def cmd_shmoo(b: Bench, a):
    b.attach()
    sched = vc_schedule(a)
    log(f"schedule ({len(sched)} points): {sched}")
    wr, fh, path = open_log(a.tag, b, {"mode": "shmoo", "schedule": sched, "windows": a.windows,
                                       "settle_windows": a.settle})
    log(f"logging to {path}")
    last = None
    try:
        for i, vc in enumerate(sched):
            b.set_vc(vc)
            for k in range(a.settle):
                w = b.next_window(last)
                last = w["w_id"]
                wr.writerow(row_of(w, a.tag, f"settle{i}"))
            fails = 0
            for k in range(a.windows):
                w = b.next_window(last)
                last = w["w_id"]
                wr.writerow(row_of(w, a.tag, f"point{i}"))
                fails = sum(1 for t in w["taps"] if t["err"] > 0)
            fh.flush()
            ws = w["taps"]
            summ = " ".join(f"{(t['mean'] if t['mean'] is not None else -1):.0f}"
                            f"{'*' if t['err'] else ''}" for t in ws[2:])
            log(f"Vc {vc:.2f} VCCINT {w['vccint_v']:.4f} die {w['temp_c']:.1f}C "
                f"taps-with-errors {fails}: {summ}")
    except KeyboardInterrupt:
        log("interrupted")
    finally:
        fh.close()
        b.safe()
        log(f"saved {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["program", "status", "monitor", "shmoo"])
    ap.add_argument("--stm", default="/dev/ttyACM1")
    ap.add_argument("--tag", default="test")
    ap.add_argument("--windows", type=int, default=10)
    ap.add_argument("--settle", type=int, default=2)
    ap.add_argument("--from", dest="frm", type=float, default=0.85)
    ap.add_argument("--to", type=float, default=0.80)
    ap.add_argument("--step", type=float, default=0.01)
    ap.add_argument("--back", action="store_true", help="return along the same points")
    ap.add_argument("--list", default="")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    os.makedirs(LOGDIR, exist_ok=True)
    b = Bench(a.stm, os.path.join(LOGDIR, "vivado_transcript.log"))
    try:
        {"program": cmd_program, "status": cmd_status, "monitor": cmd_monitor,
         "shmoo": cmd_shmoo}[a.cmd](b, a)
    except Exception:
        b.safe()
        raise
    finally:
        b.close()


if __name__ == "__main__":
    main()
