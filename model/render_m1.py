"""M1 renders: the DigiGlide model through a simple saw pad (padsynth.py). 120 BPM, C minor, spec defaults
(CHRD Seventh, VCNT 5, BASS root, SPRD 77, DRFT 8, VIB 4, GLID 1 bar, PATH Smooth) unless noted.

    progression.wav            i - VI - iv - v, a chord every 2 bars, GLID 1 bar
    moves/NN_<move>.wav        the same progression, a chord every 3 bars; chords 2-4 use the MOVE
    paths/NN_<path>.wav        one change, i -> VI, GLID 1 bar, with each PATH
    paths_all.wav              the ten path files back to back
    *.png                      pitch traces (what each voice plays, in MIDI notes)
    notes.txt                  the notes each chord lands on

One shared gain for every file, so loudness compares across them.
    python3 render_m1.py [out dir]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import digiglide as G
import padsynth as S

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/glide/renders/M1')
BPM = 120.0
BAR = int(round(240.0 / BPM * G.HZ))
BASE = G.Params(key=0, scl=1)                            # C minor + spec defaults
PROG = [0, 5, 3, 4]                                       # i VI iv v


def slug(s):
    return s.lower().replace(' ', '_')


def plot(path, pitch, gate, title, marks):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    p = np.asarray(pitch, float) / 100.0
    g = np.asarray(gate, bool)
    t = np.arange(len(p)) / G.HZ
    fig, ax = plt.subplots(figsize=(11, 5))
    names = ['voice 1 (bass)', 'voice 2', 'voice 3', 'voice 4', 'voice 5', 'voice 6 / sub']
    for v in range(p.shape[1]):
        if np.all(np.isnan(p[:, v])):
            continue
        y = np.where(g[:, v], p[:, v], np.nan)
        ax.plot(t, y, lw=1.4, label=names[v])
        ax.plot(t, np.where(g[:, v], np.nan, p[:, v]), lw=0.6, color='0.75')
    for b, lab in marks:
        ax.axvline(b / G.HZ, color='0.6', lw=0.7, ls='--')
        ax.text(b / G.HZ + 0.05, np.nanmax(p) + 0.6, lab, fontsize=8)
    lo, hi = int(np.nanmin(p)) - 1, int(np.nanmax(p)) + 2
    ax.set_yticks(range(lo, hi + 1, 1), minor=True)
    ax.set_yticks([n for n in range(lo, hi + 1) if n % 12 in (0, 7)])
    ax.set_yticklabels([f'{G.NOTE_NAMES[n % 12]}{n // 12 - 1} ({n})' for n in range(lo, hi + 1) if n % 12 in (0, 7)])
    ax.grid(axis='y', which='both', color='0.92')
    ax.set_xlabel('seconds')
    ax.set_ylabel('MIDI note (scientific names, C4 = 60)')
    ax.set_title(title)
    ax.legend(loc='lower right', fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def landed(pitch, b):
    return sorted(int(round(c / 100)) for c in pitch[b] if c == c)


def name(n):
    return f'{G.NOTE_NAMES[n % 12]}{n // 12 - 1}'


jobs = []        # (file stem, title, events, n blocks, marks, landing blocks)

steps = [BASE.copy(deg=d) for d in PROG]
ev, nb = G.progression(steps, 2, BPM, n_tail_bars=3)
jobs.append(('progression', 'i - VI - iv - v in C minor, Seventh, GLID 1 bar, PATH Smooth',
             ev, nb, [(k * 2 * BAR, G.ROMAN[d].lower() if d in (0, 3, 4) else G.ROMAN[d]) for k, d in enumerate(PROG)],
             [(k + 1) * 2 * BAR - 1 for k in range(4)]))

for mv in range(1, 10):
    steps = [BASE.copy(deg=PROG[0])] + [BASE.copy(deg=d, move=mv) for d in PROG[1:]]
    ev, nb = G.progression(steps, 3, BPM, n_tail_bars=3)
    jobs.append((f'moves/{mv:02d}_{slug(G.MOVES[mv])}', f'MOVE {G.MOVES[mv]} on chords 2-4 (a chord every 3 bars)',
                 ev, nb, [(k * 3 * BAR, ('' if k == 0 else G.MOVES[mv] + ' ') + G.ROMAN[d]) for k, d in enumerate(PROG)],
                 [(k + 1) * 3 * BAR - 1 for k in range(4)]))

for pa in range(10):
    steps = [BASE.copy(deg=0, path=pa), BASE.copy(deg=5, path=pa)]
    ev = {0: [('trig', 0, steps[0])], BAR: [('trig', 16, steps[1])], 4 * BAR: [('off',)]}
    jobs.append((f'paths/{pa:02d}_{slug(G.PATHS[pa])}', f'PATH {G.PATHS[pa]}: i -> VI, GLID 1 bar',
                 ev, 6 * BAR, [(0, 'i'), (BAR, 'VI')], [BAR - 1, 4 * BAR - 1]))

os.makedirs(os.path.join(OUT, 'moves'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'paths'), exist_ok=True)
audio, notes = {}, []
for stem, title, ev, nb, marks, lands in jobs:
    pitch, gate, pan, level, m = G.run(ev, nb, BPM)
    L, R = S.render(pitch, gate, pan, level)
    audio[stem] = (L, R)
    plot(os.path.join(OUT, stem + '.png'), pitch, gate, title, marks)
    chords = ['  '.join(name(n) for n in landed(pitch, b)) for b in lands]
    notes.append(f'{stem}: ' + ' | '.join(chords))
    print(f'{stem:28s} {len(L) / S.SR:5.1f} s  peak {max(np.abs(L).max(), np.abs(R).max()):.3f}')

peak = max(max(np.abs(L).max(), np.abs(R).max()) for L, R in audio.values())
gain = 0.89 / peak                                        # -1 dBFS for the loudest file
for stem, (L, R) in audio.items():
    S.write_wav(os.path.join(OUT, stem + '.wav'), L, R, gain)
gap = np.zeros(S.SR // 2)
cat = [np.concatenate([np.concatenate([audio[s][c], gap]) for s in sorted(audio) if s.startswith('paths/')]) for c in (0, 1)]
S.write_wav(os.path.join(OUT, 'paths_all.wav'), cat[0], cat[1], gain)
with open(os.path.join(OUT, 'notes.txt'), 'w') as f:
    f.write('Notes each chord settles on (scientific names, C4 = MIDI 60; the Digitone screen names these an octave '
            'higher). Shared gain %.3f.\n\n' % gain)
    f.write('\n'.join(notes) + '\n')
print('gain', round(gain, 3), '->', OUT)
