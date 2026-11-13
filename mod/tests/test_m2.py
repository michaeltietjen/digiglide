"""M2: chord changes pick the minimum-movement assignment. C maj -> A min holds C and E and moves G to A, without
retriggering the held voices. Two trigs on track 1 (steps 1 and 5, LEN INF), progression [C3 maj, A2 min], GLID 1/4.
    ~/dn2-workspace/repos/digikit/.venv-fast/bin/python test_m2.py [GLIDE.syx]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glidekit import Session, latest, params, note_ons, note_offs, pitch_trace

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
s = Session(img, tag='m2')
s.trig(0); s.trig(4)
s.progression([params('C3', 'maj', glid='1/4', drft=0), params('A2', 'min', glid='1/4', drft=0)])
fr = s.play(1900, bpm=120)                       # a beat at 120 BPM = 750 blocks: trig 2 ~752, slide ~752..1502

ok = True
def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg)

ons = note_ons(fr, range(4))
blocks = sorted({i for i, *_ in ons})
check(len(blocks) == 1, f'GLIDE voices start only once (blocks {blocks}): the second trig does not retrigger')
first = {v: n for _, v, n, _ in ons}
check(sorted(first.values()) == [48, 52, 55], f'first chord C maj {sorted(first.values())}')
change = None
for v in first:
    tr = pitch_trace(fr, v)
    end = tr[-10]
    moved = [i for i in range(blocks[0] + 1, len(tr)) if tr[i] != tr[i - 1]]
    print(f'    voice {v}: {first[v]:5.1f} -> {end:5.2f}  (moved over blocks {moved[:1]}..{moved[-1:]})')
    if first[v] in (48, 52):
        check(end == first[v] and not moved, f'{["C", "E"][first[v] == 52]} holds at {first[v]}')
    else:
        check(end == 57, f'G slides to A (ends at {end})')
        if moved:
            change = (moved[0], moved[-1])
            seg = tr[moved[0] - 1:moved[-1] + 1]
            check(all(b >= a for a, b in zip(seg, seg[1:])), 'the slide only goes up (no overshoot)')
            check(abs((moved[-1] - moved[0]) - 750) < 40,
                  f'slide lasts ~1/4 note = 750 blocks at 120 BPM ({moved[-1] - moved[0]})')
offs = [o for o in note_offs(fr, range(4)) if o[0] < len(fr) - 6]
check(not offs, f'no note-offs on GLIDE voices while held {offs[:4]}')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
