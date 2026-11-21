"""BAL (build 24): the bass voice alone against the chord's voices together, through the SHARC emulator. 5 voices,
BASS FOL, HOLD on, C MIN7, BPAT PULS 1/8, 120 BPM; RMS dB after the first strike.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b24_bal_audio.py IMAGE.syx [BAL knob ...]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, Ui
import dn2paths as P, dn2frame as D

img = sys.argv[1]
bals = [int(a) for a in sys.argv[2:]] or [64, 96, 127]
BV = 4
sec7, snap = P.snap('stock')


def rms(fr, keep):
    out = []
    for f in fr:
        f = bytearray(f)
        for v in range(16):
            if v not in keep:
                f[0x74 + 2 * v:0x76 + 2 * v] = b'\0\0'
        out.append(D.swap16(bytes(f)))
    L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), out)
    x = (np.asarray(L, float) + np.asarray(R, float)) / 2
    x = x[len(x) * 300 // len(fr):]
    return 20 * np.log10(max(np.sqrt(np.mean(x ** 2)), 1e-9))


for bal in bals:
    s = Session(img, tag=f'b24a{bal}', solo=True)
    s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, voic=64, bass=3, hold=1), t=0, mach=None, atk=None)
    s.k.call(s.sym['dg_par_set'], [0, 19, 1 << 8])
    s.k.call(s.sym['dg_par_set'], [0, 23, bal << 8])
    s.trig(0, note=48, length=30, t=0)
    fr = s.play(3200, bpm=120)
    c, b = rms(fr, {0, 1, 2, 3}), rms(fr, {BV})
    print(f'BAL {bal - 64:+3d}: chord {c:6.1f} dB  bass {b:6.1f} dB  bass - chord {b - c:+5.1f} dB', flush=True)
