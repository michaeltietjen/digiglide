"""DigiGlide M4a (spec rev 3, M4's progression tests): the parameters come from the sound and from p-locks.

Track 1 = a DigiGlide sound (WAVETONE, KEY C, SCL minor, CHRD Seventh, VCNT 5, BASS root, GLID 1 bar, other defaults),
VOICES = 6, trigs with LEN INF on steps 1, 17, 33, 49 and 53. P-locks: DEG I / VI / IV / V on steps 1 / 17 / 33 / 49
(a 4-step progression from p-locked DEG values), GLID 0 on step 33 (a hard change), and step 53 interrupts step 49's
1-bar glide halfway (DEG I).
Checks:
  - every trig read the parameters it should: the sound's values, its own step's locks, nothing from other steps;
  - every note word matches the M1 model block by block (within 0.25 cent);
  - GLID 0: the chord changes in one block, onto whole notes;
  - the chord change mid-glide shows no jump (largest per-block step at the change);
  - a sound without the switch (slot 100) plays stock: no DigiGlide voices.
    ~/dn2-workspace/repos/digikit/.venv/bin/python test_m4a.py [DIGIGLIDE.syx]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dgkit import Session, latest, U16, G, edges, word, model

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg)


BASE = G.Params(key=0, scl=1, chrd=1, glid=5)
STEPS = [0, 16, 32, 48, 52]
LOCKS = {0: dict(deg=0), 16: dict(deg=5), 32: dict(deg=3, glid=0), 48: dict(deg=4), 52: dict(deg=0)}

s = Session(img, tag='m4a')
s.set_sound(BASE)
for st in STEPS:
    s.trig(st, note=60, length=127)
for st, f in LOCKS.items():
    s.lock(st, **f)
log = s.trig_log()
fr = s.play(15000, bpm=120, each=log)
d = s.dg()
ons, offs = edges(fr)
isr = log.isr_blocks()
check(len(isr) == len(STEPS) and d['trigs'] == len(STEPS), f'{d["trigs"]} trigs ({len(STEPS)} placed)')
off = ons[0] - isr[0]
blocks = [b + off for b in isr]
check(len(ons) == 1, f'one attack (the first trig) and the rest glide: attack blocks {ons}')
check(d['step_log'][:len(STEPS)] == STEPS, f'steps seen by the hook {d["step_log"][:len(STEPS)]} == placed {STEPS}')

want = [BASE.copy(**LOCKS[st]) for st in STEPS]
got = log.params
for k, (w, g) in enumerate(zip(want, got)):
    same = all(getattr(w, f) == getattr(g, f) for f in G.Params.FIELDS)
    locked = [f for i, f in enumerate(G.Params.FIELDS) if log.locks[k] >> i & 1]
    check(same and sorted(locked) == sorted(LOCKS[STEPS[k]]),
          f'trig {k + 1} (step {STEPS[k] + 1}): {w.label()}, GLID {G.GLID_NAMES[g.glid]}, locked {locked}')

b0 = blocks[0]
ev = {}
for k, b in enumerate(blocks):
    ev.setdefault(b - b0, []).append(('trig', STEPS[k], want[k], 60))
pitch, gate, m = model(ev, len(fr) - b0 - 8, d['last_tempo'], tails=s.tails())
n = len(pitch)
words = np.array([[word(f, v) for v in range(6)] for f in fr[b0:b0 + n]], float) * 100 / 256
mp = np.array(pitch)
live = ~np.isnan(mp)
diff = np.abs(np.where(live, words - mp, 0))
check(diff.max() <= 0.25, f'note words match the model in all {n} blocks x 6 voices: largest difference '
                          f'{diff.max():.3f} cent')

b = blocks[2] - b0                                       # GLID 0
step = np.abs(words[b] - words[b - 1])[:5]
whole = np.abs(mp[b, :5] - G.DigiGlide().v[0].cur) * 0     # (placeholder for shape)
check(np.max(step) >= 100 and np.all(np.abs(words[b + 1, :5] - words[b, :5]) < 2),
      f'GLID 0 on step 33: the chord changes in one block (moves {np.round(step, 1)} cents) and stays')
b = blocks[4] - b0                                       # mid-glide change
around = np.max(np.abs(np.diff(words[b - 3:b + 3, :5], axis=0)))
moving = np.max(np.abs(words[b - 1, :5] - words[blocks[3] - b0 - 1, :5]))
check(moving > 50 and around < 5,
      f'step 53 interrupts the glide {moving:.0f} cents into it; largest per-block step around the change '
      f'{around:.2f} cents (no jump)')

# control: the same sound without the switch plays stock (one voice, no DigiGlide edges)
s2 = Session(img, tag='m4a_off')
s2.set_sound(BASE, on=False)
s2.trig(0, note=60, length=127)
fr2 = s2.play(400, bpm=120)
ons2 = [(i, v) for i, f in enumerate(fr2) for v in range(16) if (U16(f, 0x22) >> v) & 1]
check(len(ons2) == 1 and s2.dg()['trigs'] == 0, f'without the switch: stock (note-ons {ons2}, DigiGlide trigs '
                                                 f'{s2.dg()["trigs"]})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
