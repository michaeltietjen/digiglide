"""Grid recording on a DigiGlide track, against stock: [RECORD] tapped (grid recording), three trig keys pressed,
then the steps that hold trigs, the frames' note-ons while placing them, and the bytes of the pattern that changed.
Playback of the result in a fresh session.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python rec_grid.py [stock|IMAGE.syx] [hold]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest, Ui, U16
from osver import A
from emu import panelin

arg = sys.argv[1] if len(sys.argv) > 1 else 'stock'
img = None if arg == 'stock' else arg
hold = len(sys.argv) > 2
tag = ('stock' if not img else 'dg') + ('_h' if hold else '')


def setup(t):
    s = Session(img, tag=t, solo=True, reserve=0)
    if img:
        s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=int(hold)))
        for _ in range(3):
            s.k.tap('SYN')
    else:
        s.k.select(1, track=0)
    return s


s = setup('grid_' + tag)
k, h = s.k, s.k.h
pat = h.u32(A(0x42C5A9A0))
steps = lambda: [st for st in range(64) if h.r(pat + 2 * st + 1, 1)[0] & 1]
before = bytes(h.r(pat, 131072))


def btn(g, m, n=3_000_000, fr=20):
    h.pc = panelin.buttons(h.m, h.profile, g, m); h.run(n); h.frames(fr)


btn(2, 0x04); btn(2, 0x00, fr=200)                       # [RECORD]: grid recording
st0 = len(h.sent)
for mask in (0x01, 0x04, 0x10):
    btn(3, mask, fr=120); btn(3, 0x00, fr=200)
h.frames(700)
ons = [(i, hex(U16(f, 0x22))) for i, (f, _) in enumerate(h.sent[st0:]) if U16(f, 0x22)]
after = bytes(h.r(pat, 131072))
diff = [i for i in range(len(after)) if after[i] != before[i]]
print(tag, 'steps with trigs:', steps())
print(tag, 'note-ons while placing:', ons[:8])
print(tag, 'pattern bytes changed:', [(hex(i), before[i], after[i]) for i in diff[:40]], len(diff))
if img:
    print(tag, 'DigiGlide events', h.u32(s.sym['DG'] + 4), 'name', repr(s.chord_name(0)))
p = setup('gridplay_' + tag)
h2 = p.k.h
h2.w(h2.u32(A(0x42C5A9A0)), after)
fr = p.play(3000, bpm=120)
pb = [(i, [(v, U16(f, 2 + 2 * v) >> 8) for v in range(16) if U16(f, 0x22) >> v & 1]) for i, f in enumerate(fr) if U16(f, 0x22)]
print(tag, 'playback note-ons:', pb[:8])
print(tag, 'playback note-offs:', [(i, hex(U16(f, 0x24))) for i, f in enumerate(fr) if U16(f, 0x24)][:8])
