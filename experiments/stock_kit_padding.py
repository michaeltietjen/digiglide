import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session
from osver import A
s = Session(None, tag='pad', solo=False)
k, h = s.k, s.k.h
IMG = 0x405ce96c + 0xae0200
snd = h.u32(A(0x800052A0)); kit = (snd - 0x4210D08C) // 0x5d71
print('kit', kit, 'rem', (snd - 0x4210D08C) % 0x5d71)
for i in (0, 1, kit, 128):
    r = IMG + 0x2a00 * i
    print(i, 'magic %#x ver %d tail %#x pad zero %s' % (h.u32(r), h.u32(r + 4), struct.unpack('>I', bytes(h.r(r + 0x28ab, 4)))[0], not any(h.r(r + 0x28af, 337))))
pat = bytes((7 * i + 1) & 0xFF or 1 for i in range(337))
for i in range(129):
    h.w(IMG + 0x2a00 * i + 0x28af, pat)
def chk(what):
    bad = [i for i in range(129) if bytes(h.r(IMG + 0x2a00 * i + 0x28af, 337)) != pat]
    print(what, 'padding changed in kits', bad, flush=True)
chk('start')
k.tap('SYN'); h.turn(0, 1, 8); h.frames(300); h.run(200_000_000); chk('sound edit')
k.tap('FX') if False else None
s.func_with(1, 1); h.frames(300); h.run(300_000_000); chk('FUNC+YES (save pattern)')
s.func_with(1, 3); h.frames(300); h.run(300_000_000); chk('FUNC+NO (reload pattern)')
k.play(600, bpm=120); chk('play')
