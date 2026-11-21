"""Build 23 groundwork: can sound slot 65 hold a third DigiGlide lock lane? A lock on slot 65 lands in the voice's
record (frame +0xDA + 146 v + 80); no machine has a record for it. Renders the same frames through the SHARC
emulator with that word as the run left it and forced to several values, on each machine, and compares the audio.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b23_slot65.py IMAGE.syx"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, Ui
import dn2paths as P, dn2frame as D

img = sys.argv[1]
sec7, snap = P.snap('stock')
for mach in (0, 1, 2, 3):
    s = Session(img, tag=f'b23s65_{mach}', solo=True)
    s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, voic=64), t=0, mach=mach, atk=None)
    for st, n in [(0, 48), (4, 53), (8, 55), (12, 50)]:
        s.trig(st, note=n, length=60, t=0)
    fr = [bytes(f) for f in s.play(2000, bpm=120)[:2000]]
    base = set(int.from_bytes(f[0xDA + 146 * v + 80:0xDA + 146 * v + 82], 'big') for f in fr for v in range(16))
    def render(val):
        g = []
        for f in fr:
            f = bytearray(f)
            if val is not None:
                for v in range(16):
                    o = 0xDA + 146 * v + 80
                    f[o:o + 2] = val.to_bytes(2, 'big')
            g.append(D.swap16(bytes(f)))
        L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), g)
        return np.asarray(L, float) + np.asarray(R, float)
    ref = render(None)
    out = []
    for val in (0, 0x2A00, 0x7FFF, 0x4C1B):
        x = render(val)
        out.append(f'{val:#06x}: max diff {np.max(np.abs(x - ref)):.3g}')
    print(f'machine {mach}: word values seen {sorted(base)[:6]}  rms {np.sqrt(np.mean(ref**2)):.3g}  ' + '  '.join(out), flush=True)
