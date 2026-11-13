"""Live recording over more than one pass of the pattern: keys in pass 1, then the recorded trigs play back in pass 2
(with or without more keys on top). For every note-on block: how long the pitch words move after it and from where.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python rec_glide2.py IMAGE.syx [hold] [keys2]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16
from osver import A
from emu import panelin
import cfkit

img = sys.argv[1]
hold, keys2 = 'hold' in sys.argv, 'keys2' in sys.argv
s = Session(img, tag='recglide2' + ('_h' if hold else '') + ('_k' if keys2 else ''), solo=True, reserve=0)
k, h = s.k, s.k.h
s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=int(hold)))
for _ in range(3):
    k.tap('SYN')
for st in range(128):
    k.call(A(0x40054690), [s.ctx0, st, 1, 0])
pat = h.u32(A(0x42C5A9A0))
k.tap('KEYB')


def btn(g, m, n=3_000_000, fr=20):
    h.pc = panelin.buttons(h.m, h.profile, g, m); h.run(n); h.frames(fr)


h.w(A(0x402A0DEC), cfkit.BE(120 * 120))
btn(2, 0x04); btn(2, 0x0C); btn(2, 0x00)
st0 = len(h.sent)
marks = []
for mask in (0x01, 0x04, 0x10):                         # pass 1: three keys, 4 steps apart
    marks.append((len(h.sent) - st0, 'key'))
    btn(3, mask, fr=375); btn(3, 0x00, fr=375)
h.frames(3000 - (len(h.sent) - st0) % 3000 if (len(h.sent) - st0) < 3000 else 1)
if keys2:                                               # pass 2: two more keys between the recorded trigs
    h.frames(180)
    for mask in (0x02, 0x08):
        marks.append((len(h.sent) - st0, 'key'))
        btn(3, mask, fr=375); btn(3, 0x00, fr=375)
h.frames(3400)
fr = [f for f, _ in h.sent[st0:]]
print('hold', hold, 'keys2', keys2, 'blocks', len(fr), 'events', h.u32(s.sym['DG'] + 4),
      'trig steps', [x for x in range(64) if h.r(pat + 2 * x + 1, 1)[0] & 1], 'key blocks', marks)
P = lambda f: tuple(U16(f, 2 + 2 * v) for v in range(8))
ons = [i for i, f in enumerate(fr) if U16(f, 0x22)]
chg = [i for i in range(1, len(fr)) if P(fr[i]) != P(fr[i - 1])]
ev = sorted(set(ons) | {i for i in chg if i - 1 not in chg})
for i in ev:
    j = i
    while j + 1 in set(chg) or (j + 1 < len(fr) and P(fr[j + 1]) != P(fr[j])):
        j += 1
    a, b = P(fr[i - 1]) if i else P(fr[0]), P(fr[min(j, len(fr) - 1)])
    print(f' block {i:5d}: note-on {U16(fr[i], 0x22):04x} off {U16(fr[i], 0x24):04x}  moves {j - i:4d} blocks  '
          + ' '.join(f'{x / 256:.1f}>{y / 256:.1f}' for x, y in zip(a[:5], b[:5])), flush=True)
