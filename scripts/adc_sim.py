#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Mauro Rodriguez Blasco
"""
The 3-bit flash ADC's transfer curve in the three sign-off corners, with ngspice and the SKY130
models: vin swept from 0 to 0.9 V in 1 mV steps, with an ideal 0.9 V on vref, and from the 3
bits the codes seen, the 7 thresholds, the DNL and the INL. The same script runs the pre-layout
netlist and the extracted one, so that the two can be compared.

    python3 scripts/adc_sim.py [netlist]

The netlist defines the subcircuit 'adc' (vin vref b0 b1 b2 vdd vss); by default
netlist/adc.spice, which includes the blocks' netlists. The PDK is read from PDK_ROOT (default
~/.volare). A threshold is where the code first reaches k; the DNL of a step is its width over
an LSB (112.5 mV) minus 1, and the INL of a threshold its distance from k LSB, in LSB.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sim import CORNERS, ROOT, SETTINGS, lib

LSB = 0.9 / 8
STEP = 1e-3


def run(text: str, keep: list[str]) -> tuple[str, dict[str, str]]:
    """ngspice on a bench, and the text of the files it wrote that are named in keep."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / ".spiceinit").write_text(SETTINGS)
        (Path(tmp) / "bench.cir").write_text(text)
        done = subprocess.run(["ngspice", "-b", "bench.cir"], cwd=tmp, capture_output=True,
                              text=True, timeout=1800)
        files = {n: (Path(tmp) / n).read_text() for n in keep if (Path(tmp) / n).is_file()}
    return done.stdout + done.stderr, files


def ports(netlist: Path) -> list[str]:
    text = re.sub(r"\n\+", " ", netlist.read_text(errors="replace"))
    m = re.search(r"^\.subckt\s+adc\s+(.*)$", text, re.M | re.I)
    pins = [p.lower() for p in m.group(1).split() if "=" not in p] if m else []
    if sorted(pins) != sorted(["vin", "vref", "b0", "b1", "b2", "vdd", "vss"]):
        sys.exit(f"{netlist.name}: no subcircuit adc with pins vin vref b0 b1 b2 vdd vss "
                 f"(found {pins or 'none'})")
    return pins


def transfer(netlist: Path, process: str, temp: float, vdd: float) -> dict:
    nodes = dict(vin="vin", vref="vref", b0="b0", b1="b1", b2="b2", vdd="vdd", vss="0")
    lines = [f"* the ADC's transfer curve, {process}", f'.lib "{lib()}" {process}', f".temp {temp}",
             f'.include "{netlist}"', f"VDD vdd 0 {vdd}", "VREF vref 0 0.9", "VIN vin 0 0",
             "X1 " + " ".join(nodes[p] for p in ports(netlist)) + " adc",
             f".dc VIN 0 0.9 {STEP}", ".control", "run", "wrdata bits.txt v(b0) v(b1) v(b2)", ".endc", ".end"]
    out, files = run("\n".join(lines) + "\n", keep=["bits.txt"])
    data = files.get("bits.txt", "")
    rows = [[float(v) for v in l.split()] for l in data.splitlines() if l.strip()]
    if not rows:
        sys.exit(f"{process}: the transfer bench failed\n{out[-2000:]}")
    codes = [(r[0], sum((r[1 + 2 * i] > vdd / 2) << i for i in range(3))) for r in rows]
    seen = {c for _, c in codes}
    thresholds = {}
    for v, c in codes:
        for k in range(1, 8):
            if c >= k and k not in thresholds:
                thresholds[k] = v
    t = [thresholds.get(k) for k in range(1, 8)]
    dnl = [((t[k] - t[k - 1]) / LSB - 1) for k in range(1, 7) if t[k] is not None and t[k - 1] is not None]
    inl = [((t[k - 1] - (k * LSB)) / LSB) for k in range(1, 8) if t[k - 1] is not None]
    monotonic = all(b[1] >= a[1] for a, b in zip(codes, codes[1:]))
    return {"missing": 8 - len(seen), "thresholds": t, "dnl": max(map(abs, dnl), default=float("nan")),
            "inl": max(map(abs, inl), default=float("nan")), "monotonic": monotonic}


def main() -> int:
    netlist = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "netlist" / "adc.spice").resolve()
    if not lib().is_file():
        sys.exit(f"No SKY130 in {lib()}: set PDK_ROOT")
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(lambda c: transfer(netlist, *c), CORNERS))
    print(f"{netlist.name}: vin 0 to 0.9 V in {STEP * 1e3:g} mV steps, vref 0.9 V\n")
    print("| | " + " | ".join(f"{p}, {t} °C, {v:.2f} V" for p, t, v in CORNERS) + " |")
    print("|---" * (len(CORNERS) + 1) + "|")
    rows = [("Missing codes", lambda r: f"{r['missing']}"),
            ("Monotonic", lambda r: "yes" if r["monotonic"] else "no"),
            ("Thresholds (mV)", lambda r: " ".join(f"{x * 1e3:.0f}" if x is not None else "–" for x in r["thresholds"])),
            ("Largest DNL", lambda r: f"{r['dnl']:.3f} LSB"),
            ("Largest INL", lambda r: f"{r['inl']:.3f} LSB")]
    for name, f in rows:
        print(f"| {name} | " + " | ".join(f(r) for r in results) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
