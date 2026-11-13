"""DigiGlide on every machine (rev 6): the settings belong to the track and are kept in the kit, so a DigiGlide track
plays chords with an FM TONE, an FM DRUM or a WAVETONE sound, and a sound load leaves them alone.
  A  FM TONE (the demo's track 2) and FM DRUM (track 15): VCNT 5 from the store, a 4-trig progression: every trig is a
     chord event on the track's own reserved voices, 5 voices sound with the track's machine, later chords glide (one
     attack block), and not one byte of the track's sound was written.
  B  pages: on an FM TONE track [SYN] reaches CHORD, MOTION and SETUP after FM TONE's own four; knob A on CHORD turns
     TYPE in the store, and the sound and every other byte of the live kit but the buffer word stay as they were;
     the knob rows cannot be p-locked or randomised.
  C  a sound load (imitated in memory: another name, another machine's values everywhere) on a DigiGlide track: the
     settings are the track's, the next trigs are still chords.
  D  a WAVETONE sound made with image 14 or older (VCNT's code in slot 54, HOLD's mark in slot 94) on a track never
     set up: its values are taken over into the store once.
  E  a track never set up plays stock notes and the kit's record is not written.
  F  p-locks made with images <= 14 (the lanes of slots 50..64 on a WAVETONE track) still play: a TYPE lock on a step
     changes that step's chord; the same lane on an FM TONE track is FM TONE's own and is not read.
  G  each kit has its own settings (a pattern change, PERFORM KIT: the settings follow the current kit).
  H  a store that is not DigiGlide's (wiped, or garbage after the check word) reads as OFF with the defaults.
  I  switching: [FUNC] + push E on an FM TONE track reserves the voices, again hands them back; SETUP shows the
     tracks that are on.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_every_machine.py [DIGIGLIDE.syx]"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, U16, Ui, FIELDS, SLOTS, slot_code
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
OUT = os.path.expanduser('~/glide/renders/rev6')
os.makedirs(OUT, exist_ok=True)
print('image', os.path.basename(img))
ok = True
NAMES = {0: 'FM TONE', 1: 'WAVETONE', 2: 'FM DRUM', 3: 'SWARMER'}


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def settle(s, n=4):
    for _ in range(n):
        s.k.tap('SYN'); s.k.h.frames(120)


def voices_of(s, t):
    d = s.k.h.u32(s.sym['DG'] + 80)                      # DG.vdata
    v = [s.k.h.r(d + 5 * i + 1, 1)[0] for i in range(16)]
    return v[t], sum(v[:t])


def snd_bytes(s, t):
    return bytes(s.k.h.r(s.k.sound(t), 1163))


def progression(s, t, roots=(60, 65, 67, 62)):
    for st in range(128):
        s.k.call(A(0x40054690), [s.ctx0 + 132 * t, st, 1, 0])
    for i, n in enumerate(roots):
        s.trig(8 * i, note=n, length=127, t=t)
    return s.play(len(roots) * 1500 + 1200, bpm=120)


dgw = lambda s, off: s.k.h.u32(s.sym['DG'] + off)

# ---------------------------------------------------------------- A
for t in (1, 14):
    s = Session(img, tag=f'em_a{t}', solo=True, reserve=0)
    m = s.k.mach(t)
    s.k.h.frames(3200)
    before = snd_bytes(s, t)
    s.set_sound(Ui(vcnt=5, glid=3, drft=0, vib=0), t=t, mach=None, atk=None)
    settle(s)
    have, base = voices_of(s, t)
    check(m in (0, 2) and have == 5, f'A: track {t + 1} ({NAMES.get(m, m)}): VCNT 5 reserves {have} voices from voice {base}')
    fr = progression(s, t)
    mine = ((1 << have) - 1) << base
    ons = [(i, U16(f, 0x22)) for i, f in enumerate(fr) if U16(f, 0x22)]
    outside = [(i, hex(b)) for i, b in ons if b & ~mine]
    swallowed = dgw(s, 96)                               # DG.swallowed
    mid = fr[ons[0][0] + 700] if ons else fr[-1]
    machs = {U16(mid, 0x94 + 2 * (base + j)) for j in range(have)}
    notes = sorted(round(U16(mid, 2 + 2 * (base + j)) / 256) for j in range(have))
    last = fr[-20]
    notes_last = sorted(round(U16(last, 2 + 2 * (base + j)) / 256) for j in range(have))
    check(ons and not outside and swallowed == 4, f'A: track {t + 1}: 4 trigs taken as chords ({swallowed}), no note-on outside its voices {outside[:3]}')
    check(len({i for i, _ in ons}) == 1 and bin(ons[0][1]).count('1') == 5 if ons else False,
          f'A: track {t + 1}: one attack block, 5 voices; the other chords glide (attack blocks {[i for i, _ in ons][:6]})')
    check({n % 12 for n in notes} <= {0, 4, 7} and {n % 12 for n in notes_last} <= {2, 6, 9} and len(set(notes)) >= 4,
          f'A: track {t + 1}: C major sounds {notes}, the last chord is D major {notes_last}')
    check(len(machs) == 1, f'A: track {t + 1}: every chord voice carries one machine word ({sorted(machs)})')
    check(snd_bytes(s, t) == before, f'A: track {t + 1}: the sound itself is byte for byte as before')

# ---------------------------------------------------------------- B
s = Session(img, tag='em_b', solo=True, reserve=0)
k, h = s.k, s.k.h
h.out = OUT
h.frames(3200)
T = 1
check(s.select_track(T) and k.mach(T) == 0, f'B: track 2 (FM TONE) selected (active track {s.active_track() + 1})')
s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3), t=T, mach=None, atk=None)
k.tap('SYN'); h.frames(2200)
seen = []
for _ in range(9):
    k.tap('SYN')
    seen.append(s.drawn_page())
first = struct.unpack('>i', bytes(h.r(s.sym['dg_ui_first'], 4)))[0]
check(first == 4 and {4, 5, 6} <= set(seen) and max(seen) == 6, f'B: [SYN] reaches DigiGlide\'s three pages after FM TONE\'s four (first {first}, pages drawn {seen})')
for page, name in ((4, 'chord'), (5, 'motion'), (6, 'setup'), (0, 'own')):
    s.syn_page(page)
    h.png(f'fmtone_page_{name}.png')
s.syn_page(4)
kit0 = bytes(h.r(h.u32(A(0x800052A0)), 0x5d71))
for burst in (11, 11, 7):
    if h.turn_to(0, lambda: k.slot(T, 50) >> 8, 3, burst=burst, tries=80):
        break
h.frames(300); h.run(400_000_000)
kit1 = bytes(h.r(h.u32(A(0x800052A0)), 0x5d71))
diff = [i for i in range(len(kit0)) if kit0[i] != kit1[i]]
buf = 0x48e4 + 2 * 70
check(k.slot(T, 50) == 3 << 8, f'B: knob A on CHORD turns TYPE in the store: {k.slot(T, 50):#06x} (DIM)')
check(diff and set(diff) <= {buf, buf + 1}, f'B: in the live kit only the buffer word changed (bytes {[hex(x) for x in diff[:6]]}): the FM TONE sound is untouched')
h.png('fmtone_page_chord_dim.png')
row = k.call(s.sym['dg_row'], [0]) if 'dg_row' in s.sym else 0
if row:
    r = struct.unpack('>17I', bytes(h.r(row, 68)))
    check(r[0] & 8 and r[9:13] == (0, 0, 0, 0), f'B: the knob row cannot be p-locked (flags {r[0]:#x}) and has no randomiser')
msg = lambda: bytes(h.r(s.sym['dg_msg'], 28)).split(b'\0')[0].decode()
s.syn_page(6)
mask = k.call(s.sym['dg_on_mask'])
h.png('fmtone_page_setup_tracks.png')
check(mask == 1 << T, f'I: SETUP\'s track row: DigiGlide on on track 2 only (mask {mask:#06x})')
v_on = voices_of(s, T)[0]
s.shortcut(); k.tap('SYN'); h.frames(400); m_off = msg(); v_off = voices_of(s, T)[0]; p_off = k.slot(T, 54)
s.shortcut(); k.tap('SYN'); h.frames(400); v_back = voices_of(s, T)[0]
check(v_on == 5 and p_off == 0 and v_off == 0 and v_back == 5,
      f'I: [FUNC] + push E on the FM TONE track: 5 voices reserved -> OFF hands them back ({v_off}) -> on again reserves {v_back}')
s.select_track(0)
k.tap('SYN'); h.frames(300)
check(k.slot(0, 50) == 0 and k.slot(T, 50) == 3 << 8, f'B: back on track 1 its own TYPE shows ({k.slot(0, 50):#06x}); track 2 keeps {k.slot(T, 50):#06x}')

# ---------------------------------------------------------------- C
s = Session(img, tag='em_c', solo=True, reserve=0)
s.k.h.frames(3200)
s.set_sound(Ui(vcnt=5, key=7, glid=3, hold=1, drft=0, vib=0))
settle(s)
progression(s, 0)                                        # (it plays chords, then the sound is changed under it)
t0 = dgw(s, 96)
was = [s.k.slot(0, sl) for sl in SLOTS]
b = s.k.sound(0)
s.k.h.w(b + 4, b'OTHER SOUND'.ljust(16, b'\0'))
for sl in range(50, 65):
    s.k.sound_slot(0, sl, 0x4000)
settle(s)
check([s.k.slot(0, sl) for sl in SLOTS] == was, 'C: after a sound load the track\'s settings are as they were')
fr = progression(s, 0)
check(t0 == 4 and dgw(s, 96) == 8, f'C: 4 trigs were chords before the load ({t0}), the next 4 are too ({dgw(s, 96) - t0} taken)')

# ---------------------------------------------------------------- D, E
s = Session(img, tag='em_d', solo=True, reserve=0)
k, h = s.k, s.k.h
h.frames(3200); settle(s)
fr = progression(s, 0)
pad = bytes(h.r(s.store(), 337))
check(dgw(s, 96) == 0 and not any(pad), f'E: a track never set up plays stock notes ({dgw(s, 96)} taken) and the kit record\'s spare bytes stay zero')
old = Ui(vcnt=4, type=1, ext=3, key=5, glid=4, hold=1, path=2, bass=3)
assert k.mach(0) == 1
for sl, f in zip(SLOTS, FIELDS):
    k.sound_slot(0, sl, slot_code(f, old[f]) << 8)
settle(s)
got = {f: k.slot(0, sl) >> 8 for sl, f in zip(SLOTS, FIELDS)}
want = {f: slot_code(f, old[f]) for f in FIELDS}
check(s.marked(0) and got == want and h.u32(s.sym['dg_imported']) == 1,
      f'D: an older DigiGlide sound on a track never set up: its settings are taken over once ({h.u32(s.sym["dg_imported"])})'
      + ('' if got == want else f' DIFFER {[(f, got[f], want[f]) for f in got if got[f] != want[f]]}'))
have, base = voices_of(s, 0)
check(have == 4, f'D: and the track reserves its {have} voices')

# ---------------------------------------------------------------- F
name_of = lambda: bytes(h.r(s.sym['dg_name'], 16)).split(b'\0')[0].decode()
k.slot(0, 52, 0); k.slot(0, 51, 0); k.slot(0, 50, 0)       # KEY off, no extension, MAJ
for st in range(128):
    k.call(A(0x40054690), [s.ctx0, st, 1, 0])
s.trig(0, note=60); s.trig(8, note=62); s.trig(16, note=64)
s.lock(8, type=1)                                        # as images <= 14 stored it: slot 50's lane, step 9
names = []
s.play(3 * 1500 + 300, bpm=120, each=lambda i: names.append(name_of()))
seq = [n for i, n in enumerate(names) if n and (i == 0 or names[i - 1] != n)]
check(seq == ['C MAJ', 'D MIN', 'E MAJ'], f'F: a TYPE lock from an older image on step 9 still plays: {seq}')
s2 = Session(img, tag='em_f', solo=True, reserve=0)
s2.k.h.frames(3200)
s2.set_sound(Ui(vcnt=5, glid=3, drft=0, vib=0), t=1, mach=None, atk=None); settle(s2)
for st in range(128):
    s2.k.call(A(0x40054690), [s2.ctx0 + 132, st, 1, 0])
s2.trig(0, note=60, t=1); s2.trig(8, note=62, t=1)
s2.lock(8, t=1, type=1)                                  # on FM TONE slot 50 is the machine's own parameter
names = []
nm2 = lambda: bytes(s2.k.h.r(s2.sym['dg_name'], 16)).split(b'\0')[0].decode()
s2.play(2 * 1500 + 300, bpm=120, each=lambda i: names.append(nm2()))
seq = [n for i, n in enumerate(names) if n and (i == 0 or names[i - 1] != n)]
check(seq == ['C MAJ', 'D MAJ'], f'F: on an FM TONE track that lane is the machine\'s: not read as a DigiGlide lock ({seq})')

# ---------------------------------------------------------------- G, H
s = s2; k, h = s.k, s.k.h
SND = A(0x800052A0)
kit0 = h.u32(SND)
on0 = k.slot(1, 54)
h.w(SND, struct.pack('>I', kit0 + 0x5d71))               # as a pattern change does: the next kit is the current one
on1, mk1 = k.slot(1, 54), s.marked(1)
k.slot(3, 54, 2 << 8); k.slot(3, 50, 2 << 8)             # track 4 of kit 2: 4 voices, SUS
there = (k.slot(3, 54), k.slot(3, 50))
h.w(SND, struct.pack('>I', kit0))
back = (k.slot(1, 54), k.slot(3, 54), s.marked(3))
check(on0 == 0x300 and on1 == 0 and not mk1 and there == (0x200, 0x200) and back == (0x300, 0, False),
      f'G: each kit has its own settings: kit 1 track 2 on ({on0:#x}), kit 2 off ({on1:#x}); kit 2 track 4 set {there}; back in kit 1: {back}')
st = s.store()
keep = bytes(h.r(st, 292))
h.w(st + 4, bytes([0xFF]) * 288)
g1 = (k.call(s.sym['dg_on_mask']), k.slot(1, 54), k.slot(1, 53))
h.w(st + 4, bytes([0xFE] * 7 + [2] + [0xFE] * 10) * 16)        # set up (HOLD's mark), every other value out of range
g2 = (k.call(s.sym['dg_on_mask']), [k.call(s.sym['dg_test_read'], [1, 0]) >> 31, list(bytes(h.r(s.sym['dg_ui'], 18)))])
h.w(st, bytes(292))
g3 = (k.call(s.sym['dg_on_mask']), s.marked(1))
h.w(st, keep)
dflt = [0, 0, 0, 127, 64, 2, 0, 0, 0, 0, 0, 0, 0, 8, 4, 127, 0, 2]
check(g1 == (0, 0, 127 << 8) and g2 == (0, [0, dflt]) and g3 == (0, False) and k.slot(1, 54) == 0x300,
      f'H: garbage after the check word, out-of-range values, a wiped store: all read as OFF with the defaults ({g1}, {g2[0]}, {g3})')
print('screenshots:', OUT)
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
