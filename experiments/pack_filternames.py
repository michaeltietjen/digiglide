"""Sound pack groundwork: the FLTR page of demo tracks whose filter byte (+0xDF) is 0, 1, 2, 3, 4."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session
import cfkit
OUT = os.path.expanduser('~/glide/experiments/out/pack')
os.makedirs(OUT, exist_ok=True)
s = Session(None, tag='pack_fnames', solo=False)
k = s.k; h = k.h; h.out = OUT
fb = {t: h.r(k.sound(t) + 0xDF, 1)[0] for t in range(16)}
pick = {}
for t, b in fb.items():
    pick.setdefault(b, t)
print('filter byte -> first track:', pick)
for b, t in sorted(pick.items()):
    h.press(cfkit.KEYS['TRK'], 500_000); h.frames(10)
    h.press(cfkit.TRIG(t + 1), 500_000); h.frames(10); h.release(cfkit.TRIG(t + 1)); h.frames(10)
    h.release(cfkit.KEYS['TRK']); h.frames(10); h.run(40_000_000)
    k.tap('FLTR'); h.frames(10); h.run(40_000_000)
    h.png(f'filter_type_{b}_track{t + 1}.png')
print('done')
