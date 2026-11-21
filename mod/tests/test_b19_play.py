"""DigiGlide build 19: the PLAY modes Strum and Harp, on DigiGlide's own voices. A DigiGlide track (TYPE MIN, EXT 7,
4 voices), trigs C3 on step 1 and D3 on step 9, each 60 long; when each note-on reaches the DSP, and its note.
  A  CHRD: the chord's voices start in one block (as before build 19).
  B  STRM: they start one after the other, low to high, 20 blocks (13 ms) apart; the second trig the same.
  C  STRU: high to low.
  D  HARP (BASS on, as default): the bass voice struck with the chord, then a run up through the chord's notes from
     its lowest chord voice for three octaves, 51 blocks (34 ms) a note, round the other 3 voices; a run on each
     trig; no note-off until the trig ends.
  E  HARP, POS locked to +36 on step 9: the second run starts higher than with no lock.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b19_play.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
CHRD, STRM, STRU, HARP = 0, 1, 2, 3


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def run(tag, play, lock_pos=None):
    s = Session(img, tag=tag, solo=True)
    s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, pos=64, voic=64, play=play), t=0, mach=None, atk=None)
    s.trig(0, note=48, length=60, t=0)
    s.trig(8, note=50, length=60, t=0)
    if lock_pos is not None:
        s.k.call(s.sym['dg_lock_put'], [0, 8, 4, lock_pos])
    fr = s.play(3000, bpm=120)
    ons, offs = [], []
    for b, f in enumerate(fr):
        on, off = U16(f, 0x22), U16(f, 0x24)
        for v in range(16):
            if on >> v & 1:
                ons.append((b, v, (U16(f, 2 + 2 * v) + 128) >> 8))   # nearest note (DRFT, VIB)
            if off >> v & 1:
                offs.append((b, v))
    return s, ons, offs


def split(ons):
    """the note-ons of the first trig and of the second (the second starts after the longest gap), lowest note first
    within a block."""
    ons = sorted(ons, key=lambda x: (x[0], x[2]))
    if len(ons) < 2:
        return ons, []
    g = max(range(len(ons) - 1), key=lambda i: ons[i + 1][0] - ons[i][0])
    return ons[:g + 1], ons[g + 1:]


s, ons, offs = run('b19a', CHRD)
a, b = split(ons)
check(len(a) == 4 and len({x[0] for x in a}) == 1, f'A: CHRD starts the 4 voices in one block: {a}')

s, ons, offs = run('b19b', STRM)
a, b = split(ons)
gaps = [a[i + 1][0] - a[i][0] for i in range(len(a) - 1)]
check(len(a) == 4 and gaps == [20, 20, 20], f'B: STRM, 4 note-ons 20 blocks apart: {a}')
check([x[2] for x in a] == sorted(x[2] for x in a), f'B: low to high {[x[2] for x in a]}')
check(len(b) == 4 and [x[2] for x in b] == sorted(x[2] for x in b), f'B: the second trig strummed too: {b}')

s, ons, offs = run('b19c', STRU)
a, b = split(ons)
check(len(a) == 4 and [x[2] for x in a] == sorted((x[2] for x in a), reverse=True), f'C: STRU, high to low: {a}')

s, ons, offs = run('b19d', HARP)
a, b = split(ons)
bass, runa = a[0], a[1:]
notes = [x[2] for x in runa]
gaps = [runa[i + 1][0] - runa[i][0] for i in range(len(runa) - 1)]
check(bass[0] == runa[0][0] and bass[2] < runa[0][2], f'D: the bass {bass[2]} struck with the run\'s first note {runa[0][2]}')
check(len(runa) >= 10 and set(gaps) == {51}, f'D: HARP, {len(runa)} notes 51 blocks apart (gaps {sorted(set(gaps))})')
check(notes == sorted(notes) and {n % 12 for n in notes} <= {0, 3, 7, 10} and notes[-1] - notes[0] <= 36,
      f'D: up through C MIN7 for three octaves: {notes}')
check(len({x[1] for x in runa}) == 3 and bass[1] not in {x[1] for x in runa}, f'D: round the 3 chord voices {sorted({x[1] for x in runa})}, not the bass voice {bass[1]}')
check(len(b) >= 10 and {n % 12 for _, _, n in b} <= {2, 5, 9, 0}, f'D: the second trig runs D MIN7: {[x[2] for x in b]}')
first_b = b[1][2] if len(b) > 1 else None
early = [o for o in offs if a and o[0] < runa[-1][0]]
check(not early, f'D: no note-off during the run ({early})')
print('  runs', s.k.h.u32(s.sym['dg_pm_runs']))

s, ons, offs = run('b19e', HARP, lock_pos=100)   # (at 80 the engine's voicing keeps C lowest)
a, b2 = split(ons)
check(len(b2) > 1 and first_b is not None and b2[1][2] > first_b, f'E: POS locked up on step 9: the run starts at {b2[1][2] if len(b2) > 1 else None}, '
      f'not {first_b}')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
