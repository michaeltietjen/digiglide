"""DigiGlide M4b: screenshots of the SYN pages on a DigiGlide track (and a plain WAVETONE track as control)."""
import os, sys, glob
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest, G
OUT = os.path.expanduser('~/glide/experiments/out/m4')
img = sys.argv[1] if len(sys.argv) > 1 else latest()
s = Session(img, tag='m4pages')
k = s.k
k.h.out = OUT
s.set_sound(G.Params(key=2, scl=1, deg=3, chrd=3, vcnt=5, bass=2, sprd=77, move=4, glid=6, path=4, time=2, ordr=3, stag=2, drft=12, vib=6, scrb=100))
k.tap('SYN')
for i in range(6):
    k.h.png(f'b{os.path.basename(img)[-6:-4]}_syn_{i + 1}.png')
    k.tap('SYN')
print('done', sorted(os.listdir(OUT)))
