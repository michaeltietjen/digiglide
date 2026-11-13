"""HOLD on, short sequenced trigs: what do the chord voices' frame fields do after stock's own note has ended?
DigiGlide copies the source voice's velocity, curve, level, machine, track and sound record to every chord voice,
every block. Prints every change of those fields on voices 0..4 over 3000 playing frames.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python hold_fields.py IMAGE.syx"""
import os, sys, hashlib
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, U16, Ui, latest

img = sys.argv[1] if len(sys.argv) > 1 else latest()
s = Session(img, tag='holdf', solo=True, reserve=0)
s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=1))
for _ in range(3):
    s.k.tap('SYN')
for st, n in ((2, 64), (10, 59), (18, 55)):
    s.trig(st, note=n, length=2)
fr = s.play(3000, bpm=120)
last = {}
import struct
for i, f in enumerate(fr):
    on, off = U16(f, 0x22), U16(f, 0x24)
    row = [(U16(f, 0x34 + 2 * v), U16(f, 0x74 + 2 * v), U16(f, 0x94 + 2 * v), U16(f, 0xA5A + 2 * v)) for v in range(6)]
    if on or off or i % 100 == 0:
        print(f'F {i:5d} on {on:04x} off {off:04x} (vel, level, mach, trk) v0..5 {row}')
