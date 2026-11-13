"""DigiGlide M4b: which stock knob rows draw DigiGlide's values well? Pokes dg_rows (RAM) and screenshots HARMONY."""
import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest, G
OUT = os.path.expanduser('~/glide/experiments/out/m4')
img = sys.argv[1] if len(sys.argv) > 1 else latest()
s = Session(img, tag='m4rows')
k = s.k
k.h.out = OUT
s.set_sound(G.Params(key=2, scl=1, deg=3, chrd=3, vcnt=5, bass=2, sprd=77, move=4))
TRIES = {'a': [76, 38, 73, 82, 62, 37, 62, 76], 'b': [37, 76, 38, 73, 76, 62, 37, 38]}
for tag, rows in TRIES.items():
    k.h.w(s.sym['dg_rows'], b''.join(struct.pack('>I', 0x4243325C + 68 * r) for r in rows + [76] * 8))
    for _ in range(3):                      # to HARMONY (page 4) from wherever: tap until the header changes
        pass
    k.tap('SYN'); k.tap('SYN'); k.tap('SYN'); k.tap('SYN')
    k.h.png(f'rows_{tag}.png')
    k.tap('SYN')                             # back round to the start of the cycle
print('ok')
