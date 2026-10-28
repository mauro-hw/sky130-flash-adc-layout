# sky130-comparator-layout

The layout of a continuous-time comparator in the SkyWater SKY130 open PDK, from the
schematic to the post-layout simulation: DRC, LVS, parasitic extraction and a comparison of
the pre-layout and post-layout performance in three process corners.

**Status:** work in progress. The pre-layout netlist is ready; the layout comes next.

Layout by **Mauro Rodriguez Blasco**. The circuit was designed with
[VibeSPICE](https://github.com/mauro-hw/vibespice), an agent by the same author that designs
and simulates analog circuits.

## The circuit

One of the seven comparators of a 3-bit flash ADC (input range 0 to 0.9 V, 1.8 V supply):
the output goes high when `inp` is above `inn`, its tap of the reference ladder.

- A PMOS low-Vt input pair, so that it works with inputs down to 0.1 V, with an NMOS
  current-mirror load.
- A common-source second stage and an inverter for a full logic level.
- About 0.9 µA per branch, set by a 1.3 MΩ high-resistivity poly resistor and a
  diode-connected PMOS.

Pre-layout netlist: [netlist/comparator.spice](netlist/comparator.spice).

Requirements, from the ADC's error budget, in every corner: offset within ±8.16 mV,
hysteresis at most 34.5 mV and supply current at most 3.29 µA.

## Pre-layout

The bias resistor as the PDK device (`sky130_fd_pr__res_xhigh_po_0p35`, 0.35 × 227.5 µm at
2 kΩ/□) instead of an ideal 1.3 MΩ. Supply current of one comparator, DC, both inputs at
0.45 V:

| Corner | Ideal resistor | PDK resistor |
|---|---|---|
| tt, 25 °C, 1.80 V | 1.564 µA | 1.560 µA |
| ss, 100 °C, 1.60 V | 1.284 µA | 1.392 µA |
| ff, −40 °C, 1.95 V | 1.776 µA | 1.616 µA |

The resistor's negative temperature coefficient narrows the spread across corners.

## Tools

| Step | Tool |
|---|---|
| Schematic | xschem 3.1.0 |
| Simulation | ngspice 47 |
| Layout, DRC and parasitic extraction | Magic |
| LVS | Netgen |
| PDK | sky130A, open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`, installed with volare |

## License

[Apache License 2.0](LICENSE). If you reuse or adapt this design, keep the [NOTICE](NOTICE)
file with it.
