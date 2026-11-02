v {xschem version=3.1.0 file_version=1.2
* SPDX-License-Identifier: Apache-2.0
* Copyright 2026 Mauro Rodriguez Blasco
*
* The 3-bit flash ADC's top level, the schematic of netlist/adc.spice: the reference ladder,
* the seven comparators and the encoder. Open it with: xschem --rcfile xschem/xschemrc xschem/adc.sch
}
G {}
K {}
V {}
S {}
E {}
N 120 1020 120 1040 {lab=tap1}
N 120 1160 120 1180 {lab=vss}
C {res_high_po_1p41.sym} 120 1070 0 0 {name=R1 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
C {res_high_po_1p41.sym} 120 1130 0 0 {name=R2 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
N 120 860 120 880 {lab=tap2}
N 120 1000 120 1020 {lab=tap1}
C {res_high_po_1p41.sym} 120 910 0 0 {name=R3 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
C {res_high_po_1p41.sym} 120 970 0 0 {name=R4 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
N 120 700 120 720 {lab=tap3}
N 120 840 120 860 {lab=tap2}
C {res_high_po_1p41.sym} 120 750 0 0 {name=R5 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
C {res_high_po_1p41.sym} 120 810 0 0 {name=R6 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
N 120 540 120 560 {lab=tap4}
N 120 680 120 700 {lab=tap3}
C {res_high_po_1p41.sym} 120 590 0 0 {name=R7 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
C {res_high_po_1p41.sym} 120 650 0 0 {name=R8 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
N 120 380 120 400 {lab=tap5}
N 120 520 120 540 {lab=tap4}
C {res_high_po_1p41.sym} 120 430 0 0 {name=R9 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
C {res_high_po_1p41.sym} 120 490 0 0 {name=R10 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
N 120 220 120 240 {lab=tap6}
N 120 360 120 380 {lab=tap5}
C {res_high_po_1p41.sym} 120 270 0 0 {name=R11 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
C {res_high_po_1p41.sym} 120 330 0 0 {name=R12 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
N 120 60 120 80 {lab=tap7}
N 120 200 120 220 {lab=tap6}
C {res_high_po_1p41.sym} 120 110 0 0 {name=R13 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
C {res_high_po_1p41.sym} 120 170 0 0 {name=R14 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
N 120 -100 120 -80 {lab=vref}
N 120 40 120 60 {lab=tap7}
C {res_high_po_1p41.sym} 120 -50 0 0 {name=R15 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
C {res_high_po_1p41.sym} 120 10 0 0 {name=R16 L=47 model=res_high_po_1p41 spiceprefix=X mult=1}
N 100 -50 100 10 {lab=vss}
N 100 10 100 110 {lab=vss}
N 100 110 100 170 {lab=vss}
N 100 170 100 270 {lab=vss}
N 100 270 100 330 {lab=vss}
N 100 330 100 430 {lab=vss}
N 100 430 100 490 {lab=vss}
N 100 490 100 590 {lab=vss}
N 100 590 100 650 {lab=vss}
N 100 650 100 750 {lab=vss}
N 100 750 100 810 {lab=vss}
N 100 810 100 910 {lab=vss}
N 100 910 100 970 {lab=vss}
N 100 970 100 1070 {lab=vss}
N 100 1070 100 1130 {lab=vss}
N 100 1130 100 1180 {lab=vss}
N 100 1180 120 1180 {lab=vss}
C {lab_pin.sym} 120 1180 0 1 {name=pvss lab=vss}
C {comparator.sym} 400 1000 0 0 {name=X1}
N 120 1020 340 1020 {lab=tap1}
C {lab_pin.sym} 400 960 0 1 {name=pv1 lab=vdd}
C {lab_pin.sym} 400 1040 0 1 {name=ps1 lab=vss}
N 300 980 340 980 {lab=vin}
C {comparator.sym} 400 840 0 0 {name=X2}
N 120 860 340 860 {lab=tap2}
C {lab_pin.sym} 400 800 0 1 {name=pv2 lab=vdd}
C {lab_pin.sym} 400 880 0 1 {name=ps2 lab=vss}
N 300 820 340 820 {lab=vin}
C {comparator.sym} 400 680 0 0 {name=X3}
N 120 700 340 700 {lab=tap3}
C {lab_pin.sym} 400 640 0 1 {name=pv3 lab=vdd}
C {lab_pin.sym} 400 720 0 1 {name=ps3 lab=vss}
N 300 660 340 660 {lab=vin}
C {comparator.sym} 400 520 0 0 {name=X4}
N 120 540 340 540 {lab=tap4}
C {lab_pin.sym} 400 480 0 1 {name=pv4 lab=vdd}
C {lab_pin.sym} 400 560 0 1 {name=ps4 lab=vss}
N 300 500 340 500 {lab=vin}
C {comparator.sym} 400 360 0 0 {name=X5}
N 120 380 340 380 {lab=tap5}
C {lab_pin.sym} 400 320 0 1 {name=pv5 lab=vdd}
C {lab_pin.sym} 400 400 0 1 {name=ps5 lab=vss}
N 300 340 340 340 {lab=vin}
C {comparator.sym} 400 200 0 0 {name=X6}
N 120 220 340 220 {lab=tap6}
C {lab_pin.sym} 400 160 0 1 {name=pv6 lab=vdd}
C {lab_pin.sym} 400 240 0 1 {name=ps6 lab=vss}
N 300 180 340 180 {lab=vin}
C {comparator.sym} 400 40 0 0 {name=X7}
N 120 60 340 60 {lab=tap7}
C {lab_pin.sym} 400 0 0 1 {name=pv7 lab=vdd}
C {lab_pin.sym} 400 80 0 1 {name=ps7 lab=vss}
N 300 20 340 20 {lab=vin}
N 300 980 300 820 {lab=vin}
N 300 820 300 660 {lab=vin}
N 300 660 300 500 {lab=vin}
N 300 500 300 340 {lab=vin}
N 300 340 300 180 {lab=vin}
N 300 180 300 20 {lab=vin}
N 300 980 300 1120 {lab=vin}
C {ipin.sym} 300 1120 3 0 {name=p1 lab=vin}
C {ipin.sym} 120 -100 1 0 {name=p2 lab=vref}
N 460 1000 640 1000 {lab=t1}
N 640 1000 640 580 {lab=t1}
N 640 580 700 580 {lab=t1}
N 460 840 620 840 {lab=t2}
N 620 840 620 560 {lab=t2}
N 620 560 700 560 {lab=t2}
N 460 680 600 680 {lab=t3}
N 600 680 600 540 {lab=t3}
N 600 540 700 540 {lab=t3}
N 460 520 700 520 {lab=t4}
N 460 360 600 360 {lab=t5}
N 600 360 600 500 {lab=t5}
N 600 500 700 500 {lab=t5}
N 460 200 620 200 {lab=t6}
N 620 200 620 480 {lab=t6}
N 620 480 700 480 {lab=t6}
N 460 40 640 40 {lab=t7}
N 640 40 640 460 {lab=t7}
N 640 460 700 460 {lab=t7}
C {encoder.sym} 780 520 0 0 {name=X8}
C {lab_pin.sym} 780 410 0 0 {name=pv8 lab=vdd}
C {lab_pin.sym} 780 630 0 0 {name=ps8 lab=vss}
N 860 500 920 500 {lab=b2}
C {opin.sym} 920 500 0 0 {name=pb2 lab=b2}
N 860 520 920 520 {lab=b1}
C {opin.sym} 920 520 0 0 {name=pb1 lab=b1}
N 860 540 920 540 {lab=b0}
C {opin.sym} 920 540 0 0 {name=pb0 lab=b0}
C {iopin.sym} 760 -60 0 0 {name=p3 lab=vdd}
C {iopin.sym} 760 -20 0 0 {name=p4 lab=vss}
T {3-bit flash ADC, top level} 520 -150 0 0 0.5 0.5 {}
T {reference ladder: 16 x res_high_po_1p41, L = 47 um, two per step} 150 -110 0 0 0.25 0.25 {}
