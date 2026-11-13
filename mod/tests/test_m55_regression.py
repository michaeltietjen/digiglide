"""DigiGlide M5.5 (spec rev 3): regression against stock 1.11.

  1. Stock projects load unchanged: after boot (the demo project, saved on stock OS, loaded by each OS) the app object,
     the 16 live sounds and the playing pattern are byte-identical on DigiGlide and on stock.
  2. Non-DigiGlide tracks render identically to stock: the demo plays on every track while track 1 is a DigiGlide
     sound (VCNT 5) holding a chord progression; stock plays the same project with track 1 left stock. Both reserve 6
     voices for track 1, so the other 15 tracks get the same voices 6..15 on both OSes. Every frame's fields for voices
     6..15 (note, velocity, curve, level, machine, filter type, sound record, voice -> track, and their on / off bits)
     are byte-identical, the FX block too, and the SHARC renders with voices 0..5 silenced in both are bit-identical.
    ~/dn2-workspace/repos/digikit/.venv/bin/python test_m55_regression.py [DIGIGLIDE.syx]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, latest, G, U16, Ui
from osver import A
import dn2paths as P, dn2frame as D

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def state(s):
    h = s.k.h
    app = h.u32(A(0x446478D0)); snd = h.u32(A(0x800052A0)); pat = h.u32(A(0x42C5A9A0))
    return {'app object': bytes(h.r(app, 451596)), 'sounds': bytes(h.r(snd, 52 + 1163 * 16)),
            'pattern': bytes(h.r(pat, 131072))}


# 1. the stock project as each OS loads it (no edits: solo=False keeps the demo's trigs; the VOICE reservation is the
# only change and is the same on both)
a = Session(None, tag='m55_load', solo=False, reserve=0)
b = Session(img, tag='m55_load', solo=False, reserve=0)
for q in (a, b):                                        # let both settle: the snapshot is taken as soon as the
    q.k.h.frames(50); q.k.h.run(400_000_000)            # main screen shows, a little earlier or later in start-up
sa, sb = state(a), state(b)
for k in sa:
    diff = sum(1 for x, y in zip(sa[k], sb[k]) if x != y)
    check(diff == 0, f'1. {k} after loading the demo project: {diff} bytes differ from stock')

# 2. the other tracks while track 1 plays DigiGlide
N = 6000
runs = {}
for name, im in (('stock', None), ('digiglide', img)):
    s = Session(im, tag='m55_play', solo=False)          # track 1 reserves 6 voices on both
    if im:
        s.set_sound(Ui())
    else:
        s.k.select(1, track=0)
    for st in range(128):
        s.k.call(A(0x40054690), [s.ctx0, st, 1, 0])          # track 1: only our trigs
    for st, n in ((0, 60), (8, 65), (16, 67), (24, 62)):   # a chord every half bar: 4 keys in 6000 blocks
        s.trig(st, note=n, length=127)
    runs[name] = [bytes(f[:2688]) for f in s.play(N, bpm=120)]
    if im:
        dg_trigs = s.dg()['trigs']
check(dg_trigs >= 4, f'2. DigiGlide played on track 1 ({dg_trigs} trigs)')
fa, fb = runs['stock'], runs['digiglide']
OTHER = range(6, 16)
fields = [(0x02, 2), (0x34, 2), (0x54, 2), (0x74, 2), (0x94, 2), (0xB4, 2), (0xA5A, 2)]
bad = []
# the N frames played; the 4 after [STOP] are left out: when the UI task acts on the key (the stop's note-offs)
# is a frame earlier or later from run to run, on stock too (as the tempo word in render_m5.py)
for i, (x, y) in enumerate(zip(fa[:N], fb[:N])):
    for v in OTHER:
        for o, n in fields:
            if x[o + 2 * v:o + 2 * v + n] != y[o + 2 * v:o + 2 * v + n]:
                bad.append((i, v, hex(o)))
        if x[0xDA + 146 * v:0xDA + 146 * (v + 1)] != y[0xDA + 146 * v:0xDA + 146 * (v + 1)]:
            bad.append((i, v, 'record'))
    for o in (0x22, 0x24, 0x26, 0x28):
        if (U16(x, o) ^ U16(y, o)) & 0xFFC0:
            bad.append((i, 'mask', hex(o)))
    if x[0x9FA:0xA5A] != y[0x9FA:0xA5A]:
        bad.append((i, 'fx', None))
check(len(fa) == len(fb) and not bad, f'2. {N} frames played: voices 6..15 and the FX block byte-identical to stock'
                                      + (f' (first differences {bad[:4]})' if bad else ''))
played = sorted({U16(f, 0xA5A + 2 * v) for f in fa for v in OTHER if (U16(f, 0x22) >> v) & 1})
check(len(played) >= 3, f'2. other tracks played meanwhile: tracks {[t + 1 for t in played]}')


def silence_dg(frames):
    out = []
    for f in frames:
        f = bytearray(f)
        for o in (0x22, 0x26):
            f[o:o + 2] = (U16(f, o) & 0xFFC0).to_bytes(2, 'big')
        for v in range(6):
            f[0x74 + 2 * v:0x76 + 2 * v] = b'\0\0'          # level 0
        out.append(D.swap16(bytes(f)))
    return out


sec7, snap = P.snap('stock')
ra = D.render(D.Frame(D.image_from_sec7(sec7), snap), silence_dg(fa[:3000]))
rb = D.render(D.Frame(D.image_from_sec7(sec7), snap), silence_dg(fb[:3000]))
same = np.array_equal(np.asarray(ra[0]), np.asarray(rb[0])) and np.array_equal(np.asarray(ra[1]), np.asarray(rb[1]))
check(same, f'2. render of the other tracks (voices 0..5 silenced in both), 3000 blocks: bit-identical '
            f'(rms {float(np.sqrt(np.mean(np.asarray(ra[0], float) ** 2))):.4f})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
