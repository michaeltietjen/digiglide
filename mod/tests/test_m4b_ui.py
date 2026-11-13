"""DigiGlide M4b (spec rev 3, M4's UI tests): both pages on screen, turnable and p-lockable through the stock UI.

Track 1 = a DigiGlide sound. Checks, in the emulated OS with the panel's own keys and encoders:
  - [SYN] cycles through WAVETONE's 3 pages and DigiGlide's HARMONY and MOTION (page dots: 5); screenshots of both;
  - a WAVETONE track with VCNT OFF keeps the pages (screenshot); FM TONE keeps stock's page count;
  - knob A on HARMONY turns KEY: the sound's slot 50 follows, within KEY's range;
  - GRID RECORDING, hold trig 1, turn knob C: a p-lock of DEG (slot 52) on step 1 in the pattern, the sound unchanged;
    the locked cell is drawn inverted; a trig on step 1 reads the locked DEG and KEY from the sound (the hook's read).
    ~/dn2-workspace/repos/digikit/.venv/bin/python test_m4b_ui.py [DIGIGLIDE.syx]
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, G, U16, SLOT0
from osver import A
import cfkit
from emu import panelin

img = sys.argv[1] if len(sys.argv) > 1 else latest()
OUT = os.path.expanduser('~/glide/renders/M4')
os.makedirs(OUT, exist_ok=True)
print('image', os.path.basename(img))
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg)


def key_held(h, key):
    """The firmware's key-held bitmap 0x445a1e30, bit (code - 1), code = channel * 8 + bit + 1."""
    code = key[0] * 8 + key[1] + 1
    return (h.r(A(0x445A1E30) + (code - 1) // 8, 1)[0] >> ((code - 1) % 8)) & 1


def let_go(h, key, tries=6):
    for _ in range(tries):
        if not key_held(h, key):
            return True
        h.release(key); h.frames(10); h.run(50_000_000)
    return not key_held(h, key)


def page_now(s):
    return s.drawn_page()                                   # once the redraw has caught up (dgkit)


s = Session(img, tag='m4b')
k, h = s.k, s.k.h
h.out = OUT
show = G.Params(key=2, scl=1, deg=3, chrd=3, vcnt=5, bass=2, sprd=77, move=4, glid=6, path=4, time=2, ordr=3,
                stag=2, drft=12, vib=6, scrb=100)
s.set_sound(show)
seen = []
for _ in range(7):
    k.tap('SYN')
    seen.append(page_now(s))
# WAVETONE's third page draws through its own grid (0x400175e4), which the hook does not see: it reads as the page
# before it, so a 5-page cycle reads [1, 1, 3, 4, 0, 1]
def visits_in_order(seq, order):
    i = 0
    for x in seq:
        if i < len(order) and x == order[i]:
            i += 1
    return i == len(order)


# (a tap can land late in the emulator: the order is checked, not one page per tap)
check(set(seen) <= {0, 1, 3, 4} and visits_in_order(seen, [3, 4, 0]),
      f'[SYN] cycles 5 pages {seen}: WAVETONE 0-2, HARMONY 3, MOTION 4, back to WAVETONE')
check(k.call(A(0x400C24D2), [1]) == 5, 'WAVETONE page count on a DigiGlide track: 5')
check(s.syn_page(3), 'HARMONY reached')
h.png('harmony.png')
check(s.syn_page(4), 'MOTION reached')
h.png('motion.png')

# knob A: KEY (cfkit's turn_to: unheld 11-detent messages, read back after each; the panel queue drains slowly)
s.set_sound(G.Params(key=0, scl=1, deg=0, chrd=1))
s.trig(0, length=127)
s.syn_page(3)
slot = lambda n: k.slot(0, SLOT0 + n)
for burst in (11, 11, 7, 5):                            # (the emulator's knob is slow and coarse: about 44 detents a
    if h.turn_to(0, lambda: slot(0) >> 8, 5, burst=burst, tries=60):     # step, and a big burst can step by 2)
        break
check(slot(0) == 5 << 8, f'knob A turns KEY: slot 50 = {slot(0):#06x} (F)')
h.turn_to(0, lambda: slot(0) >> 8, 12, tries=120)  # past the top: KEY's record range stops it at B
h.run(300_000_000)
check(slot(0) == 11 << 8, f'KEY stops at its maximum (B): slot 50 = {slot(0):#06x}')
s.set_sound(G.Params(key=5, scl=1, deg=0, chrd=1))

# GRID RECORDING, hold trig 1, turn knob C: lock DEG (read back after each message, as turn_to does)
model = h.u32(s.ctx0 + 44)
lock = lambda: k.call(A(0x4003CDBA), [model, 0, 0, SLOT0 + 2]) & 0xFFFFFFFF
locked = lambda: -1 if lock() == 0xFFFFFFFF else (lock() & 0xFFFF) >> 8
# The emulated panel drops a key now and then while its input queue is busy (a [RECORD] tap that does not engage
# GRID RECORDING turns the sound instead of locking): retry the gesture, restoring the sound, up to 4 times.
for attempt in range(4):
    h.run(100_000_000 * (attempt + 1)); h.frames(20)
    h.press(cfkit.RECORD, 500_000); h.frames(20); h.release(cfkit.RECORD); h.frames(20)
    h.press(cfkit.TRIG(1), 500_000); h.frames(80)
    h.turn_to(2, locked, 5, tries=40)
    h.frames(4)
    h.png('harmony_locked_deg_held.png')
    h.release(cfkit.TRIG(1)); h.frames(6)
    let_go(h, cfkit.TRIG(1))                       # a dropped release leaves the trig held: PLAY then does nothing
    h.press(cfkit.RECORD, 500_000); h.frames(20); h.release(cfkit.RECORD); h.frames(20)
    let_go(h, cfkit.RECORD)
    h.run(300_000_000)
    if locked() == 5:
        break
    print(f'    attempt {attempt + 1}: no lock (sound DEG {slot(2) >> 8}), retrying')
    k.slot(0, SLOT0 + 2, 0)
lv = locked()
check(lv == 5 and slot(2) == 0, f'held trig + knob C: DEG p-locked on step 1 to {lv} ({G.ROMAN[lv] if lv >= 0 else "-"}); '
                                f'the sound keeps DEG {slot(2) >> 8}')
steps = k.call(h.u32(h.u32(s.ctx0) + 40), [s.ctx0])
check(h.u16(steps) & 1, f'step 1 keeps its trig ({h.u16(steps):#06x})')
# What a trig on step 1 reads, through the hook's own read path (dg_test_read = read_params: the playing pattern's
# lock table, else the sound). Playback itself is covered by test_m4a.py (locks placed through 0x4004f8fe, the
# function this held-trig turn calls); here the emulated panel will not start PLAY again after the GRID RECORDING
# gestures (no key held, play state stays 0), an emulator limitation noted in notes/build_log.md.
mask = k.call(s.sym['dg_test_read'], [0, 0])
p = s.cur()
check(p.deg == 5 and p.key == 5 and mask == (1 << 2 | 0x10000),           # bit 16: VCNT on
      f'a trig on step 1 reads DEG {G.ROMAN[p.deg]} from the UI lock and KEY {G.NOTE_NAMES[p.key]} from the sound '
      f'(lock mask {mask:#06b})')

# VCNT OFF: the pages stay on a WAVETONE track (VCNT has to be reachable to switch DigiGlide on); other machines are
# stock: the FM TONE page count is the stock table's
s2 = Session(img, tag='m4b_plain')
s2.set_sound(G.Params(), on=False)
check(s2.k.call(A(0x400C24D2), [1]) == 5, 'a WAVETONE track with VCNT OFF keeps the 5 pages (VCNT is reachable)')
check(s2.k.call(A(0x400C24D2), [0]) == s2.k.h.u32(A(0x42432AD4)), f'FM TONE: stock page count ({s2.k.h.u32(A(0x42432AD4))})')
s2.k.h.out = OUT
s2.syn_page(3)
s2.k.h.png('harmony_vcnt_off.png')
print('screenshots:', OUT)
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
