"""Do chord changes glide while live recording? Three keys in keyboard mode about a beat apart, with and without
[RECORD] + [PLAY]; per key, how many blocks the voices' pitch words keep moving after the key (a glide), and how far.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python rec_glide.py IMAGE.syx rec|play|stop [hold]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16
from osver import A
from emu import panelin
import cfkit

img, mode = sys.argv[1], sys.argv[2]
hold = len(sys.argv) > 3
s = Session(img, tag='recglide_' + mode + ('_h' if hold else ''), solo=True, reserve=0)
k, h = s.k, s.k.h
s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=int(hold)))
for _ in range(3):
    k.tap('SYN')
for st in range(128):
    k.call(A(0x40054690), [s.ctx0, st, 1, 0])
k.tap('KEYB')


def btn(g, m, n=3_000_000, fr=20):
    h.pc = panelin.buttons(h.m, h.profile, g, m); h.run(n); h.frames(fr)


h.w(A(0x402A0DEC), cfkit.BE(120 * 120))
if mode == 'rec':
    btn(2, 0x04); btn(2, 0x0C); btn(2, 0x00)
elif mode == 'play':
    btn(2, 0x08); btn(2, 0x00)
print(mode, 'hold', hold, 'playing', h.u32(A(0x42C5A994)))
for n, mask in enumerate((0x01, 0x04, 0x10)):
    st = len(h.sent)
    btn(3, mask, fr=375); btn(3, 0x00, fr=375)
    fr = [f for f, _ in h.sent[st:]]
    ons = [i for i, f in enumerate(fr) if U16(f, 0x22)]
    vs = [v for v in range(16) if any(U16(f, 0x22) >> v & 1 for f in fr)] or list(range(8))
    moving = [i for i in range(1, len(fr)) if any(U16(fr[i], 2 + 2 * v) != U16(fr[i - 1], 2 + 2 * v) for v in range(16))]
    span = {v: (min(U16(f, 2 + 2 * v) for f in fr), max(U16(f, 2 + 2 * v) for f in fr)) for v in vs}
    print(f' key {n}: {len(fr)} blocks, note-on blocks {ons[:4]}, pitch moving in {len(moving)} blocks (first {moving[:1]}, last {moving[-1:]}),',
          'spans', {v: f'{a / 256:.2f}..{b / 256:.2f}' for v, (a, b) in span.items()}, 'name', s.chord_name(0), flush=True)
print('events', h.u32(s.sym['DG'] + 4))
