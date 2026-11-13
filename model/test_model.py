"""M1 check: DigiGlide rules the Brickglide comparison can't cover (randomness, time, the spec's own rules).
    python3 test_model.py
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import digiglide as G  # noqa: E402

fails = []


def check(ok, what):
    print('  ok  ' if ok else '  FAIL', what)
    if not ok:
        fails.append(what)


P = G.Params(key=0, scl=1)                       # C minor, Seventh, VCNT 5, BASS root, GLID 1 bar
PROG = [P.copy(deg=d) for d in (0, 5, 3, 4)]     # i VI iv v
BAR = 3000


def same(a, b):
    return all(x == y or (x != x and y != y) for ra, rb in zip(a, b) for x, y in zip(ra, rb)) and len(a) == len(b)


def sounding(pitch, gate, b):
    return [round(pitch[b][i] / 100.0, 2) for i in range(6) if gate[b][i]]


# first trig: chord stacked from the bass, bass root in 36..47
ev, nb = G.progression(PROG, 2)
pitch, gate, pan, lvl, m = G.run(ev, nb)
p0 = G.DigiGlide()
first = [round(c / 100) for c in sorted(pitch[1][i] for i in range(5))]
check(first == [36, 43, 46, 55, 60],
      f'first chord Cm7 voice-led up from Brickglide\'s default notes, bass C2 (MIDI 36): {first}')
check(all(gate[1][i] for i in range(5)) and not gate[1][5], 'VCNT 5, BASS root: 5 voices on, no sub')

# repeatability
pitch2 = G.run(ev, nb)[0]
check(same(pitch, pitch2), 'two runs are identical (seeded drift)')

# no jumps while gliding: per-block pitch steps stay small (Smooth 1 bar over a few semitones)
mx = max(abs(pitch[b][i] - pitch[b - 1][i]) for b in range(2, nb) for i in range(5) if gate[b][i] and gate[b - 1][i])
check(mx < 8.0, f'largest per-block step while sounding: {mx:.2f} cents (< 8)')

# every glide lands on the voice-led chord
for k in range(1, 4):
    b = (k * 2 + 1) * BAR + BAR // 2           # 1.5 bars after the trig, the 1-bar glide is over
    notes = sorted(m_ for m_ in (round(pitch[b][i] / 100) for i in range(5)))
    root_pc, pcs = G.chord_tones(0, 1, PROG[k].deg, 1)
    off = max(abs(pitch[b][i] / 100 - round(pitch[b][i] / 100)) for i in range(5))
    check(all(n % 12 in pcs for n in notes) and notes[0] % 12 == root_pc and 36 <= notes[0] <= 47 and off < 0.13,
          f'chord {k + 1} ({G.ROMAN[PROG[k].deg]}7) lands on chord tones {notes}, bass root, within drift+vib ({off * 100:.1f} c)')

# mid-glide chord change: no jump
ev = {0: [('trig', 0, P.copy(deg=0, glid=6))], BAR: [('trig', 16, P.copy(deg=5, glid=6))],
      int(BAR * 1.5): [('trig', 24, P.copy(deg=3, glid=6))], 5 * BAR: [('off',)]}
pitch = G.run(ev, 6 * BAR)[0]
b = int(BAR * 1.5)
mx = max(abs(pitch[b][i] - pitch[b - 1][i]) for i in range(5))
check(mx < 3.0, f'new chord mid-glide starts from the current pitch (step at the change {mx:.2f} cents)')

# GLID 0: hard change
ev = {0: [('trig', 0, P.copy(deg=0, glid=0, drft=0, vib=0))], BAR: [('trig', 16, P.copy(deg=5, glid=0, drft=0, vib=0))],
      2 * BAR: [('off',)]}
pitch = G.run(ev, 2 * BAR + 10)[0]
check(all(abs(pitch[BAR][i] / 100 - round(pitch[BAR][i] / 100)) < 1e-9 for i in range(5)) and
      any(abs(pitch[BAR][i] - pitch[BAR - 1][i]) >= 100 for i in range(5)), 'GLID 0: hard change in one block')

# released voices: next trig lays out fresh (jump, no glide)
ev = {0: [('trig', 0, P.copy(deg=0))], BAR: [('off',)], 2 * BAR: [('trig', 32, P.copy(deg=5))], 3 * BAR: [('off',)]}
pitch, gate = G.run(ev, 3 * BAR)[:2]
check(all(abs(pitch[2 * BAR][i] - round(pitch[2 * BAR][i] / 100) * 100) < 15 for i in range(5)),
      'trig after release: fresh layout, voices already on the new chord in its first block')

# sub: an octave under the bass, follows it
ev, nb = G.progression([p.copy(bass=2) for p in PROG], 2)
pitch, gate = G.run(ev, nb)[:2]
ok = True
for b in (BAR // 2, 3 * BAR, 5 * BAR + BAR // 2, 7 * BAR + 1500):
    bass = min(pitch[b][i] for i in range(4))
    ok &= abs(pitch[b][4] - (round(bass / 100) * 100 - 1200)) < 60 and gate[b][4]
check(ok, 'BASS root+sub: VCNT 5 = 4 drones + sub, the sub sits an octave under the bass and follows it')

# moves: repeatable, land on the chord, Bloom passes the lowest target
for mv in range(1, 10):
    ev, nb = G.progression([PROG[0].copy(drft=0, vib=0)] + [p.copy(move=mv, drft=0, vib=0) for p in PROG[1:]], 3)
    a = G.run(ev, nb)[0]
    b2 = G.run(ev, nb)[0]
    b = 6 * BAR - 1
    landed = all(abs(a[b][i] / 100 - round(a[b][i] / 100)) < 1e-6 for i in range(5))
    check(same(a, b2) and landed, f'MOVE {G.MOVES[mv]}: repeatable, voices settled on whole notes before the next chord')

# EVOL: every voice moves to a nearby scale note
ev = {0: [('trig', 0, P.copy(deg=0, drft=0, vib=0))], BAR * 2: [('trig', 32, P.copy(move=G.EVOL, drft=0, vib=0))],
      BAR * 6: [('off',)]}
pitch = G.run(ev, BAR * 6)[0]
before = [round(pitch[2 * BAR - 1][i] / 100) for i in range(5)]
after = [round(pitch[6 * BAR - 1][i] / 100) for i in range(5)]
minor = {0, 2, 3, 5, 7, 8, 10}
check(all(0 < abs(a - b) <= 5 and a % 12 in minor for a, b in zip(after, before)),
      f'EVOL: {before} -> {after}, each within 5 semitones, in C minor')

# different steps give different random choices (seed includes the step)
ev1 = {0: [('trig', 0, P.copy(deg=0, drft=0, vib=0))], BAR: [('trig', 16, P.copy(move=G.EVOL, drft=0, vib=0))]}
ev2 = {0: [('trig', 0, P.copy(deg=0, drft=0, vib=0))], BAR: [('trig', 20, P.copy(move=G.EVOL, drft=0, vib=0))]}
a, b = G.run(ev1, 4 * BAR)[0][-1], G.run(ev2, 4 * BAR)[0][-1]
check(a != b, 'EVOL on another step chooses differently (seed = pattern, step, voice)')

# SCRB: halfway holds the voices halfway along their (Linear) path
ev = {0: [('trig', 0, P.copy(deg=0, drft=0, vib=0, path=1))],
      BAR: [('trig', 16, P.copy(deg=5, drft=0, vib=0, path=1, scrb=64))]}
pitch = G.run(ev, 4 * BAR)[0]
frm = [pitch[BAR - 1][i] for i in range(5)]
to = G.run({0: ev[0], BAR: [('trig', 16, P.copy(deg=5, drft=0, vib=0, path=1))]}, 4 * BAR)[0][-1]
frac = [(pitch[-1][i] - frm[i]) / (to[i] - frm[i]) for i in range(5) if abs(to[i] - frm[i]) > 50]
check(frac and all(abs(f - 64 / 127) < 0.01 for f in frac), f'SCRB 64: voices hold {[round(f, 3) for f in frac]} of the way')

# vibrato and drift sizes
ev = {0: [('trig', 0, P.copy(deg=0, drft=0, vib=20))]}
pitch = G.run(ev, 20 * 1500)[0]
dev = max(abs(pitch[b][1] - 4300) for b in range(len(pitch)))
check(19.0 < dev <= 20.0001, f'VIB 20: voice 2 swings +-{dev:.2f} cents around G2')
ev = {0: [('trig', 0, P.copy(deg=0, drft=30, vib=0))]}
pitch = G.run(ev, 60 * 1500)[0]
dev = [max(abs(pitch[b][i] - round(pitch[b][i] / 100) * 100) for b in range(len(pitch))) for i in range(5)]
check(all(5 < d <= 30.0001 for d in dev), f'DRFT 30: largest drift per voice over 60 s {[round(d, 1) for d in dev]} cents (<= 30)')

print('FAIL' if fails else 'OK', f'({len(fails)} failures)')
sys.exit(1 if fails else 0)
