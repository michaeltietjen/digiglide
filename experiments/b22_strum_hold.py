"""Image 21 on the unit: STRM / STRU "just hold notes over the top". Dumps every voice's note-on / note-off timeline
(all 16 voices, not only DigiGlide's block) for CHRD, STRM and STRU at a few trig lengths, to see what keeps sounding.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b22_strum_hold.py IMAGE.syx"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mod', 'tests'))
from dgkit import Session, Ui, U16

img = sys.argv[1]
STEPS = [(0, 48), (4, 53), (8, 55), (12, 50)]
for play in [int(a) for a in sys.argv[2].split(',')] if len(sys.argv) > 2 else (0, 1):
    for length in [int(a) for a in sys.argv[3].split(',')] if len(sys.argv) > 3 else (30, 127):
        s = Session(img, tag=f'b22_{play}_{length}', solo=True)
        s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, pos=64, voic=64, play=play), t=0, mach=None, atk=None)
        for st, n in STEPS:
            s.trig(st, note=n, length=length, t=0)
        fr = s.play(3000, bpm=120)
        ev = []
        for b, f in enumerate(fr):
            on, off = U16(f, 0x22), U16(f, 0x24)
            for v in range(16):
                if on >> v & 1:
                    ev.append((b, v, 'on', (U16(f, 2 + 2 * v) + 128) >> 8))
                if off >> v & 1:
                    ev.append((b, v, 'off', None))
        print(f'== play {play} length {length}  dg {s.dg()["base"] if "base" in s.dg() else ""}')
        for e in ev:
            print('  ', e)
