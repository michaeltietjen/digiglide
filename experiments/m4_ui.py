"""DigiGlide M4b: turn a knob on HARMONY (KEY -> F), p-lock DEG by holding trig 1 and turning, play: the trig uses it."""
import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest, G, SLOT0
import cfkit
OUT = os.path.expanduser('~/glide/experiments/out/m4')
img = sys.argv[1] if len(sys.argv) > 1 else latest()
s = Session(img, tag='m4ui')
k = s.k; h = k.h
h.out = OUT
s.set_sound(G.Params(key=0, scl=1, deg=0, chrd=1))
s.trig(0, length=127)
print('on HARMONY:', s.syn_page(3))
h.png('ui_0_harmony.png')
slot = lambda n: k.slot(0, SLOT0 + n) >> 8
KEYENC = 0                                   # knob A (encoder 0)
before = slot(0)
print('turn_to KEY 5:', h.turn_to(KEYENC, lambda: slot(0), 5, tries=40), ': KEY', before, '->', slot(0))
h.png('ui_1_key_F.png')
# p-lock DEG (knob C) on step 1: hold the trig, turn
model = k.h.u32(s.ctx0 + 44)
lock = lambda: k.call(0x4003CDBA, [model, 0, 0, SLOT0 + 2])
s.set_sound(G.Params(key=5, scl=1, deg=0, chrd=1))   # DEG back to I in the sound
h.tap(cfkit.RECORD); h.frames(10)                   # GRID RECORDING: holding a trig edits its locks
h.press(cfkit.TRIG(1), 500_000); h.frames(80)       # a held trig registers after ~80 frames
h.turn_to(KEYENC + 2, lambda: (lambda v: -1 if v in (-1, 0xFFFFFFFF) else (v & 0xFFFF) >> 8)(lock()), 5, tries=40)
h.png('ui_2_deg_locked_held.png')
h.release(cfkit.TRIG(1)); h.frames(6)
h.tap(cfkit.RECORD); h.frames(10)
v = lock()
print('lock on step 1, DEG slot:', hex(v & 0xFFFFFFFF), '; sound DEG stays', slot(2))
h.png('ui_3_after_release.png')
steps = k.call(k.h.u32(k.h.u32(s.ctx0) + 40), [s.ctx0])
print('step 1 word after the UI lock:', hex(k.h.u16(steps)))
h.tap(cfkit.STOP); h.frames(40)
fr = s.play(300, bpm=120)
from dgkit import U16
ons = [(i, v, U16(f, 0xA5A + 2 * v)) for i, f in enumerate(fr) for v in range(16) if (U16(f, 0x22) >> v) & 1]
print('note-ons in the playback:', ons[:8], 'play state', hex(k.h.u32(0x42C5A994)), hex(k.h.u32(0x42C5A918)))
d = s.dg(); p = s.cur()
print('trig read: KEY', p.key, 'DEG', p.deg, 'locks', bin(d['locks']), 'trigs', d['trigs'])
