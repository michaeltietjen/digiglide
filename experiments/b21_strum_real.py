"""Build 21: STRM/STRU in the ways a player uses them: trigs back to back (length 127, legato), HOLD on, GLID 0,
and long trigs with a gap. Prints each trig's note-on blocks and notes."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest, Ui, U16
img = sys.argv[1] if len(sys.argv) > 1 else latest()

def run(tag, play, steps, length, **kw):
    s = Session(img, tag=tag, solo=True)
    p = dict(vcnt=4, type=1, ext=2, glid=3, pos=64, voic=64, play=play); p.update(kw)
    s.set_sound(Ui(**p), t=0, mach=None, atk=None)
    for st, n in steps:
        s.trig(st, note=n, length=length, t=0)
    fr = s.play(3000, bpm=120)
    ons = []
    for b, f in enumerate(fr):
        on = U16(f, 0x22)
        for v in range(16):
            if on >> v & 1:
                ons.append((b, (U16(f, 2 + 2 * v) + 128) >> 8))
    return ons

steps = [(0, 48), (4, 53), (8, 55), (12, 50)]
for name, length, kw in [('short 30', 30, {}), ('legato 127', 127, {}), ('length 60', 60, {}),
                         ('hold on', 30, dict(hold=1)), ('glid 0 legato', 127, dict(glid=0))]:
    for play in (1, 2):
        ons = run('b21' + name.replace(' ', '') + str(play), play, steps, length, **kw)
        print(f'{name:14} play {play}: {ons[:20]}', flush=True)
