"""DigiGlide build 23: bass patterns (BPAT, BRATE) on the bass voice. A held chord (HOLD on, 5 voices, BASS FOL: the
bass voice is engine voice 4), trigs as each case says.
  A  every pattern at 1/8, 120 BPM, C MIN7: the notes (intervals from the root), the grid, 80 % gates, a pluck
     (RSET 256) at every note, odd steps' level word at 80 % of even steps' (Offbeat: all full)
  B  WALK's fifth is the chord's own: C DIM (6), C MAJ (7)
  C  the grid at 90 and 140 BPM and at 1/4 and 1/16
  D  a new root restarts the pattern at step 0; a trig on the same root goes on with it
  E  a BPAT lock on a step (lane 65): that trig plays the locked pattern, the next unlocked trig the track's
  F  BPAT HOLD: the bass voice is struck once and held, as image 22 (one note-on, RSET 0)
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b23_bass.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
K_TYPE, K_BPAT, K_BRATE = 0, 19, 20
BV = 4
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def run(tag, bpat, brate=1, bpm=120, typ=1, trigs=((0, 48),), length=30, blocks=2400, locks=()):
    s = Session(img, tag='b23b' + tag, solo=True)
    s.set_sound(Ui(vcnt=5, type=typ, ext=2 if typ == 1 else 0, glid=3, voic=64, bass=3, hold=1), t=0, mach=None,
                atk=None)
    s.k.call(s.sym['dg_par_set'], [0, K_BPAT, bpat << 8])
    s.k.call(s.sym['dg_par_set'], [0, K_BRATE, brate << 8])
    for st, n in trigs:
        s.trig(st, note=n, length=length, t=0)
    for st, word in locks:
        assert s.k.call(A(0x4004F8FE), [s.ctx0, st, 65, word]) & 0xFF
    fr = s.play(blocks, bpm=bpm)
    ons, offs = [], []
    for b, f in enumerate(fr):
        if U16(f, 0x22) >> BV & 1:
            ons.append((b, (U16(f, 2 + 2 * BV) + 128) >> 8, U16(f, 0xDA + 146 * BV + 134), U16(f, 0x74 + 2 * BV)))
        if U16(f, 0x24) >> BV & 1:
            offs.append(b)
    return ons, offs


def step_blocks(bpm, brate):
    return 2700000 * (4 >> brate) / (bpm * 120)


PAT = {1: [0] * 6, 2: [0, 12] * 3, 3: [0, 0, 7, 12, 0, 0], 4: [0, 7] * 3, 5: [0, 3, 7, 3, 0, 3],
       6: [None, 0] * 3, 7: [0, None, None, 0, None, None, 0, None]}
NAMES = ['HOLD', 'PULS', 'OCT', 'WALK', 'R-5', 'ARP', 'OFFB', '332']
L = step_blocks(120, 1)                                 # 375 blocks
for bp in range(1, 8):
    ons, offs = run(f'A{bp}', bp, blocks=3200)
    root = ons[0][1] if ons else 0
    want = [(k, iv) for k, iv in enumerate(PAT[bp]) if iv is not None]
    got = [(round((b - ons[0][0]) / L) + (1 if bp == 6 else 0), n - root) for b, n, _, _ in ons]
    # (Offbeat's first note is on step 1: its own start is the reference, one step in)
    good_notes = got[:len(want)] == want if bp != 6 else [iv for _, iv in got[:3]] == [0, 0, 0]
    on_grid = all(abs((b - ons[0][0]) - round((b - ons[0][0]) / L) * L) <= 1 for b, *_ in ons)
    gates = [o - b for (b, *_), o in zip(ons, offs)]
    good_gate = gates and all(abs(g - 0.8 * L) <= 2 for g in gates[1:4])
    pluck = all(r == 256 for _, _, r, _ in ons)
    lv = {}
    for b, n, r, w in ons[1:]:
        lv.setdefault(round((b - ons[0][0]) / L) % 2, set()).add(w)
    if bp == 6:
        acc = len(lv) == 1
    else:
        acc = 0 in lv and 1 in lv and all(abs(o / e - 0.8) < 0.01 for o in lv[1] for e in lv[0])
    check(good_notes and on_grid and good_gate and pluck and acc,
          f'A {NAMES[bp]:4s}: {got[:8]}  gates {gates[1:4]}  levels {sorted((k, sorted(v)) for k, v in lv.items())}')

for typ, name, fifth in ((3, 'DIM', 6), (0, 'MAJ', 7)):
    ons, _ = run('B' + name, 3, typ=typ)
    ivs = [n - ons[0][1] for _, n, _, _ in ons[:4]]
    check(ivs == [0, 0, fifth, 12], f'B WALK on C {name}: {ivs}')

for bpm, brate in ((90, 1), (140, 1), (120, 0), (120, 2)):
    ons, _ = run(f'C{bpm}_{brate}', 1, brate=brate, bpm=bpm, blocks=3000)
    gaps = [ons[i + 1][0] - ons[i][0] for i in range(len(ons) - 1)]
    want = step_blocks(bpm, brate)
    check(len(gaps) >= 3 and all(abs(g - want) <= 1 for g in gaps),
          f'C PULS {bpm} BPM {["1/4", "1/8", "1/16"][brate]}: gaps {gaps[:5]} (want {want:.1f})')

ons, _ = run('D', 3, trigs=((0, 48), (6, 48), (12, 53)), length=127, blocks=3400)
step16 = 2700000 / 14400
seq = [(round(b / L), n) for b, n, _, _ in ons]
t2 = [n for b, n, _, _ in ons if b >= 12 * step16 - 2][:4]
t1 = [n for b, n, _, _ in ons if 6 * step16 - 2 <= b < 12 * step16 - 2]
check(t2 and [n - t2[0] for n in t2] == [0, 0, 7, 12] and t2[0] == 53 and t1[:3] == [60, 48, 48],
      f'D same root goes on {t1[:3]}, new root restarts {[n - t2[0] for n in t2] if t2 else t2}')

ons, _ = run('E', 0, trigs=((0, 48), (8, 48)), length=60, blocks=3000, locks=((0, 2 + 1),))
first = [n for b, n, _, _ in ons if b < 8 * step16 - 2]
second = [n for b, n, _, _ in ons if b >= 8 * step16 - 2]
check(len(first) >= 3 and len(set(first)) == 2 and len(second) == 1,
      f'E BPAT OCT locked on step 1: {first}; step 9 unlocked (HOLD): {second}')

ons, offs = run('F', 0, blocks=2000)
check(len(ons) == 1 and ons[0][2] == 0, f'F BPAT HOLD: {len(ons)} note-on, RSET {ons[0][2] if ons else None}')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
