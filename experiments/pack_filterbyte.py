"""Sound pack groundwork: where does a sound keep its filter machine? Bytes around the machine byte (+0xDE) for the
demo's 16 sounds, and what the stock filter readers report."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session
s = Session(None, tag='pack_fbyte', solo=False)
k = s.k
for t in range(16):
    snd = k.sound(t)
    b = bytes(k.h.r(snd + 0xD8, 16))
    name = bytes(k.h.r(snd + 4, 16)).split(b'\0')[0].decode('latin1')
    print(f'track {t + 1:2d} {name:16s} +D8..E7:', b.hex(' '), ' slot66', hex(k.slot(t, 66)), 'slot67', hex(k.slot(t, 67)))
