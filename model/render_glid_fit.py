"""Listening demos for "GLID is the whole change": MOVE Bloom and Cascade up at GLID 1 bar, under Brickglide's rule
(old: a Move lasts at least 2.5 s, Bloom twice GLID, a Cascade's delays on top) and DigiGlide's (new: the last voice
lands at GLID). 120 BPM, KEY A minor, EXT 7, A4 F4 C5 G4, a chord every 2 bars, HOLD on. A quiet tick marks every bar
line: in the new files the chord has arrived on the tick one bar after each change.
    python3 render_glid_fit.py      -> ~/glide/renders/glid_fit/*.wav, README.txt
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import digiglide as G
import padsynth as S

OUT = os.path.expanduser('~/glide/renders/glid_fit')
os.makedirs(OUT, exist_ok=True)
BPM, PER = 120.0, 2
BAR = int(round(240.0 / BPM * G.HZ))
ROOTS = [57, 53, 60, 55]
out, peak, notes = [], 0.0, [__doc__.split('    python3')[0]]
for move, mname in ((1, 'bloom'), (2, 'cascade_up')):
    for fit, tag in ((False, 'old'), (True, 'new')):
        G.DigiGlide.FIT = fit
        ev = {}
        for k, root in enumerate(ROOTS):
            pcs, sk, sc = G.chord_for(root, 0, 2, 22)
            p = G.Params(key=sk, scl=sc, glid=5, move=move if k else 0)
            ev[k * PER * BAR] = [('trig', k * 16 * PER, p, root, pcs)]
        nb = (len(ROOTS) * PER + 2) * BAR
        ev[nb - BAR] = [('off',)]
        m = G.DigiGlide(BPM, 0)
        pitch, gate, pan, level, lands = [], [], [], [], []
        for b in range(nb):
            for e in ev.get(b, []):
                if e[0] == 'trig':
                    m.trig(e[1], e[2], *e[3:])
                    if b:
                        lands.append(max(v.delay + v.dur for v in m.v if v.path is not None and v.t0 == b))
                else:
                    m.gate_off()
            row = m.block()
            pitch.append([float('nan') if c is None else c for c, _, _, _ in row])
            gate.append([g for _, g, _, _ in row])
            pan.append([x for _, _, x, _ in row])
            level.append([x for _, _, _, x in row])
        L, R = S.render(pitch, gate, pan, level)
        peak = max(peak, float(np.max(np.abs(np.r_[L, R]))))
        out.append((f'{mname}_{tag}', L, R))
        notes.append(f'{mname}_{tag}.wav: MOVE {G.MOVES[move]}, GLID 1 bar (2.000 s). After each chord change the last '
                     f'voice lands after ' + ', '.join(f'{x:.3f} s' for x in lands))
G.DigiGlide.FIT = True
tick = np.sin(2 * np.pi * 2000 * np.arange(int(S.SR * 0.004)) / S.SR) * np.hanning(int(S.SR * 0.004)) * 0.12 * peak
gain = 10 ** (-1 / 20) / (peak * 1.12)
for stem, L, R in out:
    for k in range(len(L) * int(G.HZ) // (S.SR * BAR) + 1):
        a = int(k * BAR / G.HZ * S.SR)
        if a + len(tick) <= len(L):
            L[a:a + len(tick)] += tick
            R[a:a + len(tick)] += tick
    S.write_wav(os.path.join(OUT, stem + '.wav'), L, R, gain)
open(os.path.join(OUT, 'README.txt'), 'w').write('\n'.join(notes) + '\n')
print('\n'.join(notes[1:]))
