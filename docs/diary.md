# Design and debug diary

What I ran into while designing and laying out this comparator: the symptom, its cause, the
fix and the lesson. I work with Claude (Claude Code) as an assistant throughout. Newest entries
go at the end of each day.

## 2026-10-28 · The circuit

### The first comparator met its offset nominally, but not with mismatch
- **Symptom:** the comparator's offset was −0.74 mV against a ±8.16 mV limit. With the PDK's
  mismatch models (`tt_mm`, 30 Monte Carlo runs) its standard deviation was 22.8 mV, and 23
  runs of 30 failed.
- **Cause:** the input pair was 4 × 0.5 µm and the mirror 1 × 1 µm. Random mismatch scales as
  σ(ΔVth) = A_VT / √(W·L) (Pelgrom), so tiny devices mismatch a lot.
- **Lesson:** process corners move every transistor together, so they create no offset; only
  local mismatch does. The layout fixes systematic mismatch (gradients), with common
  centroid and dummies, but not random mismatch: only device area reduces it.
- **Area:** doubling W and L multiplies the area by 4 and halves σ; going from 20 to 8 mV takes
  (20/8)² = 6.25 times the area.

### The requirement comes from the ADC's yield, not from a fixed offset
- **Symptom:** the ADC's budget gave the comparator ±8.16 mV, about 7 % of an LSB. I could
  not tell whether that was much or little.
- **Cause:** that budget assumed a fixed offset. With random offsets, a Monte Carlo of the
  ADC (100 000 per σ) showed that the binding requirement was the ±2 % gain error, about
  0.12 LSB, four times stricter than the others at ±0.5 LSB.
- **Decision:** the gain error went to ±0.5 LSB, like the rest, and the comparator aims at
  σ ≤ 8 mV. About 10 mV already gives 99.95 % of ADCs.

## 2026-10-29 · Reviewing the redesigned comparator

### `m=` without `mult=` overstates mismatch in SKY130
- **Symptom:** the redesign reported σ = 5.7 mV.
- **Cause:** SKY130 scales mismatch with 1/√(W·L·mult), where `mult` is a model parameter.
  ngspice's `m=` multiplies the current, but with `mult=1` the m fingers draw a single
  mismatch, as if they were one small device. On silicon each finger varies on its own.
  With `mult=` equal to `m=`, σ was 3.6 mV.
- **Lesson:** check what a simulator's multiplier means for statistics, not only for current.

### A regular-Vt input pair left the tail source without headroom at the top tap
- **Symptom:** at the top tap (0.79 V), in ss at 1.6 V, the tail source XM5 had 9 mV across
  it and its current fell from 2 µA to 0.18 µA.
- **Cause:** the regular-Vt PMOS needs too much V_SG for that input range.
- **Fix:** a low-Vt pair: σ 5.2 mV and 1.87 µA at the top tap, with 0.28 V of headroom. It
  also makes every transistor low-Vt, which simplifies the layout's implants.

## 2026-10-29 · The tools

### Magic on Tcl 9: the device generators fail
- **Symptom:** every generated device failed with `can't read "sky130::ruleset"`.
- **Cause:** Fedora 44 builds Magic on Tcl 9. The PDK reads `$sky130::ruleset` from inside the
  namespace `sky130`. Tcl 8 resolved that name globally; Tcl 9 reads it as
  `::sky130::sky130::ruleset`.
- **Fix:** a link in `mag/.magicrc`, without touching the PDK.

### Fedora's Netgen is from 2005
- **Symptom:** `netgen -batch lvs` waited for input instead of comparing.
- **Cause:** Fedora's `netgen` package is 1.3.7, with no `lvs` command.
- **Fix:** I built Netgen 1.5.326 from its source into `~/.local`.

### GCC 16 compiles C23 by default, and Netgen's C does not
- **Symptom:** after the first build, `tclnetgen.so` was missing.
- **Cause:** C23 reads the old-style function pointer `int (*)()` as taking no arguments,
  and `base/netcmp.c` failed with 10 errors.
- **Fix:** `make EXTRA_CFLAGS=-std=gnu99`.

### Magic's console speaks Tcl, not bash
- **Symptom:** `cd ~/…/mag && magic` gave `wrong # args: should be "cd ?dirName?"`.
- **Cause:** I typed it in Magic's console, which runs Tcl; `&&` does not exist there.
- **Lesson:** start Magic from a terminal inside `mag/`, so that it reads `.magicrc`.

### The device dialog failed too, for the same Tcl 9 reason
- **Symptom:** Devices 1 → nmos gave `can't set "magic::w_val": parent namespace doesn't
  exist`.
- **Cause:** Magic's own `toolkit.tcl` names its dialog's variables the way Tcl 9 no longer
  resolves.
- **Fix:** `mag/.magicrc` redefines the seven procedures with absolute names.

## 2026-10-29 · The first layout: the NMOS mirror

### Magic is a paint program, not a PCB editor
- **Symptom:** shapes appeared that I had not meant to draw, and DRC rose to 12.
- **Cause:** in Magic, the middle button over the layout paints whatever is under the cursor
  into the box, and a key pressed over the layout runs a command.
- **Lesson:** type commands in the console. In the layout, the left and right buttons only
  place the box. `u` undoes.

### One device with six fingers instead of six devices
- **Choice:** the mirror is one 6-finger device in the order D B A A B D, so nothing has to be
  placed by hand. With shared diffusion a dummy touches its neighbour's strip, so the dummies
  sit next to B, the diode node `in`. That node has low impedance; next to A they would load
  `out`.

### The device type is in the cell's name
- **Symptom:** the generated cell was called `sky130_fd_pr__nfet_01v8_…`.
- **Cause:** I left the dialog's default type. The design uses `nfet_01v8_lvt`, and LVS would
  have failed on the device type.

### `s` + `delete` did not delete an expanded instance
- **Cause:** with the cell expanded, `s` selects what is under the cursor inside it, not the
  instance.
- **Fix:** select it by its instance name: `select cell <name>`, then `delete`.

### A generated device lands where the box is
- **Symptom:** the routing I pasted did not connect to the transistor.
- **Cause:** the box had moved between `box 0 0 0 0` and the generation, so the transistor
  sat 8.8 µm off the coordinates I was using.
- **Fix:** `select cell XM; move w 8.805um; move n 0.86um`.

### Labels need metal under them
- **Symptom:** `Moving label "in" from metal1 to space`.
- **Cause:** I pasted the port labels before the routing, so there was no metal under them.
- **Fix:** `erase labels`, then label after routing.

### Why the diffusion strips leave in metal2
- Between the gate-contact strips of neighbouring fingers there are 0.33 µm. A metal1 track
  needs 0.14 µm of width plus 0.14 µm of spacing on each side, 0.42 µm in all. So the strips
  go up or down in metal2, through a via.

### A via (`m2contact`) in Magic
- In Magic, a contact is drawn as a layer, and its area already includes 0.055 µm of metal
  around the cut: the smallest is 0.26 × 0.26 µm.
- The rules ask for 0.03 µm more metal on two opposite sides, so the metal1 and metal2 pads
  are 0.26 × 0.32 µm.
- A cell's own metal must reach 0.083 µm² even when it sits on a subcell's metal.
- **Paint the contact last:** metal painted over a contact turns it into plain metal and
  splits it.

### My two mistakes in the `out` net
- I left `um` off a number. Magic then reads it in lambda (0.01 µm), and the box would have
  painted metal over the gates.
- I gave the contact the pad's height. The pad must exceed the contact by 0.03 µm, or the
  via-enclosure rule fails.

### `save` saves one cell; `writeall force` saves them all
- `save mirror` did not write the generated transistor's cell, so the extraction could not
  find it.

### Result
- The mirror passes `python3 scripts/flow.py all mirror`: no DRC errors, LVS matches
  `netlist/mirror.spice` uniquely, extraction and GDS done.

## 2026-10-30 · Learning to read a layout

### The 4:1 rectangle is the gate
- **What I saw:** each finger of the mirror is a hatched rectangle, 4 µm wide and 1 µm tall,
  between two narrow columns of contacts: the 4:1 of the netlist's L = 4 and W = 1.
- **What it is:** the channel, where the poly crosses the diffusion; Magic draws it as a layer
  of its own (`nmoslvt`). Along the current, from one column to the next, it measures
  L = 4 µm; across, W = 1 µm. The poly runs on past the diffusion, and the gate is contacted
  there, in the horizontal contact bars above and below each finger.
- **Drain and source** are the narrow columns of diffusion contacts between the gates. Each
  inner column is shared by the fingers on both sides of it.

### Nothing in the drawing tells drain from source
- **Cause:** a MOSFET is symmetric. The circuit decides which side is which: in an NMOS the
  source is the side at the lower voltage.
- **In the mirror:** columns 0, 2, 4 and 6 go down to the `vss` bus, so they are sources;
  1, 3 and 5 are drains. Because the columns are shared, neighbouring fingers face opposite
  ways: S D, D S, S D…
- **The generator's names don't help:** it labels the columns D0, S1, D2, S3… in turn,
  whatever they are wired to. In the mirror, S1 is a drain (`in`) and D2 a source (`vss`).
- **Lesson:** read a layout by following the metal from each column to its net.

### What makes a finger A or B
- All six fingers are identical; the wiring alone decides whose they are. In a mirror the
  gates and the sources are common, so only the drain tells the two transistors apart: B's
  drains (columns 1 and 5) go to `in`, the same net as the gates, which makes B the diode;
  A's drain (column 3) goes to `out`.
- I recognised the diode fingers by the metal2 "U" that shorts two terminals: its long leg
  goes down to the drain column, its short leg to the gate's contact bar.
- **Common centroid in one row:** counting the real fingers 1 to 4, B sits at 1 and 4 and A
  at 2 and 3. Both average 2.5, so a gradient along the row shifts A and B alike.

### What the dummies are for
- **Cause:** a finger at the end of a row has a gate on one side only. Its gate prints
  slightly differently, and the trench isolation where the diffusion ends presses on it,
  which changes its mobility and threshold. Without dummies the end fingers would both be
  B's: a systematic mismatch, the same in every chip.
- **Fix:** a dummy at each end, so that every real finger has a gate on both sides at the
  same distance.
- **Electrically they do nothing:** gate and source at `vss`, so V_GS = 0 and they are off.
  In ngspice the mirror's two dummies leak 1.5 pA in tt (11 pA in ss at 100 °C) beside the
  1 µA in `in`. They are still devices, though: LVS sees them, which is why
  `netlist/mirror.spice` lists them as XMD.
- **Cost:** area, and a little capacitance on the node they touch (see "One device with six
  fingers" above).

### A shared column serves two fingers of the same kind
- A column between two fingers is a terminal of both: two drains, two sources, or, in a
  series stack, the drain of one and the source of the next. It saves area and capacitance:
  in the pair's extraction an end column gives its one finger 0.58 µm² of junction, and a
  shared column gives each of its two fingers 0.29 µm².
- A PMOS and an NMOS never share one: P+ diffusion sits in an n-well, N+ diffusion in the
  p-substrate, and they meet only through metal.

## 2026-10-30 · The input pair

### Reading the pair
- The pair is two PMOS that share the 2 µA of the tail: the one whose gate is lower takes
  more of it, and the mirror turns the difference into `OUT1`. Any difference between XM1
  and XM2 shifts that split as an input voltage would: the offset.
- A finger's gate tells whose it is: on `inp` it is XM1, so its columns are `TAIL` (source)
  and `OUT1` (drain); on `inn` it is XM2, with `TAIL` and `XM2_drain`.
- The PMOS sources are on `TAIL`, not on `vdd`: XM5 sits between them and the supply. The
  fourth terminal, `vdd`, is the body, the n-well under the whole array.
- Columns, top row D A B B A D: vdd, OUT1, TAIL, XM2_drain, TAIL, OUT1, vdd. Bottom row
  D B A A B D: vdd, XM2_drain, TAIL, OUT1, TAIL, XM2_drain, vdd. The dummies touch `OUT1` in
  the top row and `XM2_drain` in the bottom one, so both drains carry two.

### Why the pair has two rows, and why the second is swapped
- **A transistor of several fingers behaves like their average:** they are in parallel. So
  where each finger sits decides how much of a position-dependent difference reaches XM1 or
  XM2; with a Vt that rises 1 mV per position, A at 1 and 2 and B at 3 and 4 differ by
  2 mV, while B at 1 and 4 and A at 2 and 3 do not differ at all.
- **Two rows do not add area:** the same eight units in one row would be a strip about
  25 µm long; in two rows they are a block of 15 × 7 µm, closer together. The arrangement
  only fights the systematic part, which depends on position. The random part shrinks only
  with gate area (Pelgrom), which the netlist sets.
- **The swap gives each transistor the same mix of positions:** A has the ends of the top row
  and the middle of the bottom one, B the opposite. Whatever depends on position, XM1 and XM2
  share it. The mirror's single row D B A A B D cancels a linear gradient but gives B both
  ends and A the middle, so a difference between the ends and the middle of the row, such as
  the end fingers' nearness to a well edge, becomes offset.
- **The mirror is not less important:** at the switching point gm₃/gm₁ ≈ 0.9, so a mV of
  mismatch in the mirror counts almost as much at the input as one in the pair. It stayed in
  one row because it was the first layout; a 2 × 2 cross-quad (A B / B A) would do better.

### `writeall force` broke a transistor that was not expanded
- **Symptom:** in a test of the bottom row on a copy, after `load pair` in a new Magic session,
  painting and `writeall force`, the transistor's cell came back with 20 DRC errors inside it.
- **Cause:** Magic rewrote the unexpanded cell without its `magscale 1 2`, at half the
  resolution, rounding every coordinate (1541 became 770).
- **Fix:** `select top cell` and `expand` before saving; expanded, it is written intact.

## 2026-10-30 · How the comparator decides

### Four blocks, one chain
- **Bias:** R1–R4 and the diode XM8 set about 1 µA. XM5 and XM7 share XM8's gate, `VBIAS`,
  and copy it: 2 µA into `TAIL`, 1 µA into `out`.
- **Input pair:** with `inp` above `inn`, XM1, a PMOS, gets less V_SG and takes less of the
  2 µA; XM2 takes more.
- **Mirror load:** XM4 carries XM2's current and XM3 copies it, pulling it out of `OUT1`
  while XM1 pushes its own in. XM3 now pulls more than XM1 gives, so `OUT1` falls.
- **Second stage:** XM7 pushes a fixed 1 µA into `out`; XM6, with its gate on `OUT1`, pulls.
  `OUT1` lower makes XM6 weaker, XM7 wins, and `out` rises.
- Two inverting stages make a non-inverting whole: `inp` up, `OUT1` down, `out` up.

### Each stage is like an inverter, not like a divider
- A pull-up and a pull-down in series, with the output between them. But in saturation each
  is close to a current source, so when their currents disagree the node does not settle
  nearby, as between two resistors: it moves until one transistor leaves saturation.
- In tt, at the middle tap, going from −1 to +1 mV between the inputs changes the pair's
  currents by about 15 nA (1.5 %), yet moves `OUT1` from 0.640 to 0.506 V, a gain of about 67,
  and `out` from 0.070 to 1.753 V.

### XM6 does not have to turn off
- **What I thought:** `out` rises because `OUT1` falls below XM6's threshold.
- **What happens:** XM6's Vth is 0.445 V, and at 0.506 V it is still on, but it can pull only
  0.40 µA, less than XM7's 1 µA. At the balance point, `OUT1` ≈ 0.573 V, it pulls 1.09 µA.
- **Lesson:** a stage switches when one side becomes weaker than the other, not when a
  transistor turns off.

## 2026-10-30 · The second stage

### One NMOS, four decisions
- **Matching:** XM6's errors reach the input divided by the first stage's gain. In tt, 5 % more
  current in XM6 moves the offset by 0.06 mV; the same in XM3, before the gain, by 3.8 mV. So
  no common centroid and no dummies; being the mirror's unit takes care of the systematic part.
- **Placement:** its own cell, next to the mirror: its gate is XM3's drain, so `OUT1` stays
  short.
- **Columns `vss | out | vss`:** `out` gets the shared column, 0.29 µm² of junction instead
  of 0.58 µm² on two outer ones, so the loudest node has half the capacitance. The `vss`
  columns tie straight to the ring.
- **Surroundings:** a guard ring, the body contact, which also collects the charge that
  `out`'s swings push into the substrate before it reaches the mirror.
- **Measured and rejected:** dropping the bottom gate contacts would save 0.35 fF on `OUT1`,
  under 1 % of the 40 fF of XM6's own gate. Not worth it.

### Quiet on top, loud at the bottom
- `OUT1` enters on a metal1 bar laid over the gates' top contacts, which already carry metal1,
  so no via is needed.
- `out` cannot leave the middle column downwards in metal1: between the bottom gate contacts
  there are 0.33 µm, and a metal1 track needs 0.42. It goes up a via to metal2 and passes over
  them, as a PCB trace changes layer to cross another.
- The layers are not the point; the sides are. `OUT1` and `out` never run side by side.

### Result
- `python3 scripts/flow.py all stage2`: no DRC errors, LVS matches `netlist/stage2.spice`
  uniquely, extraction and GDS done.

## 2026-10-30 · The bias mirror

### A mirror with three outputs
- XM8 (the diode, `VBIAS`), XM5 (`TAIL`, ×2) and XM7 (`out`, ×1) are PMOS of one unit
  (W = 2, L = 1), with their gates on `VBIAS` and their sources on `vdd`: only the drains differ.
- **Matching is not critical:** in tt, 5 % more current in any of them changes the tail current
  by about 3 % but the offset by 0.03 mV at most. XM5 and XM8 set the tail, which both halves of
  the pair share; XM7 comes after the first stage's gain, like XM6.

### The order: D 8 5 5 7 7 5 5 8 D
- With shared diffusion, neighbours of different transistors must share `vdd`, so a single
  finger between two different ones would have `vdd` on both columns and do nothing. In a
  symmetric row only two orders work: XM7 at the ends and XM8 in the middle, or the reverse.
- I chose XM8 at the ends and XM7 in the middle. `out` gets one shared column, 0.58 µm² of
  junction instead of 1.16 µm², and leaves by one short riser instead of a wire along the row.
  The dummies touch `VBIAS`, a DC node where their capacitance helps keep it still.
- Quiet on top: the `VBIAS` gate bar, the diode's two "U"s and the `vdd` bus. Loud at the
  bottom: `out`, with `TAIL`. `out` has to cross the `TAIL` bus, because `TAIL`'s two columns
  straddle it; `TAIL` is common to both halves of the pair, which rejects what couples into it.

### Spacing rules apply inside one net
- **Symptom:** in the draft, 6 × "Metal2 spacing < 0.14um" in the diode's "U"s.
- **Cause:** the top of each "U" was 0.12 µm above the pad of its own via: one net, but a
  notch narrower than the rule.
- **Fix:** the "U"s 0.1 µm higher.

### Result
- `python3 scripts/flow.py all bias`: no DRC errors, LVS matches `netlist/bias.spice`
  uniquely, extraction and GDS done.

## 2026-10-30 · The bias resistor

### Its value sets the currents, not the offset
- In tt, 5 % more resistance lowers the tail current by 4.3 % and moves the offset by
  0.001 mV: every mirror copies the same reference, so all the currents scale together. The
  value decides speed and power, and the process moves this poly's resistance by more than
  that anyway; that is why the circuit is checked in three corners.
- So no dummies: in series, a slightly different outer strip changes only the total. The
  generator's `dummy` option draws none for this resistor anyway.

### Four strips in series: a serpentine
- The generator draws four separate strips, 0.35 × 55 µm and 0.83 µm apart, with a contact at
  each end: a block of about 4.5 × 61 µm, four times longer than any other.
- Joined in esses (tops of strips 1–2, bottoms of 2–3, tops of 3–4), every link is a 0.83 µm
  jump between neighbours; any other order needs a 55 µm wire alongside the strips. With an
  even number of strips, both ends, `VBIAS` on strip 1 and `vss` on strip 4, come out on the
  same side.
- All in metal1: the terminals carry metal1 already, and the guard ring is local interconnect
  only, so metal1 crosses it.

### Result
- `python3 scripts/flow.py all rbias`: no DRC errors, LVS matches `netlist/rbias.spice`
  uniquely, extraction and GDS done.

## 2026-10-30 · The top cell

### The floorplan: which wire may be long
- The blocks measure, in µm: bias 14.6 × 5.8, pair 15.4 × 13.2, mirror 27.4 × 4.1, stage2
  10.3 × 3.7 and the resistor 4.5 × 61.4. The resistor alone sets the comparator's height.
- In any order one wire is long: XM7 lives in the bias mirror, because it shares `VBIAS` with
  XM8, and XM6 next to the mirror, so that `OUT1` stays short. The decision is which net may
  be long and where it runs.
- My first stack (bias, pair, mirror, stage2) made `out` cross the whole height past the
  inputs and `OUT1`. Putting stage2 under the bias mirror only moved the long wire to `TAIL`.
- Final: stage2 beside the bias mirror, so `out` stays short, under the two blocks. `OUT1`
  reaches stage2 from the pair's top `out1` bus, which the pair already joins to its bottom
  one. The resistor on the left, upside down, so `VBIAS` goes straight from the bias mirror's
  gate bar to its terminals without crossing anything.
- In the extraction, `out` couples 0.06 fF to `inn` and practically nothing to `inp`, and
  `inp`–`OUT1` (1.76 fF) and `inn`–`XM2_drain` (1.73 fF) are nearly equal.

### Square ends on wires
- **Symptom:** 5 × "Metal2 width < 0.14um", at the corners of the L-shaped joints.
- **Cause:** each segment stopped at the centre line of the other, leaving a notch of
  0.07 µm on the outer corner.
- **Fix:** every metal2 line runs 0.07 µm past its end points.

### The dummies belong in the reference netlist
- LVS compares the layout with the netlist, and the layout has eight dummies: two on each
  drain of the pair, two on the mirror's diode node and two on `VBIAS`. They are now in
  `netlist/comparator.spice`; switched off, they change nothing nominal.

### A Monte Carlo's σ is itself uncertain
- With 112 copies the estimate of σ moves from one random draw to another: 5.18, 5.88 and
  5.32 mV with seeds 7, 8 and 9 on the same netlist. Adding the dummies changes the draw of
  almost every copy, so with seed 7 σ went from 5.18 to 5.36 mV with no change in the circuit.
- **Lesson:** compare σ before and after layout within that noise, about ±0.4 mV here.

### What the layout changes: speed, not DC
- The same `sim.py` on the extracted netlist: the offset without mismatch, the current and the
  output levels are identical, and σ (5.23 mV in tt) stays within its noise. Capacitance does
  nothing in DC.
- A transient shows the cost: the slowest tap's delay at 10 mV overdrive goes from 204 to
  254 ns with `out` rising and from 106 to 148 ns falling in tt, 22 to 41 % in the three
  corners.
- In tt the drawn junctions add 5 ns and the wiring the rest, mostly on `OUT1`: 11.5 fF next to
  the 40 fF of XM6's gate, on the node that decides.

### Result
- `python3 scripts/flow.py all comparator`: no DRC errors, LVS matches
  `netlist/comparator.spice` uniquely, extraction and GDS done. The whole comparator is laid
  out.

## 2026-10-30 · The reference ladder

### For 3 bits, the ladder's matching hardly matters
- 16 strips `res_high_po_1p41`, 1.41 × 47 µm, two per step: 11.06 kΩ each in tt, 177 kΩ in all,
  5.1 µA from the 0.9 V reference.
- With the PDK's mismatch models, 200 ladders give a tap error of σ = 0.42 mV (the comparator's
  offset: 5.3 mV), and at worst 0.011 LSB of DNL and 0.018 LSB of INL, against ±0.5 LSB. An LSB
  is 112.5 mV; even a gradient of 10 % from end to end would bend the INL by about 0.1 LSB.
- So the decisions were about fitting the ladder to the comparators, not about matching.

### Every tap on the same edge
- Each step goes up one strip and down the next, so every two strips the serpentine is back on
  the bottom edge: `vss`, the seven taps and `top` all leave there, one every 3.78 µm. The top
  edge only has the middle of each step.

### Compact, not spread out
- One block beside the comparators, rather than each step next to its own comparator: the
  routing is predictable, the strips share their surroundings, and the generator builds it in
  one piece. Its cost, seven tap wires fanning out to comparators 34 µm apart, comes when the
  ADC is assembled.

### Dummies in a resistor array
- A strip's resistance depends on its width, which etching sets. The outer strips have empty
  space on one side, so their edges etch differently and they come out slightly off. Without
  dummies those would be the first step's strip (at `vss`) and the last one's (at `top`).
- A dummy at each end takes the edge. Its two ends are tied to `vss`, so it carries no current
  and does not float. The generator's `dummy` option draws none for this resistor, so the block
  has 18 strips and the outer two are the dummies. LVS counts them as devices, so they are in
  the reference netlist.

### Result
- `python3 scripts/flow.py all ladder`: no DRC errors, LVS matches `netlist/ladder.spice`
  uniquely, extraction and GDS done.

## 2026-10-31 · The encoder

### Digital layout: compact and orderly, nothing to match
- The encoder turns the 7 comparator outputs (a thermometer code) into 3 bits with 11 gates:
  5 inverters, 5 NAND2 and 1 NAND4, 38 transistors, all L = 1 µm. A gate either switches or
  it does not, so nothing has to match; the layout only has to be compact and regular.
- Each gate is drawn like a standard cell: the PMOS on top, in its n-well and ring, whose top
  side is the `vdd` rail; the NMOS below, whose ring's bottom side is the `vss` rail. Each input
  is a metal1 line from the NMOS gate's contact to the PMOS gate's. Poly cannot go straight
  through: it would cross the rings' diffusion and make a transistor there.

### Series and parallel transistors share diffusion differently
- The NMOS of a NAND are in series: they share their middle column, `y | mid | vss`, which
  connects to nothing else.
- The PMOS are in parallel: either `vdd | y | vdd` or `y | vdd | y`. I chose the first, as for
  XM6: `y` on one shared column has half the junction and one pin. Its cost is a short jog in
  metal2 to the NMOS's `y`, at the end of the series stack. The NAND4: `vdd | y | vdd | y | vdd`.

### Gates side by side
- Each gate's ring overlaps its neighbour's along their shared side, so the n-wells and the
  rails join into one, as in a row of standard cells.
- **Symptom:** in the first draft, 40 × "mcon.spacing < 0.19um" and 160 × "Metal1 spacing" at
  the rails, where two gates meet.
- **Cause:** with 100 % coverage, the contacts on the generator's ring ran to 0.085 µm from
  each corner, so two neighbours' were 0.17 µm apart; and each ring's metal1 stopped 0.05 µm
  from its neighbour's.
- **Fix:** rings generated with 80 % contact coverage (`viagt 80`, `viagb 80`), and one
  continuous metal1 strip along each rail.

### The order of the row
- N12 I2 N24 N34 I4 Nb0 Ib2 N56 I6 Nb1 I7: the inputs `t1` to `t7` arrive in order, from the
  7 comparators side by side, and each pair's gates sit together. The nets between gates take
  4 tracks under the row; the two longest are `N24` and `T7_B`.
- The inputs leave at the bottom, towards the comparators, and the bits at the top.

### A missing gate that only LVS saw
- **Symptom:** the encoder had no DRC errors, but LVS failed on its pins: `b0` had no pin.
- **Cause:** I ran the encoder's block before the NAND4 existed. `getcell nand4` placed nothing
  and the rest of the block carried on, so all its wiring was there, waiting for a gate.
- **Fix:** `getcell nand4` at its place, then `save encoder`.
- **Lesson:** DRC checks that what is drawn can be built; only LVS checks that it is the
  circuit.

### Result
- `python3 scripts/flow.py all` for `inv`, `nand2`, `nand4` and `encoder`: no DRC errors, LVS
  matches each reference uniquely. The extracted encoder gives the 8 codes right in tt, ss and
  ff.

## 2026-10-31 · Folding the bias resistor

### Half the comparator was empty
- **What I saw:** the comparator was 34 × 61 µm, and the 4 strips of 55 µm of the bias resistor
  set its height; the rest of it (bias, pair, mirror) was only 27 µm tall, so a pocket of
  29 × 34 µm under the mirror held nothing.
- **What I did:** a resistor's value depends on its total length, not on how many pieces it is
  cut into, so the same 220 µm can be drawn as more, shorter strips in series: wider and
  shorter. Ten strips of 22 µm make a block of 9.5 × 28.4 µm, as tall as the rest.
- **The cost:** each strip adds the resistance of its two contacts, so 10 strips measure 0.3 %
  more than 4 (1.267 MΩ instead of 1.263 MΩ in tt). For this resistor 5 % moves the offset by
  0.001 mV.
- **LVS:** Netgen adds the lengths of resistors in series, so the 10 strips of 22 µm match the
  netlist's 4 of 55 µm and the netlist stays as designed.
- **Its two ends:** with an even number of strips both stay on one edge. The resistor goes in
  rotated 180°, so that `VBIAS`, the 1.26 MΩ node, is the end next to the bias mirror, and
  `vss`, of low impedance, the far one.
- **Result:** the comparator went from 34 × 61 µm to 39.0 × 28.4 µm, 47 % less area, with no
  empty pocket. I first tried 8 strips (37.4 × 33.9 µm), and once I saw it, 10 fitted better.
- **After layout:** the same `sim.py` on the folded comparator's extraction gives the same delays
  (254 / 149 ns in tt), the same offset without mismatch, 0.3 % less current and σ = 4.91 mV, a
  new random draw because the extracted netlist now has ten strips.
