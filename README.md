# sky130-comparator-layout

The layout of a continuous-time comparator in the SkyWater SKY130 open PDK, from the
schematic to the post-layout simulation: DRC, LVS, parasitic extraction and a comparison of
the pre-layout and post-layout performance in three process corners.

**Status:** the circuit is designed and verified before layout; the layout comes next.

Layout by **Mauro Rodriguez Blasco**. The circuit was designed in
[VibeSPICE](https://github.com/mauro-hw/vibespice), an agent by the same author that designs
and simulates analog circuits, with Claude Code (Anthropic) as its agent, and reviewed with
Claude.

## The circuit

One of the seven comparators of a 3-bit flash ADC: 1.8 V supply, input range 0 to 0.9 V, so
`inn` sits at one of the taps 0.1125 to 0.7875 V. The output goes high when `inp` is above
`inn`.

- **First stage:** a low-Vt PMOS input pair, so that it works from the lowest tap up, with
  an NMOS current-mirror load.
- **Second stage:** an NMOS common-source stage that gives a full logic level.
- **Bias:** about 1 µA from four equal high-resistivity poly segments (1.26 MΩ) and a diode
  PMOS. The tail carries 2 µA and the second stage 1 µA.

Pre-layout netlist, the reference for LVS: [netlist/comparator.spice](netlist/comparator.spice).

| Device | Role | Type | Unit W × L (µm) | Units | Gate area |
|---|---|---|---|---|---|
| XM1, XM2 | input pair | pfet_01v8_lvt | 2 × 2 | 4 each | 16 µm² each |
| XM3, XM4 | mirror load | nfet_01v8_lvt | 1 × 4 | 2 each | 8 µm² each |
| XM6 | second stage | nfet_01v8_lvt | 1 × 4 | 2 | 8 µm² |
| XM8, XM5, XM7 | bias diode, tail, second-stage load | pfet_01v8_lvt | 2 × 1 | 2, 4, 2 | 4, 8, 4 µm² |
| XR1–XR4 | bias resistor | res_xhigh_po_0p35 | 0.35 × 55 | 4 in series | 1.26 MΩ |

Every transistor is a unit repeated `m` times with `mult` equal to `m`, so that the PDK's
mismatch averages over the fingers as it would on silicon. All the transistors are low-Vt.

## Requirements

They come from the ADC. With random comparator offsets, a Monte Carlo of the ADC (no missing
codes; DNL, INL, offset and gain error within ±0.5 LSB) shows that 99.9 % of ADCs work when
the comparators' offset has a standard deviation of about 10 mV or less. The comparator aims
at **σ ≤ 8 mV** in every corner, which leaves room for the ladder and the reference. It must
also work over the whole input range at 1.60 V.

## Pre-layout results

`python3 scripts/sim.py`: 112 copies with the PDK's mismatch models, 16 at each tap, and the
nominal circuit, in the three sign-off corners. The same script will run the extracted
netlist.

| | tt, 25 °C, 1.80 V | ss, 100 °C, 1.60 V | ff, −40 °C, 1.95 V |
|---|---|---|---|
| Offset σ, with mismatch | 5.18 mV | 5.16 mV | 5.18 mV |
| Offset mean; min / max | −0.76; −11.1 / +14.4 mV | −0.79; −11.1 / +14.3 mV | −0.75; −11.0 / +14.5 mV |
| Offset without mismatch, worst tap | −0.13 mV | −0.19 mV | +0.10 mV |
| Supply current, largest | 4.55 µA | 4.31 µA | 4.63 µA |
| Output high / low | 1.800 V / 39 mV | 1.600 V / 75 mV | 1.950 V / 21 mV |
| Tail at the top tap, V<sub>SD</sub> / current | 0.41 V / 2.01 µA | 0.28 V / 1.87 µA | 0.52 V / 2.03 µA |

In VibeSPICE, the whole ADC with seven of these comparators and one mismatch sample has no
missing codes, a DNL of 0.19 LSB and an INL of 0.15 LSB in every corner.

## How the design got here

1. **A first version met its offset nominally but not with mismatch.** Its input pair
   (4 × 0.5 µm) and mirror (1 × 1 µm) gave an offset with a 20 mV standard deviation. No
   layout technique fixes random mismatch: only device area does (Pelgrom).
2. **The requirement was set from the ADC's yield**, not from a fixed offset. The ADC's
   gain-error limit was relaxed to ±0.5 LSB, like the others; at ±2 % it alone would have
   asked for σ ≤ 3.5 mV.
3. **VibeSPICE redesigned the comparator** with a regular-Vt input pair, at a reported
   σ = 5.7 mV.
4. **A review found two problems:**
   - **Overstated mismatch.** The transistors used `m=` without `mult=`. SKY130's mismatch
     scales with 1/√(W·L·mult), so the m fingers varied as one. With `mult=` equal to `m=`,
     σ was 3.6 mV.
   - **No headroom at the top tap.** The regular-Vt pair needed so much V<sub>SG</sub> that
     at a 0.79 V input the tail source had 9 mV across it in ss. Its current fell from 2 µA
     to 0.18 µA.

   A low-Vt pair fixes the second and keeps σ at 5.2 mV.

## Layout plan

- **Input pair:** 8 units in a 2 × 4 common-centroid array, rows ABBA / BAAB, with a dummy at
  each row end, gates of the dummies to vdd. One n-well with an n+ guard ring.
- **Mirror load and second stage:** one row, D 6 A B B A 6 D, with a p+ guard ring.
- **Bias mirror:** one row, D 7 5 5 8 8 5 5 7 D.
- **Bias resistor:** four parallel strips with a dummy strip at each side.
- **Routing:**
  - OUT1 and XM2_drain: equal, short and equally loaded.
  - TAIL: short and symmetric to both halves of the pair.
  - inp and inn: routed symmetrically.
  - VBIAS (about 1 MΩ): away from `out`, which swings rail to rail.

## The flow

The layout cells live in `mag/`; start Magic there (`cd mag && magic`) and it reads
[mag/.magicrc](mag/.magicrc). The checks run without a window:

```bash
python3 scripts/flow.py selftest          # the tools, on a transistor Magic generates
python3 scripts/flow.py all comparator    # DRC, LVS against netlist/comparator.spice, PEX, GDS
python3 scripts/sim.py build/comparator_pex.spice    # the same table as above, after layout
```

| Step | Tool |
|---|---|
| Schematic | xschem 3.1.0 |
| Simulation | ngspice 47 |
| Layout, DRC and parasitic extraction | Magic 8.3.685 (Fedora 44, on Tcl 9) |
| LVS | Netgen 1.5.326, built from source |
| PDK | sky130A, open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`, installed with volare |

Three traps of this setup:
- Fedora 44's Magic runs on Tcl 9. This open_pdks reads a variable of its device generators
  in a way that Tcl 9 no longer resolves, and every generated device fails. The fix is one
  line in `mag/.magicrc`.
- Fedora's `netgen` package is version 1.3.7, from 2005, with no `lvs` command. Netgen 1.5 is
  built from [its source](https://github.com/RTimothyEdwards/netgen) into `~/.local`.
- GCC 16 compiles C23 by default, and one of Netgen's files does not build under it. The fix
  is `make EXTRA_CFLAGS=-std=gnu99`.

## License

[Apache License 2.0](LICENSE). If you reuse or adapt this design, keep the [NOTICE](NOTICE)
file with it.
