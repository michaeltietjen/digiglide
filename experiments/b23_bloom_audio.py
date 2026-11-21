"""Build 23: BLOOM through the SHARC emulator. A held C MIN7 chord (HOLD on, 4 voices, BASS OFF), BLOOM from argv
(64 = off). Prints the level in 200 ms windows, each voice's level word over time, and the largest jump between
neighbouring samples relative to the signal (a click shows as a spike)."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, Ui, U16
import dn2paths as P, dn2frame as D

img, bloom = sys.argv[1], int(sys.argv[2])
N = int(os.environ.get('BLOCKS', 6000))
s = Session(img, tag=f'b23bl_{bloom}', solo=True)
s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, voic=64, bass=0, hold=1), t=0, mach=None, atk=None)
s.k.call(s.sym['dg_par_set'], [0, 21, bloom << 8])
s.trig(0, note=48, length=30, t=0)
fr = [bytes(f) for f in s.play(N, bpm=120)[:N]]
lv = np.array([[U16(f, 0x74 + 2 * v) for v in range(4)] for f in fr])
sec7, snap = P.snap('stock')
L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), [D.swap16(f) for f in fr])
x = (np.asarray(L, float) + np.asarray(R, float)) / 2
spb = len(x) // len(fr)
w = 300 * spb
print(f'BLOOM {bloom - 64:+d}  rms per 200 ms:', ' '.join(f'{20*np.log10(max(np.sqrt(np.mean(x[i:i+w]**2)),1e-9)):.1f}' for i in range(0, len(x) - w, w)))
for b in range(0, N, 600):
    print(f'  block {b:5d} level words', list(lv[b]))
dx = np.abs(np.diff(x[3000 * spb:]))
print('  max step / rms %.2f' % (dx.max() / np.sqrt(np.mean(x[3000 * spb:] ** 2))))
