# Design and debug diary

What I ran into while designing and laying out this comparator: the symptom, its cause, the
fix and the lesson. I work with Claude (Claude Code) as an assistant, and it found most of the
root causes, so every entry says who found what: what I claim as mine is what I did or worked
out myself. Newest entries go at the end of each day.

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
- **Found by:** Claude. I worked out the area arithmetic myself: doubling W and L multiplies
  the area by 4 and halves σ; going from 20 to 8 mV takes (20/8)² = 6.25 times the area.

### The requirement comes from the ADC's yield, not from a fixed offset
- **Symptom:** the ADC's budget gave the comparator ±8.16 mV, about 7 % of an LSB. I could
  not tell whether that was much or little.
- **Cause:** that budget assumed a fixed offset. With random offsets, a Monte Carlo of the
  ADC (100 000 per σ) showed that the binding requirement was the ±2 % gain error, about
  0.12 LSB, four times stricter than the others at ±0.5 LSB.
- **Decision:** the gain error went to ±0.5 LSB, like the rest, and the comparator aims at
  σ ≤ 8 mV. About 10 mV already gives 99.95 % of ADCs.
- **Found by:** Claude (the Monte Carlo); the decision was mine.

## 2026-10-29 · Reviewing the redesigned comparator

### `m=` without `mult=` overstates mismatch in SKY130
- **Symptom:** the redesign reported σ = 5.7 mV.
- **Cause:** SKY130 scales mismatch with 1/√(W·L·mult), where `mult` is a model parameter.
  ngspice's `m=` multiplies the current, but with `mult=1` the m fingers draw a single
  mismatch, as if they were one small device. On silicon each finger varies on its own.
  With `mult=` equal to `m=`, σ was 3.6 mV.
- **Lesson:** check what a simulator's multiplier means for statistics, not only for current.
- **Found by:** Claude, in review.

### A regular-Vt input pair left the tail source without headroom at the top tap
- **Symptom:** at the top tap (0.79 V), in ss at 1.6 V, the tail source XM5 had 9 mV across
  it and its current fell from 2 µA to 0.18 µA.
- **Cause:** the regular-Vt PMOS needs too much V_SG for that input range.
- **Fix:** a low-Vt pair: σ 5.2 mV and 1.87 µA at the top tap, with 0.28 V of headroom. It
  also makes every transistor low-Vt, which simplifies the layout's implants.
- **Found by:** Claude, in review.

## 2026-10-29 · The tools

### Magic on Tcl 9: the device generators fail
- **Symptom:** every generated device failed with `can't read "sky130::ruleset"`.
- **Cause:** Fedora 44 builds Magic on Tcl 9. The PDK reads `$sky130::ruleset` from inside the
  namespace `sky130`. Tcl 8 resolved that name globally; Tcl 9 reads it as
  `::sky130::sky130::ruleset`.
- **Fix:** a link in `mag/.magicrc`, without touching the PDK.
- **Found by:** Claude.

### Fedora's Netgen is from 2005
- **Symptom:** `netgen -batch lvs` waited for input instead of comparing.
- **Cause:** Fedora's `netgen` package is 1.3.7, with no `lvs` command.
- **Fix:** I built Netgen 1.5.326 from its source into `~/.local`.
- **Found by:** Claude; I did the build.

### GCC 16 compiles C23 by default, and Netgen's C does not
- **Symptom:** after the first build, `tclnetgen.so` was missing.
- **Cause:** C23 reads the old-style function pointer `int (*)()` as taking no arguments,
  and `base/netcmp.c` failed with 10 errors.
- **Fix:** `make EXTRA_CFLAGS=-std=gnu99`.
- **Found by:** Claude; I rebuilt it.

### Magic's console speaks Tcl, not bash
- **Symptom:** `cd ~/…/mag && magic` gave `wrong # args: should be "cd ?dirName?"`.
- **Cause:** I typed it in Magic's console, which runs Tcl; `&&` does not exist there.
- **Lesson:** start Magic from a terminal inside `mag/`, so that it reads `.magicrc`.
- **Found by:** me (the symptom); Claude (the cause).

### The device dialog failed too, for the same Tcl 9 reason
- **Symptom:** Devices 1 → nmos gave `can't set "magic::w_val": parent namespace doesn't
  exist`.
- **Cause:** Magic's own `toolkit.tcl` names its dialog's variables the way Tcl 9 no longer
  resolves.
- **Fix:** `mag/.magicrc` redefines the seven procedures with absolute names.
- **Found by:** me (the symptom); Claude (the cause and the fix).

## 2026-10-29 · The first layout: the NMOS mirror

### Magic is a paint program, not a PCB editor
- **Symptom:** shapes appeared that I had not meant to draw, and DRC rose to 12.
- **Cause:** in Magic, the middle button over the layout paints whatever is under the cursor
  into the box, and a key pressed over the layout runs a command.
- **Lesson:** type commands in the console. In the layout, the left and right buttons only
  place the box. `u` undoes.
- **Found by:** me, the hard way; Claude explained it.

### One device with six fingers instead of six devices
- **Choice:** the mirror is one 6-finger device in the order D B A A B D, so nothing has to be
  placed by hand. With shared diffusion a dummy touches its neighbour's strip, so the dummies
  sit next to B, the diode node `in`. That node has low impedance; next to A they would load
  `out`.
- **Found by:** Claude.

### The device type is in the cell's name
- **Symptom:** the generated cell was called `sky130_fd_pr__nfet_01v8_…`.
- **Cause:** I left the dialog's default type. The design uses `nfet_01v8_lvt`, and LVS would
  have failed on the device type.
- **Found by:** Claude, from my screenshot.

### `s` + `delete` did not delete an expanded instance
- **Cause:** with the cell expanded, `s` selects what is under the cursor inside it, not the
  instance.
- **Fix:** select it by its instance name: `select cell <name>`, then `delete`.
- **Found by:** me (the symptom); Claude (the fix).

### A generated device lands where the box is
- **Symptom:** the routing I pasted did not connect to the transistor.
- **Cause:** the box had moved between `box 0 0 0 0` and the generation, so the transistor
  sat 8.8 µm off the coordinates I was using.
- **Fix:** `select cell XM; move w 8.805um; move n 0.86um`.
- **Found by:** Claude, reading my `.mag` file.

### Labels need metal under them
- **Symptom:** `Moving label "in" from metal1 to space`.
- **Cause:** I pasted the port labels before the routing, so there was no metal under them.
- **Fix:** `erase labels`, then label after routing.
- **Found by:** Claude, reading my `.mag` file.

### Why the diffusion strips leave in metal2
- Between the gate-contact strips of neighbouring fingers there are 0.33 µm. A metal1 track
  needs 0.14 µm of width plus 0.14 µm of spacing on each side, 0.42 µm in all. So the strips
  go up or down in metal2, through a via.
- **Found by:** Claude, from the generator's geometry.

### A via (`m2contact`) in Magic
- In Magic, a contact is drawn as a layer, and its area already includes 0.055 µm of metal
  around the cut: the smallest is 0.26 × 0.26 µm.
- The rules ask for 0.03 µm more metal on two opposite sides, so the metal1 and metal2 pads
  are 0.26 × 0.32 µm.
- A cell's own metal must reach 0.083 µm² even when it sits on a subcell's metal.
- **Paint the contact last:** metal painted over a contact turns it into plain metal and
  splits it.
- **Found by:** Claude, in a prototype; I applied it to the `out` net.

### My two mistakes in the `out` net
- I left `um` off a number. Magic then reads it in lambda (0.01 µm), and the box would have
  painted metal over the gates.
- I gave the contact the pad's height. The pad must exceed the contact by 0.03 µm, or the
  via-enclosure rule fails.
- **Found by:** Claude, before I pasted them.

### `save` saves one cell; `writeall force` saves them all
- `save mirror` did not write the generated transistor's cell, so the extraction could not
  find it.
- **Found by:** Claude.

### Result
- The mirror passes `python3 scripts/flow.py all mirror`: no DRC errors, LVS matches
  `netlist/mirror.spice` uniquely, extraction and GDS done.
- **Who:** me, in Magic: the `vss` and `in` routing from Claude's commands, and the `out` net
  written by me.
