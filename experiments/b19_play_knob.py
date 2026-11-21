"""Build 19 on the unit: "STRM / HARP do nothing". Turn knob G on the CHORD page through the emulated panel (as the
owner does) and read PLAY back from the track's store after each turn, then play a trig and count note-on blocks.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b19_play_knob.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mod', 'tests'))
from dgkit import Session, latest, Ui, U16

img = sys.argv[1] if len(sys.argv) > 1 else latest()
s = Session(img, tag='b19k', solo=True)
k, h = s.k, s.k.h
h.frames(3200)
s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, voic=64), t=0, mach=None, atk=None)
s.trig(0, note=48, length=60, t=0)
k.tap('SYN'); h.frames(2200)
for _ in range(9):
    k.tap('SYN')
    if s.drawn_page() == 4:
        break
print('CHORD on screen', s.drawn_page() == 4)
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import UC_M68K_REG_D0
h.uc.hook_add(UC_HOOK_CODE, lambda uc, a, sz, u: uc.reg_write(UC_M68K_REG_D0, 0x100), begin=0x400675c8, end=0x400675c8)
h.uc.ctl_flush_tb()
print('PLAY before', hex(k.slot(0, 65)))
for kn, sl in [(0, 50), (4, 55), (5, 93), (6, 65), (7, 94)]:
    for i in range(2):
        h.turn(kn, 1, 1, hold=False); h.frames(30); h.run(150_000_000); h.frames(20)
    print(" knob", kn, "slot", sl, hex(k.slot(0, sl)))
for i in range(0):
    h.turn(6, 1, 1, hold=False); h.frames(30); h.run(150_000_000); h.frames(20)
    print(' turn', i + 1, 'PLAY', hex(k.slot(0, 65)))
fr = s.play(400, bpm=120)
blocks = sorted({b for b, f in enumerate(fr) if U16(f, 0x22)})
print('note-on blocks', blocks[:10])
