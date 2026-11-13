"""BRICKGLIDE PAD (spec, "Starter sound"): built on a WAVETONE track in the emulated OS, saved with stock's own sound
converter (0x400dd6a6: live sound -> stored sound, the form the OS writes to a project or the +Drive), then loaded
into another track with stock's loader (0x400dd1ea) and played: loading it turns DigiGlide on (VCNT 5).

Writes ~/glide/sounds/BRICKGLIDE_PAD.stored.bin (the stored sound, stock layout, magic 0xbeefbace) and
BRICKGLIDE_PAD.json (every value set, for building it by hand on the unit).
    ~/dn2-workspace/repos/digikit/.venv/bin/python make_brickglide_pad.py [DIGIGLIDE.syx]
"""
import json, os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, G, U16, word, edges, SLOTS, FIELDS, Ui, slot_code
from osver import A
import cfkit

img = sys.argv[1] if len(sys.argv) > 1 else latest()
OUT = os.path.expanduser('~/glide/sounds')
os.makedirs(OUT, exist_ok=True)
NAME = 'BRICKGLIDE PAD'
STORED_LEN = 0x200
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg)


# rev 5: one key = one chord. TYPE MIN + EXT 7 (the minor seventh Brickglide's pad started on), KEY OFF, VOIC 64, POS 0,
# GLID 1 bar, HOLD on (a played chord holds, as on Brickglide), PATH Smooth, DRFT 8, VIB 4, VCNT 5, BASS Follow -1
DG = Ui(type=1, ext=2, hold=1, voic=64, glid=5)
# WAVETONE with detuned saw-ish waves, slow amp attack (about 1/2 bar), long release; FX sends: reverb about 50 %,
# delay about 30 %, chorus about 35 %. (The reverb's and delay's own character, large hall and dotted 1/4 tape-ish, are
# the kit's FX settings, not part of a sound.)
SOUND = {
    'WAV1 (26)': (26, 0x0000), 'WAV2 (32)': (32, 0x0000),              # PRIM table position 0: saw
    'TUN2 (31)': (31, 0x4008), 'DRIF (38)': (38, 0x2000),              # osc 2 a few cents up; some drift
    'LEV1 (30)': (30, 0x6400), 'LEV2 (36)': (36, 0x6400),
    'AMP ATK (81)': (81, 0x5400), 'AMP HOLD (82)': (82, 0x7f00), 'AMP DEC (83)': (83, 0x7f00),
    'AMP SUS (84)': (84, 0x7f00), 'AMP REL (85)': (85, 0x6800),
    'REV send (87)': (87, 0x4000), 'DEL send (86)': (86, 0x2600), 'CHR send (88)': (88, 0x2d00),
}

s = Session(img, tag='pad')
k, h = s.k, s.k.h
s.set_sound(DG)
for sl, f in zip(SLOTS, FIELDS):                 # rev 6 keeps the settings in the kit; the saved sound still carries
    k.sound_slot(0, sl, slot_code(f, DG[f]) << 8)   # them in the slots images <= 14 used (a newer image takes them over)
for _, (sl, v) in SOUND.items():
    k.sound_slot(0, sl, v)
h.w(k.sound(0) + 4, NAME.encode().ljust(16, b'\0'))
BUF = cfkit.SPARE + 0x10000
h.w(BUF, bytes(0x400))
r = k.call(A(0x400DD6A6), [BUF, k.sound(0), 0])
stored = bytes(h.r(BUF, STORED_LEN))
check(r & 0xFF and stored[:4] == bytes.fromhex('beefbace'), f'saved with stock\'s converter (magic {stored[:4].hex()})')
open(os.path.join(OUT, 'BRICKGLIDE_PAD.stored.bin'), 'wb').write(stored)

# load it into track 6 (another track, FM TONE in the demo) with stock's loader, then play it there
cfg = k.call(A(0x40030AF8), [k.call(A(0x4003E41A), [s.app])])
k.call(A(0x40029094), [cfg, 0, 0]); k.call(A(0x40029094), [cfg, 5, 6])    # track 6 reserves the 6 voices
before = k.mach(5)
r2 = k.call(A(0x400DD1EA), [k.sound(5), BUF])
name = bytes(h.r(k.sound(5) + 4, 16)).split(b'\0')[0].decode()
slots_ok = all(k.sound_slot(5, sl) == slot_code(f, DG[f]) << 8 for sl, f in zip(SLOTS, FIELDS) if f != 'play')   # (PLAY: not saved)
check(r2 & 0xFF and k.mach(5) == 1 and name == NAME and slots_ok,
      f'loaded into track 6 (machine {before} -> {k.mach(5)} WAVETONE, name "{name}", DigiGlide slots as saved)')
h.frames(3200)                                   # rev 6: the UI takes the sound's settings over into track 6's own
for _ in range(3):
    k.tap('SYN'); h.frames(120)
on = k.call(s.sym['dg_test_read'], [5, 0]) >> 31
check(on == 1 and s.cur().vcnt == 5, f'track 6 reads VCNT on, {s.cur().vcnt} voices: DigiGlide on by loading the sound (taken over: {s.marked(5)})')
s.trig(4, note=60, length=127, t=5)                 # (step 5: the emulator's PLAY starts just after step 1)
fr = s.play(1500, bpm=120)
if not any(U16(f, 0x22) for f in fr):               # (the emulator's first PLAY after [SYN] taps can stay silent, on
    fr = s.play(1500, bpm=120)                      # every track: play again)
# (rev 4: the track's reserved voices are wherever stock packs them; track 1, the same sound, holds its own block)
ons = [i for i, f in enumerate(fr) if any(U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) == 5 for v in range(16))]
att = [v for v in range(16) if ons and (U16(fr[ons[0]], 0x22) >> v) & 1 and U16(fr[ons[0]], 0xA5A + 2 * v) == 5]
check(len(att) == 5 and s.dg()['trigs'] >= 1, f'a trig on track 6 plays a DigiGlide chord ({s.dg()["trigs"]} chord events): {len(att)} voices '
      f'{[round(word(fr[ons[0]], v) / 256) for v in att] if att else []}')
json.dump({'name': NAME, 'digiglide': {f: DG[f] for f in FIELDS},
           'sound_slots': {k_: f'{v:#06x}' for k_, (_, v) in SOUND.items()},
           'machine': 'WAVETONE', 'stored': 'BRICKGLIDE_PAD.stored.bin (stock converter 0x400dd6a6, 512 bytes)'},
          open(os.path.join(OUT, 'BRICKGLIDE_PAD.json'), 'w'), indent=1)
print('wrote', OUT)
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
