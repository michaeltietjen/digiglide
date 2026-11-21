"""Owner, 2026-11-16 (image 25): "strum down still doesn't work with chord hold on", "a ring going on that's holding
over"; all trigs, VCNT 6, BASS off. Trigs C3 F3 G3 D3 on steps 1, 5, 9, 13, HOLD on. Per trig: the note-ons (block
after the trig, voice, note, RSET of the voice record) and the voices that got none (they ring on from the last chord).
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b26_strum_seq6.py IMAGE.syx PLAY VCNT LENGTH GLID [TYPE EXT]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16

img, play, vcnt, length, glid = sys.argv[1], *map(int, sys.argv[2:6])
typ, ext = (int(sys.argv[6]), int(sys.argv[7])) if len(sys.argv) > 7 else (1, 2)
s = Session(img, tag=f'ss_{play}{vcnt}{length}{glid}{typ}{ext}', solo=True)
s.set_sound(Ui(vcnt=vcnt, type=typ, ext=ext, glid=glid, pos=64, voic=64, play=play, hold=1, bass=0, drft=0, vib=0), t=0, mach=None, atk=None)
STEPS = [(0, 48), (4, 53), (8, 55), (12, 50)]
for st, n in STEPS:
    s.trig(st, note=n, length=length, t=0)
fr = s.play(3000, bpm=120)
tag = f'PLAY {["CHRD", "STRM", "STRU", "HARP"][play]} VCNT {vcnt} len {length} GLID {glid} TYPE {typ} EXT {ext}'
for i in range(4):
    lo, hi = 187 * 4 * i, 187 * 4 * (i + 1)
    ons = [(b - lo, v, (U16(f, 2 + 2 * v) + 128) >> 8, U16(f, 0xda + 146 * v + 0) ) for b, f in enumerate(fr[lo:hi], lo) for v in range(16) if U16(f, 0x22) >> v & 1]
    end = fr[hi - 1]
    pitches = [(U16(end, 2 + 2 * v) + 128) >> 8 for v in range(vcnt)]
    missing = sorted(set(range(vcnt)) - {v for _, v, _, _ in ons})
    print(f'{tag}: trig {i + 1}: {len(ons)} note-ons {[(b, v, n) for b, v, n, _ in ons]}; voices not struck {missing}; '
          f'pitches at the end {pitches}; offs {sum(1 for f in fr[lo:hi] if U16(f, 0x24))}', flush=True)
