"""Which trig-default bytes do what (stock OS): one trig on step 3 of track 1, one default byte changed at a time,
400 blocks played; prints the note-ons (block, note, velocity) and note-offs the frames carry. Finds retrig,
probability and condition for the DigiGlide recording tests.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python trig_bytes.py"""
import os, sys, time
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, U16
from osver import A

t0 = time.time()
s = Session(None, tag='trigbytes', solo=True, reserve=0)
k, h = s.k, s.k.h
k.select(1, track=0)
d = s.trig_defaults(0)
base = bytes(h.r(d - 8, 40))
print('defaults -8..+32:', base.hex(' '), f'({time.time() - t0:.0f} s)', flush=True)


def run(label):
    k.call(A(0x40054690), [s.ctx0, 2, 1, 1])
    fr = s.play(700, bpm=120)
    ons = [(i, U16(f, 2 + 2 * v) >> 8, U16(f, 0x34 + 2 * v)) for i, f in enumerate(fr) for v in range(16) if U16(f, 0x22) >> v & 1]
    offs = [i for i, f in enumerate(fr) if U16(f, 0x24)]
    print(f'{label:14s} ons {ons[:10]} offs {offs[:10]} ({time.time() - t0:.0f} s)', flush=True)
    k.call(A(0x40054690), [s.ctx0, 2, 1, 0])
    h.w(d, base[8:40])


h.w(d + 1, bytes([20])); h.w(d + 5, bytes([60]))
base = bytes(h.r(d - 8, 40))
run('reference')
for off in list(range(0, 24)):
    if off in (1, 5):
        continue
    for val in (1, 0x30, 0x60):
        if base[8 + off] == val:
            continue
        h.w(d + off, bytes([val]))
        run(f'd+{off}={val:#x}')
