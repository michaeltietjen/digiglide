"""DigiGlide M4: the stock sound converters, called directly. Where is a live sound's name, which pointer does save
0x400dd6a6(stored, live, flags) take, and does save -> load (0x400dd1ea(live, stored)) carry slots 50..64, 93, 94?"""
import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest
import cfkit
s = Session(latest(), tag='soundio', solo=False)
k = s.k; h = k.h
snd0 = k.sound(0)
raw = bytes(h.r(snd0 - 8, 48))
print('sound(0) - 8 .. + 40:', raw.hex(' '))
print('   as text:', ''.join(chr(c) if 32 <= c < 127 else '.' for c in raw))
BUF = cfkit.SPARE + 0x10000
for off in (0, 6):
    h.w(BUF, bytes(0x400))
    for sl, v in ((50, 0x0300), (54, 0x0300), (64, 0x0b00), (93, 0x5a00)):
        k.slot(0, sl, v)
    r = k.call(0x400DD6A6, [BUF, snd0 + off, 0])
    stored = bytes(h.r(BUF, 0x200))
    w = lambda i: struct.unpack_from('>H', stored, 0x1C + 2 * i)[0]
    print(f'save(live = sound + {off}): ret {r & 0xFF}, magic {stored[:4].hex()}, words 58 {w(58):#06x} 62 {w(62):#06x} '
          f'72 {w(72):#06x} 100 {w(100):#06x}')
    if w(62) == 0x0300:
        dst = k.sound(5)
        r2 = k.call(0x400DD1EA, [dst, BUF])
        got = {sl: k.slot(5, sl) for sl in (50, 54, 64, 93)}
        print(f'   load into track 6: ret {r2 & 0xFF}, slots {", ".join(f"{a}={b:#06x}" for a, b in got.items())}, '
              f'machine {k.mach(5)}')
