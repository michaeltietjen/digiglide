"""DigiGlide: HOLD keeps the chord in the stock arpeggiator. A DigiGlide track (TYPE MIN, EXT 7), arp MODE UP,
short trigs (6 long, as live-recorded ones are): C3 on step 1 and D3 on step 9.
Stock gives every note in the arp's set its trig's length and takes it out when that runs out, so the arp plays
only while the trig lasts (image 18 on the unit: "only plays the first chord and then ducks out").
  A  HOLD on: the arp walks the whole chord until the next trig's chord replaces it; no DigiGlide chord event.
     Then [STOP]: the chord leaves the arp.
  B  HOLD off: as image 18 and stock, the arp plays while the trig lasts (one note each here).
  C  one run, a chord held by HOLD each time: HOLD switched off lets it go; the arp switched off lets it go; a
     mute lets it go.
  D  by hand (sequencer stopped): a key's chord stays after the key's "note out"; another key replaces it; the
     same key again lets it go; [STOP] lets it go. (The emulated panel takes no second key: the later keys are
     calls of the hooked "notes in" / "note out", as stock's handler makes them.)
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_arp_hold.py [DIGIGLIDE.syx]"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16
import osver
from emu import panelin

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
ARP_SET, UP, T = 0x40599728, 2, 0                        # OS 1.12: the arp's notes, 16 bytes a track
C1, C2 = [48, 51, 55, 58], [50, 53, 57, 60]
SCRATCH = 0x46BF0000                                     # cfkit's spare RAM: a note record for "notes in"


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def session(tag, hold, trigs=True):
    s = Session(img, tag=tag, solo=True, reserve=0)
    s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, pos=64, voic=64, hold=hold), t=T, mach=None, atk=None)
    if trigs:
        s.trig(0, note=48, length=6, t=T)
        s.trig(8, note=50, length=6, t=T)
    snd = s.k.sound(T)
    s.k.h.uc.mem_write(snd + 351, bytes([UP])); s.k.h.uc.mem_write(snd + 374, bytes([UP]))
    return s


def arp_set(s):
    b = bytes(s.k.h.r(ARP_SET + 16 * T, 16))
    return [32 * w + i for w in range(4) for i in range(32) if struct.unpack_from('>I', b, 4 * w)[0] >> i & 1]


def latches(s):
    return int.from_bytes(bytes(s.k.h.r(s.sym['dg_arp_latches'], 2)), 'big')


def ons(frames):
    return [(b, U16(f, 2 + 2 * v) >> 8) for b, f in enumerate(frames) for v in range(16)
            if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) == T]


def btn(h, g, m, n=3_000_000, fr=30):
    h.pc = panelin.buttons(h.m, h.profile, g, m); h.run(n); h.frames(fr)


# A: HOLD on
s = session('aha', 1)
sets = {}
fr = s.play(2900, bpm=120, each=lambda i: sets.__setitem__(i, arp_set(s)))[:2900]
n = ons(fr)
first, second = [k for b, k in n if b < 1500], [k for b, k in n if b >= 1500]
check(sets[300] == C1 and sets[1400] == C1 and latches(s) == 1, f'A: the chord is still in the arp long after its trig ended (block 300 {sets[300]}, block 1400 {sets[1400]})')
check(len(first) >= 8 and first[:8] == C1 + C1, f'A: the arp walks the whole chord, and again, until the next trig: {first}')
check(sets[1600] == C2 and len(second) >= 6 and second[:4] == C2 and set(second) == set(C2), f'A: the next trig\'s chord replaces it (set {sets[1600]}): {second}')
check(s.dg()['trigs'] == 0, f'A: no DigiGlide chord event ({s.dg()["trigs"]})')
h = s.k.h
st = len(h.sent)
h.frames(900)                                            # (the emulated UI acts on [STOP] up to 650 frames later)
tail = ons([x for x, _ in h.sent[-200:]])
check(not arp_set(s) and latches(s) == 0 and not tail, f'A: [STOP]: the chord leaves the arp (set {arp_set(s)}, held {latches(s)}, notes in the last 200 blocks {tail})')

# B: HOLD off
s = session('ahb', 0)
sets = {}
fr = s.play(2900, bpm=120, each=lambda i: sets.__setitem__(i, arp_set(s)))[:2900]
n = ons(fr)
check(sets[50] == C1 and not sets[300] and sets[1550] == C2 and not sets[1800] and latches(s) == 0,
      f'B: HOLD off: the chord leaves the arp with its trig (block 50 {sets[50]}, 300 {sets[300]}, 1550 {sets[1550]}, 1800 {sets[1800]})')
check([k for b, k in n] == [48, 50], f'B: so a short trig plays one note, as image 18 and stock: {n}')

# C: what lets a held chord go
s = session('ahc', 1)
s.trig(16, note=48, length=6, t=T)                       # (block 3000: a chord for the mute to let go)
h, snd = s.k.h, s.k.sound(T)
hold_at = s.store() + 4 + 18 * T + 7                     # the kit's record: HOLD 2 = off, 3 = on
MUTE = osver.A(0x8000521A)
sets, held = {}, {}


def steer(i):
    if i == 600:
        h.w(hold_at, bytes([2]))                         # HOLD off
    if i == 1400:
        h.w(hold_at, bytes([3]))
    if i == 2000:
        h.uc.mem_write(snd + 351, bytes([0]))            # arp OFF
    if i == 2900:
        h.uc.mem_write(snd + 351, bytes([UP]))
    if i == 3600:
        h.w(MUTE, struct.pack('>H', int.from_bytes(bytes(h.r(MUTE, 2)), 'big') | 1 << T))
    sets[i], held[i] = arp_set(s), latches(s)


fr = s.play(3900, bpm=120, each=steer)[:3900]
n = ons(fr)
check(sets[590] == C1 and held[590] == 1 and not sets[610] and held[610] == 0, f'C: HOLD switched off lets the chord go (block 590 {sets[590]}, 610 {sets[610]})')
check(sets[1990] == C2 and held[1990] == 1 and not sets[2010] and held[2010] == 0, f'C: the arp switched off lets it go (block 1990 {sets[1990]}, 2010 {sets[2010]})')
check(sets[3590] == C1 and held[3590] == 1 and not sets[3610] and held[3610] == 0, f'C: a mute lets it go (block 3590 {sets[3590]}, 3610 {sets[3610]})')
quiet = [(b, k) for b, k in n if 800 <= b < 1500 or 3800 <= b]
check(not quiet, f'C: and the arp plays nothing after HOLD off or the mute ({quiet})')

# D: by hand, the sequencer stopped
s = session('ahd', 1, trigs=False)
k, h, snd = s.k, s.k.h, s.k.sound(T)
u32 = lambda name: struct.unpack('>I', bytes(h.r(s.sym[name], 4)))[0]
k.tap('KEYB')
btn(h, 3, 0x01, fr=1500)
one = arp_set(s)
check(len(one) == 4 and latches(s) == 1, f'D: a held key gives the arp its chord ({one})')
k.call(s.sym['dg_arp_out'], [T, one[0]])
st = len(h.sent)
h.frames(1200)
n = [x for b, x in ons([x for x, _ in h.sent[st:]])]
check(arp_set(s) == one and len(n) >= 3 and set(n) <= set(one), f'D: the key\'s "note out" leaves the chord in the arp, which plays on: {n[:8]}')
level = struct.unpack('>I', bytes(h.r(0x405994CC + 40 * T, 4)))[0]   # the arp's source level, as the key gave it


def key_in(note):
    h.w(SCRATCH, bytes([0, 0, note, 100, 127, 0, 0, 0]) + bytes(8))
    r = k.call(s.sym['dg_arp_in'], [T, SCRATCH, 0, 0xFFFFFFFF, 127, 0, level, snd, SCRATCH + 8, SCRATCH + 12])
    return r, struct.unpack('>I', bytes(h.r(SCRATCH + 8, 4)))[0]


key_in(one[0] + 2)
two = arp_set(s)
check(len(two) == 4 and two[0] == one[0] + 2 and not set(two) & {one[0]} and latches(s) == 1, f'D: another key replaces the chord ({two})')
r, is_on = key_in(one[0] + 2)
check(not arp_set(s) and latches(s) == 0 and is_on == 1, f'D: the same key again lets it go (set {arp_set(s)}; the arp still takes the note: {is_on})')
key_in(one[0])
check(arp_set(s) == one and latches(s) == 1, f'D: a key after that holds its chord again ({arp_set(s)})')
btn(h, 2, 0x10); btn(h, 2, 0x00)                         # [STOP]
h.frames(900)
check(not arp_set(s) and latches(s) == 0, f'D: [STOP] lets it go (set {arp_set(s)})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
