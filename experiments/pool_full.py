"""The unit's state on build 7: tracks before the DigiGlide track hold 12 reserved voices, the DigiGlide track (13)
takes the last 4. Do tracks with no reserved voices still sound, and does DigiGlide play on voices 12..15?
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python pool_full.py IMAGE.syx"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, U16, Ui, latest
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
for others in (((0, 4), (1, 4), (2, 4), (12, 4)), ((0, 4), (1, 4), (2, 4), (12, 4), (5, 0))):
    s = Session(img, tag='pool%d' % len(others), solo=True, reserve=0)
    k = s.k
    cfg = k.call(A(0x40030AF8), [k.call(A(0x4003E41A), [s.app])])
    for t, n in others:
        k.call(A(0x40029094), [cfg, t, n])
    s.set_sound(Ui(vcnt=4, glid=3, drft=0, vib=0), t=12)
    k.h.frames(200)
    for t in (0, 5, 12, 13):
        for i in range(4):
            s.trig(4 * i + (t % 4), note=60 + i, length=2, t=t)
    names = []
    fr = s.play(3200, bpm=120, each=lambda i: names.append(bytes(k.h.r(s.sym['dg_name'], 16)).split(b'\0')[0].decode()))
    used = {}
    for f in fr:
        on = U16(f, 0x22)
        for v in range(16):
            if on >> v & 1:
                used.setdefault(U16(f, 0xA5A + 2 * v) + 1, set()).add(v)
    print('reserved (track0, n):', others, ' dg events/taken:', s.dg() if 0 else '')
    print('  chord names seen:', sorted(set(names)))
    for t in (1, 6, 13, 14):
        print(f'  track {t:2d} note-ons on voices {sorted(used.get(t, []))}')
