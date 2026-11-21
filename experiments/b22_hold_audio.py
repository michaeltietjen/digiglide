"""Image 21 on the unit: with HOLD on, STRM / STRU "just hold notes over the top". Renders the OS's frames through
the SHARC emulator: HOLD on, TYPE MIN EXT 7, 4 voices, trigs C3 F3 G3 D3 on steps 1 5 9 13, the sound's AMP ATK.
Prints each string's note-on (block, voice, note, the record's RSET word) and the level just before and after
each string's turn (5 ms windows): a strum that plucks dips and rises again; one that does not is flat.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b22_hold_audio.py IMAGE.syx PLAY HOLD [LEN]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, U16, Ui
import dn2paths as P, dn2frame as D

img, play, hold = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
length = int(sys.argv[4]) if len(sys.argv) > 4 else 30
STEPS = [(0, 48), (4, 53), (8, 55), (12, 50)]
s = Session(img, tag=f'b22a_{play}_{hold}', solo=True)
s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, pos=64, voic=64, play=play, hold=hold), t=0, mach=None, atk=None)
for st, n in STEPS:
    s.trig(st, note=n, length=length, t=0)
fr = s.play(3200, bpm=120)[:3200]
ons, offs = [], []
for b, f in enumerate(fr):
    on, off = U16(f, 0x22), U16(f, 0x24)
    for v in range(16):
        if on >> v & 1:
            ons.append((b, v, (U16(f, 2 + 2 * v) + 128) >> 8, U16(f, 0xDA + 146 * v + 134)))
        if off >> v & 1:
            offs.append((b, v))
if os.environ.get('ATKF'):                              # AMP ATK straight into every voice record (a slot set
    o = [0xDA + 146 * v + 2 * (81 - 25) for v in range(16)]   # from here does not reach the frame)
    fr2 = []
    for f in fr:
        f = bytearray(f)
        for a in o:
            f[a:a + 2] = (int(os.environ['ATKF']) << 8).to_bytes(2, 'big')
        fr2.append(bytes(f))
    fr = fr2
sec7, snap = P.snap('stock')
L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), [D.swap16(bytes(f)) for f in fr])
x = (np.asarray(L, float) + np.asarray(R, float)) / 2
spb = len(x) // len(fr)
db = lambda a, b: 20 * np.log10(max(float(np.sqrt(np.mean(x[a * spb:b * spb] ** 2))), 1e-9))
print(f'play {play} hold {hold} len {length}: {len(ons)} note-ons, {len(offs)} note-offs')
for b, v, n, rs in ons:
    print(f'  block {b:5d} voice {v:2d} note {n:3d} RSET {rs:3d}   before {db(b - 8, b):6.1f} dB  after +5ms {db(b + 2, b + 10):6.1f}  +20ms {db(b + 25, b + 35):6.1f}')
print('  offs', offs[:24])
np.save(os.path.expanduser(f'~/glide/experiments/out/b22_{os.path.basename(img)[:-4]}_{play}_{hold}_{os.environ.get("ATKF", "")}.npy'), x.astype(np.float32))
