"""Owner, 2026-11-16 (video): the same pattern is complete with DigiGlide off and loses bass and rhythm with it on.
The unit's layout: DigiGlide on track 13 (VCNT 6, HOLD on), three drum tracks, one bass. Per other track: note-ons
that reach the DSP, the voices they land on, and cuts = a note-on on a voice whose last note (another's) is still
open (no note-off yet). REL = AMP release of the other tracks (slot 85, 0..127).
    DG_OS=1.12 python b28_dropouts.py IMAGE.syx VCNT REL [DGTRACK]   (VCNT 0 = OFF)"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16

img, vc, rel = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
dgt = int(sys.argv[4]) if len(sys.argv) > 4 else 12
s = Session(img, tag=f'drop_{vc}_{rel}_{dgt}', solo=True, reserve=0)
s.set_sound(Ui(vcnt=vc or 6, type=1, ext=0, glid=3, hold=1, bass=0, voic=64, drft=0, vib=0), t=dgt, mach=None, atk=None, on=bool(vc))
for st, note in ((0, 48), (8, 53), (16, 55), (24, 50)):
    s.trig(st, note=note, length=127, t=dgt)
OTH = (0, 1, 2, 3)
for t in OTH:
    s.k.sound_slot(t, 85, rel << 8)
for st in range(0, 32, 4):  s.trig(st, note=36, length=2, t=0)          # kick
for st in range(4, 32, 8):  s.trig(st, note=38, length=2, t=1)          # snare
for st in range(0, 32, 1):  s.trig(st, note=42, length=1, t=2)          # hats, 16ths
for st in range(0, 32, 2):  s.trig(st, note=36 + st % 12, length=6, t=3)  # bass, overlapping 8ths
fr = s.play(12000, bpm=120)
h = s.k.h
d = h.u32(s.sym['DG'] + 80)
res = [h.r(d + 5 * i + 1, 1)[0] for i in range(16)] if d else None
gate = [None] * 16
ons, cut, cutby = [0] * 17, [0] * 17, {}
vo = {}
for f in fr:
    on, off = U16(f, 0x22), U16(f, 0x24)
    for v in range(16):
        if off >> v & 1:
            gate[v] = None
        if on >> v & 1:
            t = min(U16(f, 0xA5A + 2 * v), 16)
            ons[t] += 1
            vo.setdefault(t, set()).add(v)
            if gate[v] is not None and gate[v] != t:
                cut[gate[v]] += 1; cutby[(gate[v], t)] = cutby.get((gate[v], t), 0) + 1
            gate[v] = t
n = os.path.basename(img)[:-4].rsplit('_', 1)[-1]
tag = f'[{n}] DG track {dgt + 1} VCNT {vc} REL {rel}'
print(f'{tag}: reserved {res}')
print(f'{tag}: note-ons  kick {ons[0]} snare {ons[1]} hats {ons[2]} bass {ons[3]}  DG track {ons[dgt]}')
print(f'{tag}: voices used ' + ', '.join(f'{t + 1}: {sorted(vo.get(t, []))}' for t in OTH + (dgt,)))
print(f'{tag}: notes cut by another track  kick {cut[0]} snare {cut[1]} hats {cut[2]} bass {cut[3]}   {cutby}', flush=True)
