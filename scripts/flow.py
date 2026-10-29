#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Mauro Rodriguez Blasco
"""
The physical verification of a cell of mag/, with Magic and Netgen and the SKY130 rules:

    python3 scripts/flow.py drc CELL       design rules (Magic's full DRC)
    python3 scripts/flow.py lvs CELL       layout against netlist/CELL.spice (Netgen)
    python3 scripts/flow.py pex CELL       netlist with parasitic capacitances, for sim.py
    python3 scripts/flow.py gds CELL       gds/CELL.gds
    python3 scripts/flow.py all CELL       all four, stopping at the first that fails
    python3 scripts/flow.py selftest       the tools, on a transistor that Magic generates

What it writes goes to build/ (not in git), except the GDS. The PDK comes from PDK_ROOT
(~/.volare by default).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAG, BUILD = ROOT / "mag", ROOT / "build"


def pdk() -> Path:
    return Path(os.environ.get("PDK_ROOT", Path.home() / ".volare")).expanduser() / "sky130A"


def magic(script: str, cells: Path = MAG, out: Path = BUILD) -> str:
    """Magic without a window, in out/, with the cells of cells/ on its search path."""
    out.mkdir(parents=True, exist_ok=True)
    tcl = out / "flow.tcl"
    tcl.write_text(f"addpath {cells}\n{script}\nquit -noprompt\n")
    done = subprocess.run(["magic", "-dnull", "-noconsole", "-rcfile", str(MAG / ".magicrc"),
                           str(tcl)], cwd=out, capture_output=True, text=True, timeout=600,
                          env={**os.environ, "PDK_ROOT": str(pdk().parent)})
    text = done.stdout + done.stderr
    if re.search(r"^(can't read|invalid command name|Error)", text, re.M):
        sys.exit(f"Magic failed:\n{text[-1500:]}")
    return text


def drc(cell: str, cells: Path = MAG, out: Path = BUILD) -> bool:
    text = magic(f"""load {cell}
select top cell
expand
drc style drc(full)
drc on
drc check
drc catchup
puts "FLOW drc [drc list count total]"
foreach {{why boxes}} [drc listall why] {{puts "FLOW why [llength $boxes] × $why"}}""", cells, out)
    count = re.search(r"^FLOW drc (\d+)", text, re.M)
    if not count:
        sys.exit(f"DRC did not run:\n{text[-1500:]}")
    n = int(count.group(1))
    print(f"DRC {cell}: {n} error{'s' if n != 1 else ''}")
    for why in re.findall(r"^FLOW why (.+)$", text, re.M):
        print(f"  {why}")
    return n == 0


def extract(cell: str, cells: Path = MAG, out: Path = BUILD) -> tuple[Path, Path]:
    """Two netlists: one for LVS (devices only) and one flat, with the parasitic
    capacitances, for simulation."""
    magic(f"""load {cell}
select top cell
expand
extract path .
extract all
ext2spice lvs
ext2spice -o {cell}_lvs.spice
ext2spice default
ext2spice hierarchy off
ext2spice subcircuit top on
ext2spice cthresh 0
ext2spice -o {cell}_pex.spice""", cells, out)
    lvs, pex = out / f"{cell}_lvs.spice", out / f"{cell}_pex.spice"
    if not lvs.is_file() or not pex.is_file():
        sys.exit(f"The extraction of {cell} wrote no netlist")
    return lvs, pex


def lvs(cell: str, ref: Path | None = None, cells: Path = MAG, out: Path = BUILD) -> bool:
    ref = ref or ROOT / "netlist" / f"{cell}.spice"
    if not ref.is_file():
        sys.exit(f"No reference netlist for {cell}: {ref}")
    if shutil.which("netgen") is None:
        sys.exit("No netgen in PATH")
    layout, _ = extract(cell, cells, out)
    report = out / f"{cell}_lvs.out"
    report.unlink(missing_ok=True)
    done = subprocess.run(["netgen", "-batch", "lvs", f"{layout} {cell}", f"{ref} {cell}",
                           str(pdk() / "libs.tech" / "netgen" / "sky130A_setup.tcl"), str(report)],
                          cwd=out, capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
    if not report.is_file():
        sys.exit("Netgen wrote no report: is it Netgen 1.5 (netgen -batch lvs)?\n"
                 + (done.stdout + done.stderr)[-1500:])
    text = report.read_text(errors="replace")
    final = re.findall(r"^Final result:\s*(.+)$", text, re.M)
    ok = bool(final) and "match uniquely" in final[-1] and "not" not in final[-1].lower()
    print(f"LVS {cell}: {final[-1] if final else 'no result'} ({report.relative_to(ROOT)})"
          if out == BUILD else f"LVS {cell}: {final[-1] if final else 'no result'}")
    return ok


def gds(cell: str) -> Path:
    path = ROOT / "gds" / f"{cell}.gds"
    path.parent.mkdir(exist_ok=True)
    magic(f"load {cell}\nselect top cell\nexpand\ngds write {path}")
    print(f"GDS {cell}: {path.relative_to(ROOT)}")
    return path


def selftest() -> bool:
    """A transistor from the PDK's generator: no DRC errors, LVS against a netlist written
    by hand, and its extracted netlist in ngspice with the current of the schematic's."""
    with tempfile.TemporaryDirectory() as tmp:
        cells, out = Path(tmp), Path(tmp) / "build"
        magic("""drc off
load top
box 0 0 0 0
magic::gencell sky130::sky130_fd_pr__nfet_01v8 XM1 w 2 l 1 nf 1 m 1
cellname rename [lindex [cellname list children top] 0] flowtest
load flowtest
save flowtest""", cells, out)
        ok = drc("flowtest", cells, out)
        ref = cells / "flowtest.spice"
        ref.write_text(".subckt flowtest B D S G\n"
                       "XM1 D G S B sky130_fd_pr__nfet_01v8 w=2 l=1\n.ends\n")
        ok = lvs("flowtest", ref, cells, out) and ok
        _, pex = extract("flowtest", cells, out)
        (out / ".spiceinit").write_text("set ngbehavior=hsa\nset skywaterpdk\nset ng_nomodcheck\n")
        (out / "tb.cir").write_text(f"""* the extracted transistor against the schematic's
.lib "{pdk() / 'libs.tech' / 'ngspice' / 'sky130.lib.spice'}" tt
.include "{pex}"
VD d 0 0.9
VG g 0 0.9
XE 0 d 0 g flowtest
VD2 d2 0 0.9
XS d2 g 0 0 sky130_fd_pr__nfet_01v8 w=2 l=1
.control
op
let ie=-i(VD)
let ir=-i(VD2)
print ie ir
.endc
.end
""")
        done = subprocess.run(["ngspice", "-b", "tb.cir"], cwd=out, capture_output=True, text=True)
        got = dict(re.findall(r"^(ie|ir)\s*=\s*(\S+)", done.stdout, re.M))
        same = len(got) == 2 and abs(float(got["ie"]) / float(got["ir"]) - 1) < 0.02
        print(f"PEX in ngspice: {float(got.get('ie', 'nan')) * 1e6:.2f} µA extracted, "
              f"{float(got.get('ir', 'nan')) * 1e6:.2f} µA in the schematic"
              if len(got) == 2 else f"PEX in ngspice failed:\n{(done.stdout + done.stderr)[-1500:]}")
        return ok and same


def main() -> int:
    args = sys.argv[1:]
    if args[:1] == ["selftest"]:
        ok = selftest()
        print("Self-test passed." if ok else "Self-test FAILED.")
        return 0 if ok else 1
    if len(args) != 2 or args[0] not in ("drc", "lvs", "pex", "gds", "all"):
        print(__doc__.strip())
        return 2
    step, cell = args
    if not (MAG / f"{cell}.mag").is_file():
        sys.exit(f"No cell {cell} in {MAG.relative_to(ROOT)}/")
    ok = True
    for name, run in (("drc", drc), ("lvs", lvs)):
        if step in (name, "all"):
            ok = run(cell) and ok
            if not ok and step == "all":
                return 1
    if step in ("pex", "all"):
        print(f"PEX {cell}: {extract(cell)[1].relative_to(ROOT)}")
    if step in ("gds", "all"):
        gds(cell)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
