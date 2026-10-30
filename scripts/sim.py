#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Mauro Rodriguez Blasco
"""
The comparator in the three sign-off corners, with ngspice and the SKY130 models: its random
offset from many copies with the PDK's mismatch models, and nominally its offset at each tap,
its supply current, its output levels and its delay. The same script runs the pre-layout
netlist and the extracted one, so that the two can be compared.

    python3 scripts/sim.py [netlist] [--copies 112] [--seed 7] [--overdrive 10]

The netlist defines the subcircuit 'comparator' (inp inn out vdd vss); the PDK is read from
PDK_ROOT (default ~/.volare). Each copy's inp is its tap plus one common sweep of ±60 mV, so
one .dc measures every copy; its offset is where its output crosses half the supply. The delay
is the only row that the layout's capacitances can change: inp steps from the overdrive below
each tap to the overdrive above and back, and the delay runs from inp crossing the tap to out
crossing half the supply.
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


def ports(netlist: Path) -> list[str]:
    """The pins of subcircuit comparator, in its order: an extracted netlist may have them in
    another order than the schematic's."""
    text = re.sub(r"\n\+", " ", netlist.read_text(errors="replace"))
    m = re.search(r"^\.subckt\s+comparator\s+(.*)$", text, re.M | re.I)
    pins = [p.lower() for p in m.group(1).split() if "=" not in p] if m else []
    if sorted(pins) != sorted(["inp", "inn", "out", "vdd", "vss"]):
        sys.exit(f"{netlist.name}: no subcircuit comparator with pins inp inn out vdd vss "
                 f"(found {pins or 'none'})")
    return pins


def x(name: str, pins: list[str], nodes: dict[str, str]) -> str:
    return f"{name} {' '.join(nodes[p] for p in pins)} comparator"


def head(netlist: Path, section: str, temp: float, vdd: float, seed: int | None) -> list[str]:
    return [f"* comparator, {section}", f'.lib "{lib()}" {section}', f".temp {temp}",
            f".param vdd={vdd}", f'.include "{netlist}"'] \
        + ([f".options seed={seed}"] if seed is not None else []) \
        + ["VDD vdd 0 {vdd}", "VDIFF vd 0 0"]


def offsets(netlist: Path, process: str, temp: float, vdd: float, copies: int,
            seed: int) -> list[float]:
    """The offset of each copy, in volts, with the mismatch models."""
    pins, lines = ports(netlist), head(netlist, f"{process}_mm", temp, vdd, seed)
    for k in range(copies):
        t = k % 7
        lines += [f"VT{k} tap{k} 0 {TAPS[t]}", f"E{k} in{k} tap{k} vd 0 1",
                  x(f"X{k}", pins, dict(inp=f"in{k}", inn=f"tap{k}", out=f"o{k}", vdd="vdd", vss="0"))]
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
    pins, lines = ports(netlist), head(netlist, process, temp, vdd, None)
    for t, tap in enumerate(TAPS):
        lines += [f"VT{t} tap{t} 0 {tap}", f"E{t} in{t} tap{t} vd 0 1",
                  x(f"X{t}", pins, dict(inp=f"in{t}", inn=f"tap{t}", out=f"o{t}", vdd="vdd", vss="0"))]
    sides = [(s, t, d) for s, (t, d) in enumerate([(0, 0.02), (0, -0.02), (6, 0.02), (6, -0.02)])]
    for s, t, d in sides:
        lines += [f"VS{s} vs{s} 0 {{vdd}}", f"VQ{s} q{s} 0 {TAPS[t] + d}",
                  x(f"XS{s}", pins, dict(inp=f"q{s}", inn=f"tap{t}", out=f"s{s}", vdd=f"vs{s}", vss="0"))]
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


def delay(netlist: Path, process: str, temp: float, vdd: float, overdrive: float) -> dict:
    """Without mismatch: the slowest tap's delay, out rising and out falling, for inp stepping
    from the overdrive below its tap to the overdrive above (at 1 us) and back (at 3 us)."""
    pins, lines = ports(netlist), head(netlist, process, temp, vdd, None)
    for t, tap in enumerate(TAPS):
        lines += [f"VT{t} tap{t} 0 {tap}",
                  f"VP{t} in{t} 0 PULSE({tap - overdrive} {tap + overdrive} 1u 1n 1n 2u 1)",
                  x(f"X{t}", pins, dict(inp=f"in{t}", inn=f"tap{t}", out=f"o{t}", vdd="vdd", vss="0"))]
    lines += [".tran 1n 5u"]
    for t, tap in enumerate(TAPS):
        lines += [f".meas tran r{t} trig v(in{t}) val={tap} rise=1 targ v(o{t}) val={{vdd/2}} rise=1",
                  f".meas tran f{t} trig v(in{t}) val={tap} fall=1 targ v(o{t}) val={{vdd/2}} fall=1"]
    out = run("\n".join(lines + [".end"]) + "\n")
    got = {k: float(v) for k, v in re.findall(r"^([rf]\d)\s*=\s*(\S+)", out, re.M)}
    if len(got) != 14:
        sys.exit(f"{process}: the delay bench failed\n{out[-2000:]}")
    return {"rise": max(got[f"r{t}"] for t in range(7)), "fall": max(got[f"f{t}"] for t in range(7))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    ap.add_argument("netlist", nargs="?", default=str(ROOT / "netlist" / "comparator.spice"))
    ap.add_argument("--copies", type=int, default=112, help="copies with mismatch, spread over the 7 taps")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--overdrive", type=float, default=10, help="mV either side of the tap, for the delay")
    args = ap.parse_args()
    netlist = Path(args.netlist).resolve()
    if not lib().is_file():
        sys.exit(f"No SKY130 in {lib()}: set PDK_ROOT")

    def corner(c):
        process, temp, vdd = c
        return offsets(netlist, process, temp, vdd, args.copies, args.seed), \
            {**nominal(netlist, process, temp, vdd),
             **delay(netlist, process, temp, vdd, args.overdrive / 1e3)}
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
            ("Output high / low", lambda o, n: f"{n['high']:.3f} / {n['low'] * 1e3:.0f} mV"),
            (f"Delay at {args.overdrive:g} mV overdrive, slowest tap: out rising / falling",
             lambda o, n: f"{n['rise'] * 1e9:.0f} / {n['fall'] * 1e9:.0f} ns")]
    for name, f in rows:
        print(f"| {name} | " + " | ".join(f(o, n) for o, n in results) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
