"""Image 19 on the unit: knob G (PLAY) would not leave CHRD. The knob's value reaches the track through the kit's
edit buffer (FX word k 76) and dg_ui_sync, which put back any value above PTOP, and PTOP[PLAY] was 0. This writes
the buffer word as a knob turn does, syncs, reads PLAY back, saves the CHORD page (header: mode), and plays a trig.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b20_play_knob.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mod', 'tests'))
from dgkit import Session, latest, Ui, U16
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'b20')
os.makedirs(OUT, exist_ok=True)
s = Session(img, tag='b20k', solo=True)
k, h = s.k, s.k.h
h.out = OUT
h.frames(3200)
s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, voic=64), t=0, mach=None, atk=None)
s.trig(0, note=48, length=60, t=0)
k.tap('SYN'); h.frames(2200)
for _ in range(9):
    k.tap('SYN')
    if s.drawn_page() == 4:
        break
print('CHORD on screen', s.drawn_page() == 4)
buf = h.u32(A(0x800052A0)) + 0x48e4 + 2 * (70 + 6)
ok = True
for v, name in [(1, 'strm'), (2, 'stru'), (3, 'harp'), (0, 'chrd')]:
    h.frames(30)
    h.w(buf, bytes([v, 0]))                         # the knob's edit: the buffer word
    h.frames(60)                                    # the UI pass syncs it into the track
    got = k.slot(0, 65) >> 8
    ok &= got == v
    h.png(f'chord_page_{name}.png')
    print(f' PLAY buffer {v} -> track {got}', 'ok' if got == v else 'FAIL')
h.w(buf, bytes([1, 0])); h.frames(60)
fr = s.play(300, bpm=120)
blocks = sorted({b for b, f in enumerate(fr) if U16(f, 0x22)})
print(' STRM note-on blocks', blocks[:6])
ok &= len(blocks) >= 4 and blocks[1] - blocks[0] == 20
h.png('chord_page_strm_playing.png')
print('OK' if ok else 'FAIL')
