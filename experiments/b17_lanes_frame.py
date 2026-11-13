"""Build 17 measurement 2: do locks on slots no machine uses (0, 65, 100) change what the DSP is sent?"""
import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui
from osver import A
IMG = os.path.expanduser('~/dn2-workspace/build/DN2_1.12_DIGIGLIDE_16.syx')
MACH = int(os.environ.get('DG_MACH', '0'))
def run(slots):
    s = Session(IMG, tag='l17b_%d_%s' % (MACH, '_'.join(map(str, slots)) or 'none'), solo=True, reserve=0)
    s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=0), atk=0, on=False, mach=MACH)
    s.trig(2, note=60, length=14); s.trig(6, note=64, length=14)
    for sl in slots:
        assert s.k.call(A(0x4004F8FE), [s.ctx0, 2, sl, 0x2A00]) & 0xFF
    fr = s.play(1500, bpm=120)
    return [bytes(f) for f in fr]
ref = run(())
print('frames', len(ref), 'frame bytes', len(ref[0]))
for slots in ((0,), (65,), (100,), (70,)):
    got = run(slots)
    d = {}
    for i, (a, b) in enumerate(zip(ref, got)):
        for o in range(0, min(len(a), len(b)), 2):
            if a[o:o + 2] != b[o:o + 2]:
                d.setdefault(o, []).append((i, a[o:o + 2].hex(), b[o:o + 2].hex()))
    print('lock on slot', slots, ': frame words that differ:', {('%#x' % o): (len(v), v[0]) for o, v in sorted(d.items())} or 'none')
