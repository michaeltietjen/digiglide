"""Audio-ISR cost (emulator instructions per ISR) for the owner's layout: DigiGlide on track 13, drums and bass on
tracks 1..4. VCNT 0 = OFF on the same image. Prints mean / p99 / max and the 8 dearest ISRs.
    DG_OS=1.12 python b28_isr.py IMAGE.syx VCNT [glid] [play] [key=val ...]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
import numpy as np
from dgkit import Session, Ui, U16

img, vc = sys.argv[1], int(sys.argv[2])
kw = dict(a.split('=') for a in sys.argv[3:])
kw = {k: int(v) for k, v in kw.items()}
dgt = 12
s = Session(img, tag=f'isr_{vc}_' + '_'.join(f'{k}{v}' for k, v in kw.items()), solo=True, reserve=0)
u = dict(vcnt=vc or 6, type=1, ext=0, glid=3, hold=1, bass=0, voic=64, drft=8, vib=4); u.update({k: v for k, v in kw.items() if k != 'prof'})
s.set_sound(Ui(**u), t=dgt, mach=None, atk=None, on=bool(vc))
for st, note in ((0, 48), (8, 53), (16, 55), (24, 50)):
    s.trig(st, note=note, length=127, t=dgt)
for st in range(0, 32, 4):  s.trig(st, note=36, length=2, t=0)
for st in range(4, 32, 8):  s.trig(st, note=38, length=2, t=1)
for st in range(0, 32, 1):  s.trig(st, note=42, length=1, t=2)
for st in range(0, 32, 2):  s.trig(st, note=36 + st % 12, length=6, t=3)
fe = s.k.h.fastemu
orig = fe.run_isr
counts = []
def wrap(*a, **k2):
    n, ok = orig(*a, **k2)
    counts.append(n)
    return n, ok
fe.run_isr = wrap
prof = kw.pop('prof', 0)
PROF_AT = 2500
def each(i):
    if prof and i == PROF_AT: s.k.h.w(s.sym['dg_prof'], prof.to_bytes(4, 'big'))
fr = s.play(4500, bpm=120, each=each)
fe.run_isr = orig
c = np.array(counts[-len(fr):])
if prof: c = c[PROF_AT + 50:]
c0 = c; c = c[c > 30000]
n = os.path.basename(img)[:-4].rsplit('_', 1)[-1]
top = np.argsort(c)[::-1][:8]
print(f'[{n}] VCNT {vc} {kw}: ISRs {len(c)}  mean {c.mean():.0f}  p50 {np.median(c):.0f}  p99 {np.percentile(c, 99):.0f}  max {c.max()}')
print(f'[{n}] VCNT {vc} {kw}: dearest ' + ', '.join(f'{i}:{c[i]}' for i in top))
print(f'[{n}] VCNT {vc} {kw}: ISRs over 60k {int((c > 60000).sum())}, over 80k {int((c > 80000).sum())}, over 120k {int((c > 120000).sum())}', flush=True)
np.save(os.path.expanduser(f'~/glide/experiments/out/isr_{n}_{vc}_' + '_'.join(f'{k}{v}' for k, v in kw.items()) + '.npy'), c)
