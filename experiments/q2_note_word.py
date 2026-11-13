"""Open question 2: does the DSP follow the per-voice note word (+0x02+2v, note << 8) on every block,
including its fractional low byte, without a new note-on? If yes, GLIDE's slides need no SHARC code.

One voice holds a note-on at C4 (60). Without any further note-on, the note word is then set to
60 + 0.5 (fractional byte 0x80), then 67 (G4), then ramped 67 -> 69 over 64 blocks.
Measures pitch per segment by autocorrelation. Control: the same segments rendered with no word change.
    python3 q2_note_word.py
"""
import math, os, sys
SK = os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts')
sys.path.insert(0, SK)
import numpy as np
import dn2paths as P
import dn2frame as D, dn2synth as S

SEG = 64                                        # blocks per segment (~43 ms)
PLAN = [(60, 0), (60, 0x80), (67, 0), ('ramp', None)]


def pitch(x, fs=48000):
    x = np.asarray(x) - np.mean(x)
    c = np.correlate(x, x, 'full')[len(x) - 1:]
    lo, hi = int(fs / 1000), int(fs / 150)
    lag = lo + int(np.argmax(c[lo:hi]))
    if 1 <= lag < len(c) - 1:                   # parabolic refinement
        a, b, d = c[lag - 1], c[lag], c[lag + 1]
        lag = lag + 0.5 * (a - d) / (a - 2 * b + d)
    return fs / lag


def midi(f):
    return 69 + 12 * math.log2(f / 440.0)


def build(change):
    song = S.Song().assign(0, S.Sound('WAVETONE')).track(0, 0).note(2, 0, 60, 110)
    fr = song.frames(2 + SEG * len(PLAN))
    out = []
    for k, f in enumerate(fr):
        f = bytearray(D.swap16(f))              # back to ColdFire view to edit
        seg = max(0, (k - 2)) // SEG
        if change and k >= 2 + SEG:
            n, fine = PLAN[min(seg, len(PLAN) - 1)]
            if n == 'ramp':
                t = ((k - 2) - SEG * seg) / SEG
                w = int(round((67 + 2 * t) * 256))
            else:
                w = n << 8 | fine
            f[2:4] = w.to_bytes(2, 'big')
        out.append(D.swap16(bytes(f)))
    return out


sec7, snap = P.snap('stock')
res = {}
for name, change in (('control', False), ('note-word', True)):
    wav = os.path.expanduser(f'~/glide/experiments/out/q2_{name}.npz')
    os.makedirs(os.path.dirname(wav), exist_ok=True)
    if os.path.exists(wav):
        z = np.load(wav); L, R = z['L'], z['R']
    else:
        L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), build(change))
        np.savez(wav, L=L, R=R)
        D.write_wav(wav[:-4] + '.wav', L, R)
    mono = (np.array(L) + np.array(R)) / 2
    rows = []
    for s in range(len(PLAN)):
        a = (2 + SEG * s) * 32
        if PLAN[s][0] == 'ramp':
            q = SEG * 32 // 4
            rows.append([round(midi(pitch(mono[a + i * q: a + (i + 1) * q])), 2) for i in range(4)])
        else:
            rows.append(round(midi(pitch(mono[a + SEG * 32 // 2: a + SEG * 32])), 2))
    res[name] = rows
    print(f'{name:10s} rms {np.sqrt(np.mean(mono ** 2)):.4f}  pitch per segment (MIDI): {rows}')

want = [60, 60.5, 67, [67.25, 67.75, 68.25, 68.75]]
print('expected if the DSP follows the word:', want)
