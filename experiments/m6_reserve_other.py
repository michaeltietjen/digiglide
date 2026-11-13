"""Which DSP voices does a track get when it reserves voices and it is not track 1?
Stock OS (no DigiGlide): track 5 reserves 6 (VOICE setter 0x40029094), track 9 reserves 4, tracks 1 and 5 and 9 play
8 short notes each; the demo's other tracks play too. Prints the voices each track's note-ons used and the idle
voice -> track words (+0xa5a) before play.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python m6_reserve_other.py"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, U16
from osver import A

s = Session(None, tag='m6_resv', solo=False, reserve=0)
k = s.k
cfg = k.call(A(0x40030AF8), [k.call(A(0x4003E41A), [s.app])])
for t, n in ((4, 6), (8, 4)):
    k.call(A(0x40029094), [cfg, t, n])
for t in (0, 4, 8):
    for st in range(128):
        k.call(A(0x40054690), [s.ctx0 + 132 * t, st, 1, 0])
    for i in range(8):
        s.trig(2 * i, note=60 + i, length=1, t=t)
fr = s.play(3200, bpm=120)
print('idle voice -> track words in frame 0:', [U16(fr[0], 0xA5A + 2 * v) for v in range(16)])
used = {}
for f in fr:
    on = U16(f, 0x22)
    for v in range(16):
        if on >> v & 1:
            used.setdefault(U16(f, 0xA5A + 2 * v) + 1, set()).add(v)
for t in sorted(used):
    print(f'track {t:2d} played on voices {sorted(used[t])}')
