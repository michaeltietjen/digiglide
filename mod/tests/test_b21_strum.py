"""DigiGlide build 21: STRM / STRU as a player uses them. Trigs C3, F3, G3, D3 on steps 1, 5, 9, 13 (TYPE MIN, EXT 7,
4 voices, GLID 1/4). Through image 20 a trig that overlapped the last was not struck (glided in), and with HOLD on
each strum played the previous chord. Every case: each trig gives 4 note-ons 20 blocks apart, in pitch order, all
in that trig's own chord (C, F, G, D minor 7).
  A  trig length 30 (gaps), B  length 127 (legato), C  HOLD on, D  GLID 0 legato; STRM and STRU each.
  E  HARP legato: a run on every trig, in that trig's chord.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b21_strum.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
STEPS = [(0, 48), (4, 53), (8, 55), (12, 50)]
MIN7 = {0, 3, 7, 10}


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def run(tag, play, length, **kw):
    s = Session(img, tag=tag, solo=True)
    p = dict(vcnt=4, type=1, ext=2, glid=3, pos=64, voic=64, play=play); p.update(kw)
    s.set_sound(Ui(**p), t=0, mach=None, atk=None)
    for st, n in STEPS:
        s.trig(st, note=n, length=length, t=0)
    fr = s.play(3000, bpm=120)
    ons = []
    for b, f in enumerate(fr):
        on = U16(f, 0x22)
        for v in range(16):
            if on >> v & 1:
                ons.append((b, (U16(f, 2 + 2 * v) + 128) >> 8))
    by = [[o for o in ons if 187 * 4 * i <= o[0] < 187 * 4 * (i + 1)] for i in range(4)]   # by trig (a step = 187)
    return by


for name, length, kw in [('A len 30', 30, {}), ('B legato', 127, {}), ('C hold on', 30, dict(hold=1)),
                         ('D glid 0', 127, dict(glid=0))]:
    for play, pname in ((1, 'STRM'), (2, 'STRU')):
        by = run('b21s' + name[0] + str(play), play, length, **kw)
        good = True
        for (st, root), ons in zip(STEPS, by):
            notes = [n for _, n in ons]
            gaps = [ons[i + 1][0] - ons[i][0] for i in range(len(ons) - 1)]
            order = sorted(notes) if play == 1 else sorted(notes, reverse=True)
            good &= len(ons) == 4 and gaps == [20, 20, 20] and notes == order and \
                {(n - root) % 12 for n in notes} <= MIN7
        check(good, f'{name} {pname}: {[[n for _, n in o] for o in by]} at {[o[0][0] if o else None for o in by]}')

by = run('b21sE', 3, 127)
good = all(len(o) >= 8 and {(n - r) % 12 for _, n in o} <= MIN7 for (st, r), o in zip(STEPS, by))
check(good, f'E HARP legato: notes a trig {[len(o) for o in by]}, each in its chord')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
