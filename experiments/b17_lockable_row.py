"""Build 17 measurement 3: rows left lockable (image 95). GRID RECORDING, hold trig 1, turn knob E (POS) on CHORD.
What does stock call, with what, and what is left in the lock table and the edit buffer?"""
import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
from dgkit import Session, Ui
import cfkit
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import UC_M68K_REG_A7
from osver import A
IMG = os.path.expanduser('~/dn2-workspace/build/proto/DN2_1.12_DIGIGLIDE_95.syx')
s = Session(IMG, tag='lock17c', solo=True, reserve=0)
k = s.k; h = k.h
h.frames(3200)
T = 1
print('track 2 selected', s.select_track(T), 'mach', k.mach(T))
s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3), t=T, mach=None, atk=None)
s.trig(0, note=60, length=14, t=T)
h.out = '/private/tmp/claude-503/-Users-mikem1-Downloads/54f10118-8f03-4039-bd92-53c6b1b3953b/scratchpad'
k.tap('SYN'); h.frames(2200)
seen = []
for _ in range(8):
    k.tap('SYN'); seen.append(s.drawn_page())
    h.png('lock17c_p%d.png' % len(seen))
    if seen[-1] == 4: break
print('pages drawn', seen)
pat = h.u32(A(0x42C5A9A0)); lt = pat + 97872
calls = []
SET = A(0x4004F8FE)
def hook(uc, addr, size, user):
    sp = uc.reg_read(UC_M68K_REG_A7)
    w = struct.unpack('>8I', bytes(uc.mem_read(sp, 32)))
    calls.append(w)
h.uc.hook_add(UC_HOOK_CODE, hook, begin=SET, end=SET)
def state(tag):
    idx = bytes(h.r(lt + 20640 + 101 * T, 101))
    lanes = {sl: struct.unpack('>4h', bytes(h.r(lt + 2 + 258 * i, 8))) for sl, i in enumerate(idx) if i < 128}
    print(tag, 'lanes (slot: steps 0..3)', lanes, 'POS store', k.slot(T, 55) >> 8, 'step0 word', bytes(h.r(pat + 4, 2)).hex() if False else '')
state('before')
h.press(cfkit.RECORD, 500_000); h.frames(20); h.release(cfkit.RECORD); h.frames(20)
h.press(cfkit.TRIG(1), 500_000); h.frames(80)
h.turn(4, 1, 30); h.frames(30); h.run(200_000_000)
h.png('lock17c_held.png')
state('held, POS turned')
h.release(cfkit.TRIG(1)); h.frames(20); h.run(200_000_000)
state('released')
print('setter calls', len(calls))
for w in calls[:6]:
    print('   ret %#x args %s  next words %s' % (w[0], [hex(x) for x in w[1:5]], [hex(x) for x in w[5:8]]))
print('ctx0', hex(s.ctx0))
