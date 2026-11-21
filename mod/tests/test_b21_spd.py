"""DigiGlide build 21: SPD, the speed of strums and harp runs (SETUP knob C, FX word k 88). Gap = the build 19 gap
x 2^((SPD - 64) / 24): strum 20 blocks at 64, harp 51.
  A  STRM at SPD 64, 0, 127: 4 note-ons 20, 3, 120 blocks apart.
  B  HARP at SPD 100: notes 144 blocks apart.
  C  a kit saved before build 21 (the SPD byte 0) reads SPD 64.
  D  the knob: the buffer word k 88 reaches the track's SPD with SETUP on screen (screenshots in out/b21).
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b21_spd.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
K_SPD = 18
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'experiments', 'out', 'b21')
os.makedirs(OUT, exist_ok=True)


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def gaps_of(tag, play, spd):
    s = Session(img, tag=tag, solo=True)
    s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, voic=64, play=play), t=0, mach=None, atk=None)
    if spd is not None:
        s.k.call(s.sym['dg_par_set'], [0, K_SPD, spd << 8])
    s.trig(0, note=48, length=100, t=0)
    fr = s.play(2400, bpm=120)
    ons = [b for b, f in enumerate(fr) for v in range(16) if U16(f, 0x22) >> v & 1]
    return s, [ons[i + 1] - ons[i] for i in range(len(ons) - 1)]


for spd, want in [(64, 20), (0, 3), (127, 120)]:
    s, g = gaps_of(f'b21a{spd}', 1, spd)
    check(g[:3] == [want] * 3, f'A: STRM SPD {spd}: gaps {g[:3]}, want {want}')

s, g = gaps_of('b21b', 3, 100)
check(len(g) >= 4 and set(g[1:5]) == {144}, f'B: HARP SPD 100: gaps {g[:6]}, want 144')

s = Session(img, tag='b21c', solo=True)
s.set_sound(Ui(vcnt=4, type=1), t=0, mach=None, atk=None)
base = A(0x405CD96C) + 0xae0200
hits = [base + 0x2a00 * i + 0x28af for i in range(129) if bytes(s.k.h.r(base + 0x2a00 * i + 0x28af, 4)) in (b'DGK1', b'DGK2')]
for r in hits:                                  # build 23: the store may be DGK2; make it an image <= 20's DGK1
    old = bytearray(4 + 18 * 16 + 16)           # (track 1: TYPE MIN, VCNT 4 voices, HOLD off; SPD byte 0)
    old[0:4] = b'DGK1'
    old[4:4 + 18] = bytes([1, 0, 0, 127, 64, 2, 0, 2, 0, 0, 0, 0, 0, 8, 4, 127, 2, 2])
    s.k.h.w(r, bytes(old))
spd = s.k.call(s.sym['dg_par'], [0, K_SPD]) >> 8
check(hits and spd == 64, f'C: an old kit (SPD byte 0, {len(hits)} stores) reads SPD {spd}')
s.k.call(s.sym['dg_par_set'], [0, K_SPD, 10 << 8])
check(s.k.call(s.sym['dg_par'], [0, K_SPD]) >> 8 == 10 and s.k.call(s.sym['dg_par'], [0, 6]) >> 8 == 0,
      'C: SPD 10 written and read back; PLAY untouched')

s = Session(img, tag='b21d', solo=True)
k, h = s.k, s.k.h
h.out = OUT
h.frames(3200)
s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, voic=64, play=1), t=0, mach=None, atk=None)
k.tap('SYN'); h.frames(2200)
for _ in range(12):
    if s.drawn_page() == h.u32(s.sym['dg_ui_first']) + 2:
        break
    k.tap('SYN'); h.frames(300)
check(s.drawn_page() == h.u32(s.sym['dg_ui_first']) + 2, 'D: SETUP on screen')
buf = h.u32(A(0x800052A0)) + 0x48e4 + 2 * (70 + K_SPD)
for v in (100, 30):
    h.w(buf, bytes([v, 0])); h.frames(60)
    got = k.call(s.sym['dg_par'], [0, K_SPD]) >> 8
    check(got == v, f'D: knob C (buffer {v}) -> SPD {got}')
    h.png(f'setup_spd_{v}_strm.png')
k.call(s.sym['dg_par_set'], [0, 6, 3 << 8]); h.frames(60)
h.png('setup_spd_30_harp.png')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
