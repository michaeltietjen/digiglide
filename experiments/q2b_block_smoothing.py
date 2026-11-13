"""M0 wrap-up, open part of question 2: does the DSP ramp a note-word change inside its 32-sample block, or step it?

One WAVETONE voice reduced to a near-pure sine (osc 1 only, osc 2 / noise / drift off, filter open). After the note-on the
note word jumps without a note-on at block B (and, in a second case, by +25 cents, the size of the fastest glides' per-block
moves). Pitch is measured per sample with a sliding 8-sample sine fit: for a sine, x[n-1] + x[n+1] = 2 cos(w) x[n].
    python3 q2b_block_smoothing.py
"""
import math, os, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
import dn2paths as P
import dn2frame as D, dn2synth as S

OUT = os.path.expanduser('~/glide/experiments/out')
B = 200                                       # block of the jump (well after the attack)
CASES = {'octave': (72 << 8, 84 << 8), 'cents25': (72 << 8, (72 << 8) + 64)}


def sound():
    s = S.Sound('WAVETONE')
    for k, v in (('LEV2', 0), ('NLEV', 0), ('DRIF', 0), ('FREQ', 127), ('RESO', 0), ('ATK', 0), ('SUS', 127)):
        s.set(k, v)
    return s


def build(w0, w1, n):
    song = S.Song().assign(0, sound()).track(0, 0).note(2, 0, 72, 110)
    out = []
    for k, f in enumerate(song.frames(n)):
        f = bytearray(D.swap16(f))
        f[2:4] = (w1 if k >= B else w0).to_bytes(2, 'big')
        out.append(D.swap16(bytes(f)))
    return out


def track_midi(x, win=8, fs=48000):
    x = np.asarray(x, float)
    num = x[1:-1] * (x[:-2] + x[2:])
    den = 2 * x[1:-1] ** 2
    k = np.ones(win)
    c = np.clip(np.convolve(num, k, 'same') / np.maximum(np.convolve(den, k, 'same'), 1e-30), -1, 1)
    f = np.arccos(c) * fs / (2 * math.pi)
    m = 69 + 12 * np.log2(np.maximum(f, 1) / 440)
    return np.concatenate([[m[0]], m, [m[-1]]])


sec7, snap = P.snap('stock')
for name, (w0, w1) in CASES.items():
    cache = os.path.join(OUT, f'q2b_{name}.npz')
    if os.path.exists(cache):
        z = np.load(cache); L = z['L']
    else:
        L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), build(w0, w1, B + 40))
        np.savez(cache, L=L, R=R); D.write_wav(cache[:-4] + '.wav', L, R)
    m = track_midi(L)
    e = B * 32
    print(f'\n{name}: word {w0 / 256:.2f} -> {w1 / 256:.2f} sent in block {B} (samples {e}..{e + 31})')
    print('  steady before:', round(float(np.median(m[e - 600:e - 100])), 3), ' steady after:', round(float(np.median(m[e + 400:e + 1000])), 3))
    for b in range(B - 2, B + 6):
        seg = m[b * 32:(b + 1) * 32]
        print(f'  block {b:4d}: ' + ' '.join(f'{v:6.2f}' for v in seg[::4]))
