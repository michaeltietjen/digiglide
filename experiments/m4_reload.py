"""Does [FUNC] + [YES] then [FUNC] + [NO] (stock's pattern save / reload) bring back a sound value? Stock's amp VOL
(slot 90) and DigiGlide's VCNT (slot 54), both changed after the save."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest
img = sys.argv[1] if len(sys.argv) > 1 else latest()
s = Session(img if img != 'stock' else None, tag='reload', solo=False)
k = s.k; h = k.h
k.slot(0, 54, 0x200); k.slot(0, 90, 0x5000)
print('before save: VCNT', hex(k.slot(0, 54)), 'VOL', hex(k.slot(0, 90)))
s.func_with(1, 1)                                   # FUNC + YES
k.slot(0, 54, 0x0000); k.slot(0, 90, 0x2000)
print('changed:     VCNT', hex(k.slot(0, 54)), 'VOL', hex(k.slot(0, 90)))
s.func_with(1, 3)                                   # FUNC + NO
h.run(200_000_000); h.frames(20)
print('reloaded:    VCNT', hex(k.slot(0, 54)), 'VOL', hex(k.slot(0, 90)))
k.h.out = os.path.expanduser('~/glide/experiments/out/m4'); k.h.png('reload_after.png')
