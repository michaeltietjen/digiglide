"""DigiGlide M3 (spec rev 3): a trig on the DigiGlide track plays the voice-led chord.

Track 1 = a DigiGlide sound (KEY C, SCL major, DEG I, BASS root, other parameters at their defaults: VCNT 5, SPRD
77, DRFT 8, VIB 4), VOICES 6; 13 trigs (steps 1, 5, ..., 49, short LEN so each chord is fresh), CHRD p-locked per step
to every chord type in turn.
Checks, from the frames the OS sends to the DSP:
  - each trig attacks VCNT voices in one block, the bass an octave under the trig note (C5 -> MIDI 48) and the chord above it (only chord tones,
    every voice above the one below);
  - every DigiGlide voice's note word matches the M1 model (same trig blocks, gate-offs, steps and tempo) in every
    block, within 0.25 cent (the note word's resolution is 0.39 cent);
  - voices that sound carry the source voice's sound record, velocity, level, machine and track, with SPRD pans;
  - no other voice is touched (all other tracks are empty: no note-ons outside voices 0..5).
    ~/dn2-workspace/repos/digikit/.venv/bin/python test_m3_dg.py [DIGIGLIDE.syx]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dgkit import Session, latest, U16, G, edges, word, model

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
N_CH = len(G.CHORDS)
GAP = 4                                         # steps between trigs (750 blocks at 120 BPM)
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg)


s = Session(img, tag='m3')
base = G.Params(key=0, scl=0, deg=0, chrd=0, bass=1)
params = [base.copy(chrd=c) for c in range(N_CH)]
s.set_sound(base)
s.k.slot(0, 85, 0)                             # AMP REL 0: each chord is gone before the next, so each starts fresh
for k in range(N_CH):
    s.trig(GAP * k, note=60, length=20)
    if k:
        s.lock(GAP * k, chrd=k)                 # M4: each trig's CHRD as a p-lock on its step
n_blocks = GAP * N_CH * 188 + 1500
each = None
fr = s.play(n_blocks, bpm=120, each=each)
d = s.dg()
ons, offs = edges(fr)
check(d['trigs'] == N_CH, f'{d["trigs"]} trigs seen ({N_CH} placed); tempo word {d["last_tempo"]}')
check(len(ons) == N_CH, f'one attack block per trig: {len(ons)} attack blocks')
others = [i for i, f in enumerate(fr) if U16(f, 0x22) & ~0x3F & 0xFFFF]
check(not others, f'no note-ons outside the DigiGlide voices ({len(others)} blocks)')

# the model on the same events
b0 = ons[0]
ev = {}
for k, b in enumerate(ons):
    ev.setdefault(b - b0, []).append(('trig', d['step_log'][k], params[k], 60))
for b in offs:
    ev.setdefault(b - b0, []).append(('off',))
pitch, gate, m = model(ev, len(fr) - b0, d['last_tempo'], tails=s.tails())

words = np.array([[word(f, v) for v in range(6)] for f in fr[b0:]], float) * 100 / 256
mp = np.array(pitch)
live = ~np.isnan(mp)
diff = np.abs(np.where(live, words - mp, 0))
check(diff.max() <= 0.25, f'note words match the model in all {len(mp)} blocks x 6 voices: largest difference '
                          f'{diff.max():.3f} cent')
gates = np.array([[(U16(f, 0x22) >> v) & 1 for v in range(6)] for f in fr[b0:]])
want_on = np.diff(np.vstack([np.zeros(6), np.array(gate, float)]), axis=0) > 0
check(np.array_equal(gates == 1, want_on), 'attacks exactly where the model opens a gate')

for k, b in enumerate(ons):
    f = fr[b]
    att = [v for v in range(6) if (U16(f, 0x22) >> v) & 1]
    notes = [word(f, v) / 256 for v in att]
    root_pc, pcs = G.chord_tones(0, 0, 0, k)
    stacked = all(b_ > a_ for a_, b_ in zip(notes, notes[1:]))
    tones = all(round(n) % 12 in pcs for n in notes)
    check(len(att) == 5 and round(notes[0]) == 48 and stacked and tones,
          f'{G.CHORDS[k][0]:9s}: {len(att)} voices {[G.NOTE_NAMES[round(n) % 12] + str(round(n) // 12 - 1) for n in notes]}'
          f' (bass an octave under the trig note, stacked, chord tones)')

# record copies and pans, in a block where the chord sounds
f = fr[ons[0] + 50]
src = d['src']
rec = lambda v: bytes(f[0xda + 146 * v: 0xda + 146 * (v + 1)])
same = all(rec(v)[:128] + rec(v)[130:] == rec(src)[:128] + rec(src)[130:] for v in range(5))
words_ok = all(U16(f, o + 2 * v) == U16(f, o + 2 * src) for v in range(5) for o in (0x34, 0x54, 0x74, 0x94, 0xA5A))
pans = [(U16(f, 0xda + 146 * v + 128) - U16(f, 0xda + 146 * src + 128)) / 256 for v in range(5)]
want = [round(p * 64, 1) for p in G.BASE_PANS[:5]]
check(same and words_ok, f'voices 1-5 carry the source voice ({src})\'s record, velocity, curve, level, machine, track')
check(all(abs(a - b) <= 0.05 for a, b in zip(pans, want)), f'SPRD 77 pans (knob steps from the source): {pans}')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
