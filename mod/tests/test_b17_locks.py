"""DigiGlide build 17: p-locks made on the pages (POS, TYPE, EXT, VOIC, GLID, MOVE), packed into the lanes of sound
slots 0 and 100. An FM TONE track (the demo's track 2), DigiGlide on, trigs on steps 1 and 5.
  A  GRID RECORDING, trig 1 held, knob E on CHORD turned: POS is locked on step 1 (lane 0) and follows the knob, the
     track's POS is as it was, the page shows the lock; the knob pushed removes the lock, pushed again locks the
     row's value; after the key is let go the page shows the track's value again.
  B  locks written for step 5 (TYPE DIM, GLID 0) and step 9, which has no trig (POS): the pattern plays, each trig
     reads its own step's values, and the chord takes step 9's POS while it sounds.
  C  a lock is removed: the lane word goes back to "no lock".
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b17_locks.py [DIGIGLIDE.syx]"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, TrigLog
import cfkit
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'renders', 'b17')
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
# The emulated panel cannot turn a knob while a step is held: stock's knob accelerator (0x4011364e, called from the
# knob handler 0x40067470) returns 0 there, with or without the knob pushed. Its result is replaced at 0x400675c8
# with one step (0x100) while `force` is set; everything after that is the stock path (0x40067856 -> 0x40064d08).
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import UC_M68K_REG_D0
force = [0]
h.uc.hook_add(UC_HOOK_CODE, lambda uc, a, sz, u: force[0] and uc.reg_write(UC_M68K_REG_D0, force[0]), begin=0x400675c8, end=0x400675c8)
h.uc.ctl_flush_tb()


def push_knob(want):
    for _ in range(8):                                   # (the emulated panel drops key presses)
        h.press((5, 4)); h.frames(20); h.release((5, 4)); h.frames(30); h.run(100_000_000); h.frames(20)
        if want(get(0, 4)):
            return True
    return False


held = shown = -1
lk = lk_half = unlocked = relocked = None
for attempt in range(6):                                 # (a [RECORD] tap that does not land leaves GRID RECORDING
    h.run(100_000_000 * (attempt + 1)); h.frames(20)     # off; every round toggles it, so one of two rounds has it)
    if s.active_track() != T:
        s.select_track(T)
    if s.drawn_page() != 4:
        s.syn_page(4)
    k.slot(T, 55, pos0)
    h.press(cfkit.RECORD, 500_000); h.frames(20); h.release(cfkit.RECORD); h.frames(20)
    h.press(cfkit.TRIG(1), 500_000); h.frames(80); h.run(100_000_000); h.frames(20)
    held = i32('dg_view_step')
    if held == 0:
        force[0] = 0x100
        for _ in range(10):
            h.turn(4, 1, 1, hold=False); h.frames(30); h.run(150_000_000); h.frames(20)
            if get(0, 4) >= 67:
                break
        lk = get(0, 4)
        lane_lk = lane(0, 0)
        force[0] = 0x80                                  # half steps add up
        for _ in range(8):
            h.turn(4, 1, 1, hold=False); h.frames(30); h.run(150_000_000); h.frames(20)
            if get(0, 4) >= lk + 2:
                break
        lk_half = get(0, 4)
        force[0] = 0
        shown = i32('dg_view_locks')
        h.frames(40)
        h.png('chord_pos_locked_held.png')
        unlocked = push_knob(lambda v: v == -1)
        lane_un = lane(0, 0)
        shown_un = i32('dg_view_locks')
        relocked = push_knob(lambda v: v >= 0)
        lk_re = get(0, 4)
    h.release(cfkit.TRIG(1)); h.frames(30); h.run(200_000_000); h.frames(30)
    for _ in range(4):                                   # (a dropped release leaves the step held: image 31's layout)
        if i32('dg_view_step') == -1:
            break
        h.release(cfkit.TRIG(1)); h.frames(30); h.run(200_000_000); h.frames(30)
    if held == 0:
        h.png('chord_after_release.png')
        h.press(cfkit.RECORD, 500_000); h.frames(20); h.release(cfkit.RECORD); h.frames(20); h.run(300_000_000)
        break
    print(f'    attempt {attempt + 1}: no step held (GRID RECORDING not on), retrying')
check(held == 0 and lk is not None and lk >= 67 and lane_lk == 8192 + lk + 1, f'A: POS locked on step 1 and following the knob: {lk} (lane 0 word {lane_lk})')
check(lk_half is not None and lk_half >= lk + 2, f'A: half-step knob moves add up: {lk} -> {lk_half}')
check(k.slot(T, 55) == pos0, f'A: the track\'s POS is as it was ({k.slot(T, 55) >> 8})')
check(held == 0 and shown == 1 << 4, f'A: while held the page showed step 1 with POS locked (lock bits {shown:#x})')
check(unlocked and lane_un == -1 and shown_un == 0, 'A: the knob pushed with the step held removed the lock (stock\'s "remove lock")')
check(relocked and lk_re == pos0 >> 8, f'A: pushed again: locked at the row\'s value ({lk_re})')
check(i32('dg_view_step') == -1 and i32('dg_view_locks') == 0, 'A: key let go: the page shows the track again')
check(get(0, 0) == -1 and get(0, 1) == -1 and get(4, 4) == -1, 'A: nothing else is locked')
fx = [sl for sl in range(70, 88) if h.r(lt + 20640 + 101 * T + sl, 1)[0] < 128]
check(not fx, f'A: stock filed no lock under the rows\' own slots 70..87 (the filter envelope): {fx}')

s = Session(img, tag='b17b', solo=True, reserve=0)        # (after GRID RECORDING gestures the emulator's PLAY is unreliable)
k, h = s.k, s.k.h
T = 0
s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, pos=64, voic=64), t=T, mach=None, atk=None)
s.trig(0, note=60, length=14, t=T)
s.trig(4, note=62, length=14, t=T)
pat = h.u32(A(0x42C5A9A0)); lt = pat + 97872
check(k.call(A(0x4003EFDE), [s.app]) == s.ctx0, 'B: (the session\'s active track is track 1: locks go to it)')
put = lambda step, kk, v: k.call(s.sym['dg_lock_put'], [T, step, kk, v & 0xFFFFFFFF]) & 0xFF
check(put(0, 4, 100) and put(4, 0, 3) and put(4, 5, 0) and put(8, 4, 20), 'B: locks written: step 5 TYPE DIM, GLID 0; step 9 (no trig) POS 20')
check((get(4, 0), get(4, 5), get(8, 4), get(4, 4)) == (3, 0, 20, -1), f'B: read back {(get(4, 0), get(4, 5), get(8, 4), get(4, 4))}')
check(lane(0, 4) == 8192 + 129 * 4 and lane(100, 4) == 129 * 1, f'B: lane words {lane(0, 4)}, {lane(100, 4)}')
log = TrigLog(s)
steps = []
def each(i):
    log(i)
    steps.append(s.dg()['last_step'])
fr = s.play(2600, bpm=120, each=each)
d = s.dg()
seen = sorted(set(steps))
check(d['trigs'] >= 2, f'B: both trigs played ({d["trigs"]} chord events)')
check(any(l >> 4 & 1 for l in log.locks) and any(l & 1 for l in log.locks), f'B: a trig read POS locked, another TYPE locked (lock bits {sorted(set(log.locks))})')
check(8 in seen, f'B: the chord took step 9\'s lock while it sounded (steps used {seen})')

check(put(4, 0, -1) and get(4, 0) == -1 and get(4, 5) == 0, 'C: TYPE unlocked on step 5, GLID still locked')
check(put(4, 5, -1) and lane(100, 4) == -1, f'C: the last lock of the word removed: lane word {lane(100, 4)}')
print('screenshots:', os.path.abspath(OUT))
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
