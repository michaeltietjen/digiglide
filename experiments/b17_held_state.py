"""Build 17 measurement 4: where stock keeps "grid recording is on" and "this step's trig key is held"."""
import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui
import cfkit
from osver import A
IMG = os.path.expanduser('~/dn2-workspace/build/DN2_1.12_DIGIGLIDE_16.syx')
s = Session(IMG, tag='held17', solo=True, reserve=0)
k = s.k; h = k.h
h.out = '/private/tmp/claude-503/-Users-mikem1-Downloads/54f10118-8f03-4039-bd92-53c6b1b3953b/scratchpad'
h.frames(3200)
T = 1
print('track 2 selected', s.select_track(T))
s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3), t=T, mach=None, atk=None)
s.trig(0, note=60, length=14, t=T); s.trig(4, note=62, length=14, t=T)
import numpy as np
LO, HI = 0x40300000, 0x44700000
def snap(): return np.frombuffer(bytes(h.uc.mem_read(LO, HI - LO)), dtype=np.uint8)
def settle(): h.frames(60); h.run(200_000_000)
settle(); a0 = snap(); settle(); a0b = snap()
h.press(cfkit.RECORD, 500_000); h.frames(20); h.release(cfkit.RECORD); settle(); g = snap(); settle(); gb = snap()
h.png('held17_grid.png')
h.press(cfkit.TRIG(1), 500_000); h.frames(80); h.run(100_000_000); t1 = snap(); h.png('held17_t1.png')
h.release(cfkit.TRIG(1)); settle(); g2 = snap()
h.press(cfkit.TRIG(5), 500_000); h.frames(80); h.run(100_000_000); t5 = snap()
h.release(cfkit.TRIG(5)); settle(); g3 = snap()
h.press(cfkit.RECORD, 500_000); h.frames(20); h.release(cfkit.RECORD); settle(); a1 = snap()
quiet = (a0 == a0b) & (g == gb)
rec = np.nonzero(quiet & (a0 == a1) & (a0 != g) & (g == g2) & (g == g3))[0]
print('grid recording candidates', len(rec), [(hex(LO + int(i)), int(a0[i]), int(g[i])) for i in rec[:40]])
held = np.nonzero(quiet & (g == g2) & (g == g3) & ((t1 != g) | (t5 != g)))[0]
print('held candidates', len(held), [(hex(LO + int(i)), int(g[i]), int(t1[i]), int(t5[i])) for i in held[:80]])
pat = h.u32(A(0x42C5A9A0)); print('pattern', hex(pat), 'step words 0..5', bytes(h.r(pat + 4, 12)).hex())
