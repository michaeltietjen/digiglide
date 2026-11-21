"""'bass is quiet' (image 23 on the unit). The bass voice alone (every other voice's level word zeroed in the frame)
through the SHARC emulator: BPAT HOLD against the patterns, the chord's top voice alone for reference, at AMP ATK
0 and ATKF (set straight into every voice record). Prints RMS and peak dB over 2 bars.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b23_bass_level.py IMAGE.syx [ATK ...]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, U16, Ui
import dn2paths as P, dn2frame as D

img = sys.argv[1]
atks = [int(a) for a in sys.argv[2:]] or [0, 30]
BV = 4
sec7, snap = P.snap('stock')


def frames(bpat):
    s = Session(img, tag=f'b23lv{bpat}', solo=True)
    s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, voic=64, bass=3, hold=1), t=0, mach=None, atk=None)
    s.k.call(s.sym['dg_par_set'], [0, 19, bpat << 8])
    s.trig(0, note=48, length=30, t=0)
    return s.play(3400, bpm=120)[:3200]


def render(fr, keep, atk):
    out = []
    for f in fr:
        f = bytearray(f)
        for v in range(16):
            if v != keep:
                f[0x74 + 2 * v:0x76 + 2 * v] = b'\0\0'
            a = 0xDA + 146 * v + 2 * (81 - 25)
            f[a:a + 2] = (atk << 8).to_bytes(2, 'big')
        out.append(D.swap16(bytes(f)))
    L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), out)
    x = (np.asarray(L, float) + np.asarray(R, float)) / 2
    x = x[len(x) * 300 // len(fr):]                     # (after the first strike's attack)
    return 20 * np.log10(max(np.sqrt(np.mean(x ** 2)), 1e-9)), 20 * np.log10(max(np.max(np.abs(x)), 1e-9))


fr = {bp: frames(bp) for bp in (0, 1, 2, 3)}
top = max(range(4), key=lambda v: U16(fr[0][500], 2 + 2 * v))
for atk in atks:
    print(f'ATK {atk}')
    r, p = render(fr[0], top, atk)
    print(f'  chord top voice {top}   rms {r:6.1f}  peak {p:6.1f}')
    for bp, name in ((0, 'HOLD'), (1, 'PULS'), (2, 'OCT'), (3, 'WALK')):
        r, p = render(fr[bp], BV, atk)
        print(f'  bass {name}          rms {r:6.1f}  peak {p:6.1f}')
