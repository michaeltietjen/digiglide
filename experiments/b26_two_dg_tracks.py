"""Owner, 2026-11-16: "odd behaviors on glide", "arps on other tracks overwhelmed", "notes stolen from other tracks".
Tried: two DigiGlide tracks at once (the spec: one plays at a time). Track 1 a drone (HOLD, one long trig), track 2
chords (a trig every 8 steps), track 3 a stock arp. Per track: note-ons / note-offs and the voices; DG.track over time.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b26_two_dg_tracks.py IMAGE.syx [1|2]   (DigiGlide tracks)"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16

img = sys.argv[1]
ndg = int(sys.argv[2]) if len(sys.argv) > 2 else 2
s = Session(img, tag=f'two_{ndg}', solo=True, reserve=0)
s.set_sound(Ui(vcnt=5, type=4, ext=0, hold=1, glid=6, time=5, bass=2, voic=64, drft=0, vib=0), t=0, mach=None, atk=None)
s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, hold=0, voic=64, drft=0, vib=0), t=1, mach=None, atk=None, on=ndg > 1)
s.trig(0, note=48, length=127, t=0)
for st, n in ((0, 60), (8, 65), (16, 67), (24, 62)):
    s.trig(st, note=n, length=60, t=1)
s.trig(0, note=72, length=127, t=2)
h = s.k.h
snd = s.k.sound(2)
h.uc.mem_write(snd + 351, bytes([2])); h.uc.mem_write(snd + 374, bytes([2]))
dg = s.sym['DG']
d = h.u32(dg + 80)
log = []
fr = s.play(8000, bpm=120, each=lambda *a: log.append((h.u32(dg + 48), h.u32(dg + 56), h.u32(dg + 4))))
d = h.u32(dg + 80)
print('reserved voices per track', [h.r(d + 5 * i + 1, 1)[0] for i in range(16)] if d else None)
own = lambda f, v: U16(f, 0xA5A + 2 * v)
for t in (0, 1, 2):
    ons = [(i, v) for i, f in enumerate(fr) for v in range(16) if U16(f, 0x22) >> v & 1 and own(f, v) == t]
    offs = [(i, v) for i, f in enumerate(fr) for v in range(16) if U16(f, 0x24) >> v & 1 and own(f, v) == t]
    print(f'track {t + 1}: {len(ons):3d} note-ons on voices {sorted({v for _, v in ons})}, {len(offs):3d} note-offs; '
          f'on at {sorted({i for i, _ in ons})[:10]}; off at {sorted({i for i, _ in offs})[:10]}', flush=True)
ch = [(i, a[0] if a[0] < 16 else -1, hex(a[1])) for i, a in enumerate(log) if i == 0 or (a[0], a[1]) != (log[i - 1][0], log[i - 1][1])]
print('DG.track / ctl changes (call, track, voices driven):', ch[:24])
print('DigiGlide trigs', log[-1][2] if log else None)
