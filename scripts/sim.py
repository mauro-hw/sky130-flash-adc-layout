#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Mauro Rodriguez Blasco
"""
The comparator in the three sign-off corners, with ngspice and the SKY130 models: its random
offset from many copies with the PDK's mismatch models, and nominally its offset at each tap,
its supply current and its output levels. The same script runs the pre-layout netlist and the
extracted one, so that the two can be compared.

    python3 scripts/sim.py [netlist] [--copies 112] [--seed 7]

The netlist defines the subcircuit 'comparator' (inp inn out vdd vss); the PDK is read from
PDK_ROOT (default ~/.volare). Each copy's inp is its tap plus one common sweep of ±60 mV, so
one .dc measures every copy; its offset is where its output crosses half the supply.
"""
from __future__ import annotations

import argparse
import os
import re
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORNERS = (("tt", 25, 1.80), ("ss", 100, 1.60), ("ff", -40, 1.95))
TAPS = [k * 0.1125 for k in range(1, 8)]
SETTINGS = "set ngbehavior=hsa\nset skywaterpdk\nset ng_nomodcheck\n"   # the PDK's spinit


def lib() -> Path:
    return Path(os.environ.get("PDK_ROOT", Path.home() / ".volare")).expanduser() \
        / "sky130A" / "libs.tech" / "ngspice" / "sky130.lib.spice"


def run(text: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / ".spiceinit").write_text(SETTINGS)
        (Path(tmp) / "bench.cir").write_text(text)
        done = subprocess.run(["ngspice", "-b", "bench.cir"], cwd=tmp, capture_output=True,
                              text=True, timeout=900)
    return done.stdout + done.stderr


def head(netlist: Path, section: str, temp: float, vdd: float, seed: int | None) -> list[str]:
    return [f"* comparator, {section}", f'.lib "{lib()}" {section}', f".temp {temp}",
            f".param vdd={vdd}", f'.include "{netlist}"'] \
        + ([f".options seed={seed}"] if seed is not None else []) \
        + ["VDD vdd 0 {vdd}", "VDIFF vd 0 0"]


def offsets(netlist: Path, process: str, temp: float, vdd: float, copies: int,
            seed: int) -> list[float]:
    """The offset of each copy, in volts, with the mismatch models."""
    lines = head(netlist, f"{process}_mm", temp, vdd, seed)
    for k in range(copies):
        t = k % 7
        lines += [f"VT{k} tap{k} 0 {TAPS[t]}", f"E{k} in{k} tap{k} vd 0 1",
                  f"X{k} in{k} tap{k} o{k} vdd 0 comparator"]
    lines += [".dc VDIFF -0.06 0.06 0.5m"]
    lines += [f".meas dc off{k} when v(o{k})={{vdd/2}} rise=1" for k in range(copies)]
    out = run("\n".join(lines + [".end"]) + "\n")
    got = {int(k): float(v) for k, v in re.findall(r"^off(\d+)\s*=\s*(\S+)", out, re.M)}
    if len(got) != copies:
        sys.exit(f"{process}: {copies - len(got)} copies did not switch within ±60 mV")
    return [got[k] for k in range(copies)]


def nominal(netlist: Path, process: str, temp: float, vdd: float) -> dict:
    """Without mismatch: the offset at each tap; the current and output levels 20 mV either
    side of the top and bottom taps."""
    lines = head(netlist, process, temp, vdd, None)
    for t, tap in enumerate(TAPS):
        lines += [f"VT{t} tap{t} 0 {tap}", f"E{t} in{t} tap{t} vd 0 1",
                  f"X{t} in{t} tap{t} o{t} vdd 0 comparator"]
    sides = [(s, t, d) for s, (t, d) in enumerate([(0, 0.02), (0, -0.02), (6, 0.02), (6, -0.02)])]
    for s, t, d in sides:
        lines += [f"VS{s} vs{s} 0 {{vdd}}", f"VQ{s} q{s} 0 {TAPS[t] + d}",
                  f"XS{s} q{s} tap{t} s{s} vs{s} 0 comparator"]
    lines += [".dc VDIFF -0.06 0.06 0.5m"]
    lines += [f".meas dc off{t} when v(o{t})={{vdd/2}} rise=1" for t in range(7)]
    lines += [".control", "run", "op"] + [f"print -i(VS{s}) v(s{s})" for s, _, _ in sides] \
        + [".endc"]
    out = run("\n".join(lines + [".end"]) + "\n")
    off = {int(k): float(v) for k, v in re.findall(r"^off(\d+)\s*=\s*(\S+)", out, re.M)}
    cur = [float(x) for x in re.findall(r"^-i\(vs\d\)\s*=\s*(\S+)", out, re.M)]
    lvl = [float(x) for x in re.findall(r"^v\(s\d\)\s*=\s*(\S+)", out, re.M)]
    if len(off) != 7 or len(cur) != 4 or len(lvl) != 4:
        sys.exit(f"{process}: the nominal bench failed\n{out[-2000:]}")
    return {"offset": [off[t] for t in range(7)], "iq": max(cur),
            "high": min(lvl[0], lvl[2]), "low": max(lvl[1], lvl[3])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    ap.add_argument("netlist", nargs="?", default=str(ROOT / "netlist" / "comparator.spice"))
    ap.add_argument("--copies", type=int, default=112, help="copies with mismatch, spread over the 7 taps")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    netlist = Path(args.netlist).resolve()
    if not lib().is_file():
        sys.exit(f"No SKY130 in {lib()}: set PDK_ROOT")

    def corner(c):
        process, temp, vdd = c
        return offsets(netlist, process, temp, vdd, args.copies, args.seed), \
            nominal(netlist, process, temp, vdd)
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(corner, CORNERS))

    mv = lambda x: f"{x * 1e3:+.2f}"
    print(f"{netlist.name}: {args.copies} copies with mismatch (seed {args.seed})\n")
    print("| | " + " | ".join(f"{p}, {t} °C, {v:.2f} V" for p, t, v in CORNERS) + " |")
    print("|---" * (len(CORNERS) + 1) + "|")
    rows = [("Offset σ, with mismatch", lambda o, n: f"{statistics.stdev(o) * 1e3:.2f} mV"),
            ("Offset mean; min / max", lambda o, n: f"{mv(statistics.fmean(o))}; "
                                                    f"{mv(min(o))} / {mv(max(o))} mV"),
            ("Offset without mismatch, worst tap", lambda o, n: f"{mv(max(n['offset'], key=abs))} mV"),
            ("Supply current, largest", lambda o, n: f"{n['iq'] * 1e6:.2f} µA"),
            ("Output high / low", lambda o, n: f"{n['high']:.3f} / {n['low'] * 1e3:.0f} mV")]
    for name, f in rows:
        print(f"| {name} | " + " | ".join(f(o, n) for o, n in results) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
