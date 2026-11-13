"""Rev 5 listening demos (Orchid-style chords): the reference model through the simple saw pad (padsynth.py), before
any firmware work. 100 BPM; a chord a bar unless noted; GLID 1/2 bar, PATH Smooth, VCNT 5, BASS root, VOIC 64, BASS FOL-1.
What each file plays is in DEMOS and printed, with the notes every voice lands on.
    ~/dn2-workspace/repos/digikit/.venv/bin/python render_rev5.py      -> ~/glide/renders/rev5/*.wav
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import digiglide as G
import padsynth as S

OUT = os.path.expanduser('~/glide/renders/rev5')
os.makedirs(OUT, exist_ok=True)
BPM = 100.0
BAR = int(round(240.0 / BPM * G.HZ))
C5 = 60
name = lambda n: f'{G.NOTE_NAMES[n % 12]}{n // 12}'


def events(steps, hold=True, typ=0, ext=0, key=0, voic=64, glid=4, per=1.0, held=0.5, **kw):
    """steps: list of roots, or dicts {root, typ, ext, key, voic, revoice, off}. hold: no release between chords
    (HOLD on, or keys held into the next). Not hold: each chord is released after `held` of its slot.
    GLID 0: the chord is released in the block the next one starts (it retriggers, no glide)."""
    ev, b, lines = {}, 0, []
    cur = dict(typ=typ, ext=ext, key=key, voic=voic)
    last = None
    for s in steps:
        s = dict(root=s) if isinstance(s, int) else dict(s)
        for k in cur:
            cur[k] = s.get(k, cur[k])
        slot = int(BAR * per * s.get('len', 1))
        if s.get('off'):                                  # "the same key again": the chord fades
            ev.setdefault(b, []).append(('off',))
            lines.append((b, 'release', None))
        else:
            root = s.get('root', last)
            pcs, sk, sc = G.chord_for(root, cur['typ'], cur['ext'], cur['key'])
            p = G.Params(key=sk, scl=sc, voic=cur['voic'], glid=glid, **kw)
            if glid == 0 and last is not None:
                ev.setdefault(b, []).append(('off',))
            ev.setdefault(b, []).append(('trig', 0, p, root, pcs, False, bool(s.get('revoice'))))
            lines.append((b, f"{name(root)} {G.TYPES[cur['typ']]} {G.EXTS[cur['ext']]}"
                             + (f" key {G.KEY_NAMES[cur['key']]}" if cur['key'] else '') + f" voic {cur['voic']}", pcs))
            last = root
            if not hold:
                ev.setdefault(b + int(slot * held), []).append(('off',))
        b += slot
    return ev, b + 2 * BAR, lines


SCALE = [60, 62, 64, 65, 67, 69, 71, 72]
DEMOS = [
    ('01_twelve_keys', 'Twelve keys, C5 up to B5, TYPE MAJ, HOLD on: twelve major chords, each gliding to the next',
     events(list(range(60, 72)))),
    ('02_key_c_major', 'KEY C major, the white keys C5 to C6: the diatonic triads, then the same with EXT 7',
     events(SCALE + [dict(root=n, ext=2) for n in SCALE], key=1)),
    ('03_types_and_exts', 'One key (C5): TYPE MAJ, MIN, SUS, DIM, then MAJ with EXT 6, 7, MAJ7, 9, 7+9',
     events([dict(root=C5, typ=t) for t in range(4)] + [dict(root=C5, typ=0, ext=e) for e in (1, 2, 3, 4, 6)])),
    ('04_voic_sweep', 'C5 MAJ7 held, VOIC turned 0, 32, 64, 96, 127 and back to 64: the voices glide to each voicing',
     events([dict(root=C5, voic=0)] + [dict(root=C5, voic=v, revoice=True) for v in (32, 64, 96, 127, 64)], ext=3)),
    ('05_hold', 'HOLD on: C, then F, then G (each key released at once, the chord stays and glides), G again: it fades',
     events([60, 65, 67, dict(off=True)], ext=2, key=1)),
    ('06_glid_0', 'GLID 0: C, F, G, C retrigger, no glide',
     events([60, 65, 67, 60], glid=0, key=1)),
    ('07_octaves', 'The root follows the key: C4, C5, C6, then G4, G5 (TYPE MIN, EXT 7)',
     events([48, 60, 72, 55, 67], typ=1, ext=2)),
    ('08_short_notes', 'HOLD off, short notes (released after a third of the bar): each chord attacks again and glides '
                       'from the one still ringing', events([60, 69, 65, 67, 60], hold=False, held=0.33, key=1, ext=2)),
    ('09_progression', 'KEY A minor, EXT 9: A4, F4, C5, G4, twice, the second time with MOVE Spiral on each change',
     events([57, 53, 60, 55] + [57, 53, 60, 55], key=22, ext=4, per=2.0)),
]

rendered, peak = [], 0.0
notes_out = []
for stem, text, (ev, nb, lines) in DEMOS:
    if stem == '09_progression':                         # second half: MOVE Spiral
        half = sorted(ev)[4]
        for b in sorted(ev):
            if b >= half:
                ev[b] = [(e[0], e[1], e[2].copy(move=4), *e[3:]) if e[0] == 'trig' else e for e in ev[b]]
    pitch, gate, pan, level, m = G.run(ev, nb, BPM)
    L, R = S.render(pitch, gate, pan, level)
    rendered.append((stem, L, R))
    peak = max(peak, float(np.max(np.abs(np.r_[L, R]))))
    notes_out.append(f'{stem}: {text}')
    P = np.array(pitch)
    for i, (b, what, pcs) in enumerate(lines):
        nxt = lines[i + 1][0] if i + 1 < len(lines) else nb
        row = P[min(nb - 1, nxt - 2)]
        land = [name(int(round(c / 100.0))) for c in row if c == c]
        notes_out.append(f'    {b / G.HZ:5.1f} s  {what:34s} -> ' + ('fades' if pcs is None else ' '.join(land)))
gain = 10 ** (-1 / 20) / peak
for stem, L, R in rendered:
    S.write_wav(os.path.join(OUT, stem + '.wav'), L, R, gain)
open(os.path.join(OUT, 'README.txt'), 'w').write('\n'.join(notes_out) + '\n')
print('\n'.join(notes_out))
print('files:', OUT)
