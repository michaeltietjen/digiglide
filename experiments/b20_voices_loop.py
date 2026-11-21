"""Owner, image 19: "VOICES SET TO 6" every loop of pattern 2 (pattern 2 has its own kit). Count calls of the voice
setter 0x40029094 and track 1's reserved voices across 4 loops of a 1-bar pattern, VCNT 6.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b20_voices_loop.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mod', 'tests'))
from dgkit import Session, latest, Ui
from osver import A
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import UC_M68K_REG_D0

img = sys.argv[1] if len(sys.argv) > 1 else latest()
s = Session(img, tag='b20v', solo=True, reserve=2)
k, h = s.k, s.k.h
h.frames(3200)
s.set_sound(Ui(vcnt=6, type=1, ext=2), t=0, mach=None, atk=None)
s.trig(0, note=48, length=14, t=0)
s.trig(8, note=50, length=14, t=0)
calls = []
blk = [0]
def on_set(uc, a, sz, u):
    sp = uc.reg_read(__import__('unicorn').m68k_const.UC_M68K_REG_A7)
    t, n = h.u32(sp + 8), h.u32(sp + 12)
    calls.append((blk[0], t, n))
h.uc.hook_add(UC_HOOK_CODE, on_set, begin=A(0x40029094), end=A(0x40029094))
h.uc.ctl_flush_tb()
def each(b):
    blk[0] = b
fr = s.play(3000 * 4 + 200, bpm=120, each=each) if 'each' in s.play.__code__.co_varnames else s.play(12200, bpm=120)
print('voice-set calls (block, track, n):', calls[:20], 'total', len(calls))
