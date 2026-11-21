"""Owner, 2026-11-16: one DigiGlide track; "arps on other tracks overwhelmed", "notes stolen from other tracks".
The demo pattern with every track playing, track 1 a DigiGlide track (VCNT as given, HOLD, bass) or OFF. Per other
track: note-ons, and steals = a note-on on a voice whose last note (any track's) has had no note-off yet.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b26_demo_steals.py IMAGE.syx VCNT   (0 = OFF)"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16

img, vc = sys.argv[1], int(sys.argv[2])
n = os.path.basename(img)[:-4].rsplit('_', 1)[-1]
s = Session(img, tag=f'demo_{vc}', solo=False, reserve=0)
s.set_sound(Ui(vcnt=vc or 5, type=1, ext=2, glid=3, hold=1, bass=2, voic=64, drft=0, vib=0), t=0, mach=None, atk=None, on=bool(vc))
for st, note in ((0, 48), (8, 53), (16, 55), (24, 50)):
    s.trig(st, note=note, length=127, t=0)
fr = s.play(12000, bpm=120)
h = s.k.h
d = h.u32(s.sym['DG'] + 80)
res = [h.r(d + 5 * i + 1, 1)[0] for i in range(16)] if d else None
gate = [None] * 16                                       # the track whose note is open on the voice
ons, steals, stolen = [0] * 17, [0] * 17, [0] * 17
for f in fr:
    on, off = U16(f, 0x22), U16(f, 0x24)
    for v in range(16):
        if off >> v & 1:
            gate[v] = None
        if on >> v & 1:
            t = min(U16(f, 0xA5A + 2 * v), 16)
            ons[t] += 1
            if gate[v] is not None:
                steals[t] += 1; stolen[gate[v]] += 1
            gate[v] = t
print(f'[{n}] VCNT {vc}: reserved {res}')
print(f'[{n}] VCNT {vc}: note-ons per track {ons[:16]}')
print(f'[{n}] VCNT {vc}: notes cut off by a later note, per track {stolen[:16]}  (total {sum(stolen)})', flush=True)
