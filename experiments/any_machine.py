"""DigiGlide chords with another machine's voices, as the unit plays them while a sound is previewed on a DigiGlide
track: DigiGlide's own frames (notes, gates, glides, on a WAVETONE track) with every chord voice's sound record and
machine word replaced by a stock sound's of machine M (taken from the stock OS playing one note of it), rendered in
the SHARC emulator. The control is the stock OS playing the same machine's single note.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python any_machine.py IMAGE.syx M     (0 FM TONE, 1 WAVETONE, 2 FM DRUM, 3 SWARMER)"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, U16, Ui
import dn2paths as P, dn2frame as D

img, m = sys.argv[1], int(sys.argv[2])
NAME = ['FM TONE', 'WAVETONE', 'FM DRUM', 'SWARMER'][m]
TRIGS = ((2, 64), (10, 59), (18, 55))
HOLD = int(sys.argv[3]) if len(sys.argv) > 3 else 1

st = Session(None, tag=f'am_stock{m}', solo=True, reserve=0)
machs = [st.k.mach(t) for t in range(16)]
print('RES', NAME, 'demo project machines by track:', machs, flush=True)
tr = machs.index(m) if m in machs else 0
if m not in machs and not st.k.select(m, track=0):
    # the MACHINE menu did not get there in the emulator: the machine byte itself (the sound's other values stay as
    # they were, so this is that machine with an arbitrary patch, not a factory sound)
    st.k.h.w(st.k.sound(0) + 0xDE, bytes([m]))
    print('RES', NAME, 'machine byte written directly (arbitrary patch)', flush=True)
for step, n in TRIGS:
    st.trig(step, note=n, length=6, t=tr)
sf = st.play(3000, bpm=120)
i0 = next(i for i, f in enumerate(sf) if any(U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) == tr for v in range(16)))
v0 = next(v for v in range(16) if U16(sf[i0], 0x22) >> v & 1 and U16(sf[i0], 0xA5A + 2 * v) == tr)
rec = bytes(sf[i0][0xDA + 146 * v0:0xDA + 146 * v0 + 146])
words = {o: bytes(sf[i0][o + 2 * v0:o + 2 * v0 + 2]) for o in (0x54, 0x74, 0x94)}
print('RES', NAME, 'stock: voice', v0, 'machine word', U16(sf[i0], 0x94 + 2 * v0), 'note-ons', [(i, f'{U16(f, 0x22):04x}') for i, f in enumerate(sf) if U16(f, 0x22)], flush=True)

s = Session(img, tag=f'am_dg{m}', solo=True, reserve=0)
s.set_sound(Ui(vcnt=5, voic=64, glid=3, drft=0, vib=0, hold=HOLD))
for _ in range(3):
    s.k.tap('SYN')
for step, n in TRIGS:
    s.trig(step, note=n, length=6)
fr = s.play(3000, bpm=120)
ctl = 0
out = []
for f in fr:
    ctl |= U16(f, 0x22)
    f = bytearray(f)
    for v in range(16):
        if ctl >> v & 1:
            o = 0xDA + 146 * v
            keep = bytes(f[o + 128:o + 130]), bytes(f[o + 134:o + 136])       # DigiGlide's own pan and AMP RSET words
            f[o:o + 146] = rec
            f[o + 128:o + 130], f[o + 134:o + 136] = keep
            for w, b in words.items():
                f[w + 2 * v:w + 2 * v + 2] = b
    out.append(bytes(f))
ons = [(i, bin(U16(f, 0x22)).count('1')) for i, f in enumerate(fr) if U16(f, 0x22)]
offs = [(i, bin(U16(f, 0x24)).count('1')) for i, f in enumerate(fr) if U16(f, 0x24)]
vs = [v for v in range(16) if ctl >> v & 1]
print('RES', NAME, 'HOLD', HOLD, 'DigiGlide: chord voices', vs, 'note-ons (block, voices)', ons, 'note-offs', offs)
for a, b in zip(ons, ons[1:] + [(len(fr), 0)]):
    seg = fr[a[0]:b[0]]
    mv = sum(1 for x, y in zip(seg, seg[1:]) if any(U16(x, 2 + 2 * v) != U16(y, 2 + 2 * v) for v in vs))
    print('RES', NAME, f'  after block {a[0]}: pitch moves in {mv} blocks;', ' '.join(f'{U16(seg[0], 2 + 2 * v) / 256:.1f}>{U16(seg[-1], 2 + 2 * v) / 256:.1f}' for v in vs))
sec7, snap = P.snap('stock')


def rms(frames):
    L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), [D.swap16(bytes(f)) for f in frames])
    x = (np.asarray(L, float) + np.asarray(R, float)) / 2
    w = len(x) // 30
    return [float(np.sqrt(np.mean(x[i:i + w] ** 2))) for i in range(0, len(x) - w + 1, w)], float(np.max(np.abs(x))), bool(np.all(np.isfinite(x)))


a, pk, fin = rms(out)
print('RES', NAME, 'chords, rms per 100 ms:', ' '.join(f'{x:.4f}' for x in a), '| peak', round(pk, 4), 'finite', fin)
b, pk, fin = rms(sf)
print('RES', NAME, 'stock single notes:   ', ' '.join(f'{x:.4f}' for x in b), '| peak', round(pk, 4), 'finite', fin)
