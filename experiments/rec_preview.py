"""Grid recording, a trig key held: stock plays a preview note (dnfw emu-sequencer-play.md). What does DigiGlide make
of it, HOLD off and on? [RECORD] tapped, one trig key held ~2 s then released, then a wait; prints the frames'
note-on and note-off blocks (voice masks), and for DigiGlide the chord state after.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python rec_preview.py [stock|IMAGE.syx] [hold]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16
from osver import A
from emu import panelin

arg = sys.argv[1] if len(sys.argv) > 1 else 'stock'
img = None if arg == 'stock' else arg
hold = len(sys.argv) > 2
tag = ('stock' if not img else 'dg') + ('_h' if hold else '')
s = Session(img, tag='prev_' + tag, solo=True, reserve=0)
k, h = s.k, s.k.h
if img:
    s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=int(hold)))
    for _ in range(3):
        k.tap('SYN')
else:
    k.select(1, track=0)
pat = h.u32(A(0x42C5A9A0))


def btn(g, m, n=3_000_000, fr=20):
    h.pc = panelin.buttons(h.m, h.profile, g, m); h.run(n); h.frames(fr)


def ev(st):
    return ([(i, hex(U16(f, 0x22))) for i, (f, _) in enumerate(h.sent[st:]) if U16(f, 0x22)][:6],
            [(i, hex(U16(f, 0x24))) for i, (f, _) in enumerate(h.sent[st:]) if U16(f, 0x24)][:6])


btn(2, 0x04); btn(2, 0x00, fr=200)                       # [RECORD]: grid recording
for n, mask in enumerate((0x04, 0x04)):                  # first hold places the trig, second hold is on an existing trig
    st = len(h.sent)
    btn(3, mask, fr=3000)
    print(tag, f'hold {n + 1}: while held  on/off', *ev(st), flush=True)
    st = len(h.sent)
    btn(3, 0x00, fr=1500)
    print(tag, f'hold {n + 1}: after release on/off', *ev(st),
          'trigs', [x for x in range(64) if h.r(pat + 2 * x + 1, 1)[0] & 1], flush=True)
    if img:
        print(tag, '   DigiGlide events', h.u32(s.sym['DG'] + 4), 'name', repr(s.chord_name(0)), flush=True)
