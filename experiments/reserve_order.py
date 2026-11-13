"""Which DSP voices does a reserved track get when the reservations are not made in track order, or when an earlier
track's reservation is removed afterwards? Stock OS. DigiGlide assumes: blocks packed from voice 0 in track order.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python reserve_order.py"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, U16
from osver import A

CASES = {'9 then 5': ((8, 4), (4, 6)),
         '1,2,3 then 12, then 1,2,3 freed': ((0, 4), (1, 4), (2, 4), (11, 4), (0, 0), (1, 0), (2, 0)),
         '12 only': ((11, 4),)}
for name, seq in CASES.items():
    s = Session(None, tag='resord%d' % len(seq), solo=True, reserve=0)
    k = s.k
    cfg = k.call(A(0x40030AF8), [k.call(A(0x4003E41A), [s.app])])
    for t, n in seq:
        k.call(A(0x40029094), [cfg, t, n])
    d = k.call(k.h.u32(k.h.u32(cfg) + 40), [cfg])
    tracks = sorted({t for t, _ in seq} | {6, 13})
    for t in tracks:
        for i in range(8):
            s.trig(2 * i + 1, note=60 + i, length=1, t=t)
    used = {}
    for f in s.play(3200, bpm=120):
        on = U16(f, 0x22)
        for v in range(16):
            if on >> v & 1:
                used.setdefault(U16(f, 0xA5A + 2 * v), set()).add(v)
    print('CASE', name, 'VOICES', [k.h.r(d + 5 * t + 1, 1)[0] for t in range(16)], 'rows', [bytes(k.h.r(d + 5 * t, 5)).hex() for t in tracks])
    for t in tracks:
        print(f'CASE   track {t + 1:2d} note-ons on voices {sorted(used.get(t, []))}')
