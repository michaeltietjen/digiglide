"""DigiGlide build 17: what stock calls when a knob of a lockable DigiGlide row is turned or pushed with a step held
(GRID RECORDING, FM TONE track, CHORD page, trig 1, knob E = POS). The emulated panel's knob gives no delta while a
step is held (the accelerator 0x4011364e returns 0), so its result is replaced at 0x400675c8. Prints the calls of
"set lock" and "get lock" and of the held-turn method (0x40067860 -> 0x40065022 -> 0x40064d08).
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b17_held_knob_trace.py [DIGIGLIDE.syx]"""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mod', 'tests'))
from dgkit import Session, latest, Ui, TrigLog
import cfkit
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'renders', 'b17')
os.makedirs(OUT, exist_ok=True)
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


T = 1
s = Session(img, tag='b17', solo=True, reserve=0)
k, h = s.k, s.k.h
h.out = OUT
h.frames(3200)
check(s.select_track(T) and k.mach(T) == 0, 'track 2 (FM TONE) selected')
s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, pos=64, voic=64), t=T, mach=None, atk=None)
s.trig(0, note=60, length=14, t=T)
s.trig(4, note=62, length=14, t=T)
pat = h.u32(A(0x42C5A9A0)); lt = pat + 97872
i32 = lambda name: struct.unpack('>i', bytes(h.r(s.sym[name], 4)))[0]
get = lambda step, kk: struct.unpack('>i', struct.pack('>I', k.call(s.sym['dg_lock_get'], [T, step, kk]) & 0xFFFFFFFF))[0]


def lane(slot, step):
    i = h.r(lt + 20640 + 101 * T + slot, 1)[0]
    return None if i >= 128 else struct.unpack('>h', bytes(h.r(lt + 2 + 258 * i + 2 * step, 2)))[0]


k.tap('SYN'); h.frames(2200)
for _ in range(9):
    k.tap('SYN')
    if s.drawn_page() == 4:
        break
check(s.drawn_page() == 4, 'CHORD on screen')
pos0 = k.slot(T, 55)
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import *
calls = []
force = [0]
SET, GET = A(0x4004F8FE), A(0x4004EAA4)
def hook(uc, addr, size, user):
    sp = uc.reg_read(UC_M68K_REG_A7)
    st = struct.unpack('>6I', bytes(uc.mem_read(sp, 24)))
    if addr == 0x400675c8:
        if force[0]:
            uc.reg_write(UC_M68K_REG_D0, force[0] & 0xFFFFFFFF)
        return
    if addr == 0x40067860:
        calls.append(('HELDTURN -> %#x' % uc.reg_read(UC_M68K_REG_A0), st)); return
    if addr == GET and st[0] in (0x4005c5fa, 0x40015e94): return
    calls.append(({SET: 'SET', GET: 'GET', 0x40064d08: 'DELTA-LAMBDA', 0x40064db6: 'DELTA-CALL a0=%#x' % uc.reg_read(UC_M68K_REG_A0)}.get(addr, hex(addr)), st))
for a in (SET, GET, 0x400675c8, 0x40067860, 0x40064d08, 0x40064db6):
    h.uc.hook_add(UC_HOOK_CODE, hook, begin=a, end=a)
h.uc.ctl_flush_tb()
def show(tag):
    print(tag, 'lock', get(0, 4), 'lane0', lane(0, 0), 'track POS', k.slot(T, 55) >> 8)
    for n, st in calls[:14]: print('    %s %s' % (n, [hex(x) for x in st]))
    calls.clear()
for attempt in range(6):
    h.press(cfkit.RECORD, 500_000); h.frames(20); h.release(cfkit.RECORD); h.frames(20)
    h.press(cfkit.TRIG(1), 500_000); h.frames(80); h.run(100_000_000); h.frames(20)
    if i32('dg_view_step') == 0: break
    h.release(cfkit.TRIG(1)); h.frames(30); h.run(200_000_000)
print('held step', i32('dg_view_step')); calls.clear()
for d in (0x100, 0x100, 0x300, 0x80, 0x80, -0x180, 0x4000):
    force[0] = d
    h.turn(4, 1, 1, hold=False); h.frames(30); h.run(150_000_000); h.frames(20)
    force[0] = 0
    show('forced delta %d' % d)
for b in range(3):
    h.press((5, 4)); h.frames(20); h.release((5, 4)); h.frames(30); h.run(100_000_000); h.frames(20)
    show('push %d' % b)
h.release(cfkit.TRIG(1)); h.frames(30); h.run(200_000_000); h.frames(30)
print('after release: view step', i32('dg_view_step'), 'locks', i32('dg_view_locks'), 'lock', get(0, 4), 'track POS', k.slot(T, 55) >> 8)
force[0] = 1
h.turn(4, 1, 1, hold=False); h.frames(30); h.run(150_000_000); h.frames(20)
force[0] = 0
show('free forced delta 1')
