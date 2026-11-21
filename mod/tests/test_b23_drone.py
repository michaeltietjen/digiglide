"""DigiGlide build 23: the drone pieces, and the store's new layout.
  A  TYPE 5TH: for every root (12 trigs, C3 up) and VCNT 3..6 (BASS OFF), each chord's notes are the root and its
     fifth only, both present, one note a voice
  B  BLOOM: 0 (centre) leaves every voice's level word as the sound's; -64 leaves the lowest voice alone (the others'
     level words 0); +63 moves the upper voices' levels between 25 % and 100 %, each its own way, the lowest steady
  C  STRK 2 beats with HOLD on: the held chord is struck again every 2 beats, at 90 and 140 BPM
  D  a BLOOM lock on a step (lane 65): that trig thins, the next unlocked trig does not
  E  TIME DRON: with GLID 1 bar (C MAJ to F# MAJ, no drift or vibrato) the voices land from the lowest up, the top
     at GLID, the lowest at GLID / 1.75
  F  a kit saved by images <= 22 ("DGK1"): read as it was, and rewritten as "DGK2" with every setting kept at its
     first edit
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b23_drone.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
K_BLOOM, K_STRK = 21, 22
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def session(tag, **kw):
    s = Session(img, tag='b23d' + tag, solo=True)
    p = dict(vcnt=4, type=1, ext=2, glid=3, voic=64, bass=0, hold=1)
    p.update(kw)
    s.set_sound(Ui(**p), t=0, mach=None, atk=None)
    return s


def put(s, k, v):
    s.k.call(s.sym['dg_par_set'], [0, k, v << 8])


def frames(s, blocks, bpm=120):
    return s.play(blocks, bpm=bpm)


step16 = lambda bpm: 2700000 / (bpm * 120)

# A
for vc in (3, 4, 5, 6):
    s = session(f'A{vc}', vcnt=vc, type=4, ext=0, hold=0, glid=0)
    for i in range(12):
        s.trig(i, note=48 + i, length=10, t=0)
    fr = frames(s, int(12 * step16(120)) + 100)
    by = {}
    for b, f in enumerate(fr):
        on = U16(f, 0x22)
        for v in range(6):
            if on >> v & 1:
                by.setdefault(int((b + 5) // step16(120)), []).append((U16(f, 2 + 2 * v) + 128) >> 8)
    good = len(by) == 12
    for i in range(12):
        ns = by.get(i, [])
        good &= len(ns) == vc and {(n - i) % 12 for n in ns} == {0, 7}
    check(good, f'A 5TH VCNT {vc}: {[sorted(by.get(i, [])) for i in (0, 1, 7, 11)]}')

# B
res = {}
for b in (64, 0, 127):
    s = session(f'B{b}')
    put(s, K_BLOOM, b)
    s.trig(0, note=48, length=30, t=0)
    fr = frames(s, 4000)
    lv = [[U16(f, 0x74 + 2 * v) for v in range(4)] for f in fr[600:]]
    notes = [(U16(fr[700], 2 + 2 * v) + 128) >> 8 for v in range(4)]
    res[b] = (lv, notes)
lv, notes = res[64]
check(all(len(set(r)) == 1 for r in lv), f'B BLOOM 0: every voice at the sound\'s level ({lv[0]})')
lv, notes = res[0]
low = notes.index(min(notes))
check(all(r[low] > 0 and all(r[v] == 0 for v in range(4) if v != low) for r in lv[100:]),
      f'B BLOOM -64: the lowest voice alone ({lv[200]})')
lv, notes = res[127]
full = max(max(r) for r in lv)
ups = [v for v in range(4) if v != low]
spans = [(min(r[v] for r in lv) / full, max(r[v] for r in lv) / full) for v in ups]
check(all(r[low] == full for r in lv) and all(0.24 <= a < 0.6 and b - a > 0.3 for a, b in spans),
      f'B BLOOM +63: lowest steady, upper spans {[(round(a, 2), round(b, 2)) for a, b in spans]}')

# C
for bpm in (90, 140):
    s = session(f'C{bpm}')
    put(s, K_STRK, 2)
    s.trig(0, note=48, length=30, t=0)
    beats2 = 8 * step16(bpm)
    fr = frames(s, int(3.3 * beats2), bpm=bpm)
    hits = sorted({b for b, f in enumerate(fr) if U16(f, 0x22) & 0xF})
    gaps = [hits[i + 1] - hits[i] for i in range(len(hits) - 1)]
    check(len(hits) >= 4 and all(abs(g - beats2) <= 1 for g in gaps),
          f'C STRK 2 beats at {bpm} BPM: strikes at {hits[:5]} (gap {beats2:.1f})')

# D
s = session('D', hold=0)
s.trig(0, note=48, length=60, t=0)
s.trig(8, note=48, length=60, t=0)
assert s.k.call(A(0x4004F8FE), [s.ctx0, 0, 65, 9 * (0 + 1)]) & 0xFF      # BLOOM -64 on step 1
fr = frames(s, int(14 * step16(120)))
a = [U16(fr[int(3 * step16(120))], 0x74 + 2 * v) for v in range(4)]
b = [U16(fr[int(11 * step16(120))], 0x74 + 2 * v) for v in range(4)]
check(sum(1 for x in a if x == 0) == 3 and len(set(b)) == 1 and b[0] > 0, f'D BLOOM lock on step 1: {a}; step 9: {b}')

# E
s = session('E', time=5, glid=5, hold=0, type=0, ext=0, drft=0, vib=0)     # C MAJ -> F# MAJ: no common note
s.trig(0, note=48, length=127, t=0)
s.trig(16, note=54, length=127, t=0)
bar = 16 * step16(120)
fr = frames(s, int(16 * step16(120) + bar + 300))
t0 = int(16 * step16(120)) + 2
seq = [[U16(f, 2 + 2 * v) for v in range(4)] for f in fr[t0:]]
land = []
for v in range(4):
    last = seq[-1][v]
    land.append(max(i for i, r in enumerate(seq) if r[v] != last) + 1)
order = sorted(range(4), key=lambda v: seq[-1][v])
ls = [land[v] for v in order]
# (a landing is the last block the note word changes: the glide's last stretch moves less than a word's 1/256
# semitone, so the top shows a few % early; the ratios are what DRON sets: 1 : 1.25 : 1.5 : 1.75 = 4 : 5 : 6 : 7)
check(ls == sorted(ls) and abs(ls[-1] - bar) < 0.07 * bar and all(abs(ls[i] / ls[-1] - (4 + i) / 7) < 0.03 for i in range(4)),
      f'E DRON: landings low to high {ls} (bar {bar:.0f}, lowest wants {bar / 1.75:.0f})')

# F
s = session('F', hold=0, type=2, ext=3, voic=90)
st = s.store()
h = s.k.h
old = bytearray(4 + 18 * 16 + 16)
old[0:4] = b'DGK1'
for t in range(16):
    old[4 + 18 * t + 7] = 0
vals = [2, 3, 5, 90, 70, 4, 1, 2, 3, 1, 2, 3, 4, 20, 10, 100, 3, 2]   # TYPE .. BASS, HOLD 2 = marked, OFF
for k, v in enumerate(vals):
    old[4 + 18 * 0 + k] = v
old[4 + 18 * 16 + 0] = 33 + 1                                           # SPD 33
h.w(st, bytes(old))
rd = lambda k: s.k.call(s.sym['dg_par'], [0, k]) >> 8
before = [rd(k) for k in range(19)]
s.k.call(s.sym['dg_par_set'], [0, K_BLOOM, 40 << 8])
after = [rd(k) for k in range(19)]
hdr = bytes(h.r(st, 4))
check(before == vals + [33] and after == before and hdr == b'DGK2' and rd(K_BLOOM) == 40 and rd(19) == 0,
      f'F DGK1 read {before == vals + [33]}, rewritten as {hdr}, kept {after == before}, BLOOM {rd(K_BLOOM)}')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
