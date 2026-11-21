"""DigiGlide build 24: BAL, the bass voice against the chord (owner: "bass is quiet"). A held chord (HOLD on, 5 voices,
BASS FOL: the bass voice is engine voice 4), level words read from the frames.
  A  BAL 0 (centre, knob 64): every voice at the sound's level, as image 23
  B  BAL +63: the bass voice's level word at most 127 (0x7F00) and above the sound's, the chord voices at 25 %
  C  BAL -64: the bass voice silent (level word 0), the chord at the sound's level
  D  BAL with BPAT PULS: the odd steps' accent still 80 % of the even steps' (below the 127 cap)
  E  pattern notes plucked (RSET 256) at AMP ATK 0, rising from the bass's level (RSET 0) at AMP ATK 60
  F  the store: a kit saved by image 23 (no BAL byte) reads 64; BAL kept per track; a DGK1 kit converts with BAL 64
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b24_bal.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
K_BPAT, K_BAL = 19, 23
BV = 4
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def run(tag, bal, bpat=0, atk=None, blocks=1500):
    s = Session(img, tag='b24' + tag, solo=True)
    s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, voic=64, bass=3, hold=1), t=0, mach=None, atk=atk)
    s.k.call(s.sym['dg_par_set'], [0, K_BPAT, bpat << 8])
    s.k.call(s.sym['dg_par_set'], [0, K_BAL, bal << 8])
    s.trig(0, note=48, length=30, t=0)
    return s, s.play(blocks, bpm=120)


lvl = lambda f: [U16(f, 0x74 + 2 * v) for v in range(5)]
_, fr = run('A', 64)
a = lvl(fr[1200])
check(len(set(a)) == 1 and a[0] > 0, f'A BAL 0: {a}')
snd = a[0]
_, fr = run('B', 127)
b = lvl(fr[1200])
check(snd < b[BV] <= 0x7F00 and all(abs(x - snd / 4) <= snd * 0.02 for x in b[:4]), f'B BAL +63: {b} (sound {snd})')
_, fr = run('C', 0)
c = lvl(fr[1200])
check(c[BV] == 0 and all(x == snd for x in c[:4]), f'C BAL -64: {c}')
_, fr = run('D', 90, bpat=1, blocks=2400)
ons = [(b, U16(f, 0x74 + 2 * BV)) for b, f in enumerate(fr) if U16(f, 0x22) >> BV & 1]
ev = {w for b, w in ons[1:6] if round((b - ons[0][0]) / 375) % 2 == 0}      # (steps from the pattern's first)
od = {w for b, w in ons[1:6] if round((b - ons[0][0]) / 375) % 2 == 1}
check(ev and od and all(abs(o / e - 0.8) < 0.01 for o in od for e in ev) and max(ev) > snd,
      f'D BAL +26 PULS: even {sorted(ev)}, odd {sorted(od)}')
res = {}
for atk in (0, 60):
    _, fr = run(f'E{atk}', 64, bpat=1, atk=atk, blocks=2000)
    res[atk] = sorted({U16(f, 0xDA + 146 * BV + 134) for f in fr if U16(f, 0x22) >> BV & 1})
check(res[0] == [256] and res[60] == [0], f'E RSET of the bass notes: ATK 0 {res[0]}, ATK 60 {res[60]}')
s, _ = run('F', 64, blocks=10)
st, h = s.store(), s.k.h
rd = lambda t, k: s.k.call(s.sym['dg_par'], [t, k]) >> 8
h.w(st + 260, b'\0' * 16)                               # as image 23 left it
r0 = rd(0, K_BAL)
s.k.call(s.sym['dg_par_set'], [0, K_BAL, 20 << 8])
s.k.call(s.sym['dg_par_set'], [1, K_BAL, 100 << 8])
r1 = (rd(0, K_BAL), rd(1, K_BAL), rd(2, K_BAL))
old = bytearray(4 + 18 * 16 + 16)
old[0:4] = b'DGK1'
for k, v in enumerate([2, 3, 5, 90, 70, 4, 1, 2, 3, 1, 2, 3, 4, 20, 10, 100, 3, 2]):
    old[4 + k] = v
h.w(st, bytes(old))
s.k.call(s.sym['dg_par_set'], [0, 21, 40 << 8])          # (BLOOM: the first edit converts the kit)
r2 = (bytes(h.r(st, 4)), rd(0, K_BAL), rd(0, 2))
check(r0 == 64 and r1 == (20, 100, 64) and r2 == (b'DGK2', 64, 5), f'F store: image 23 kit {r0}, set {r1}, DGK1 -> {r2}')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
