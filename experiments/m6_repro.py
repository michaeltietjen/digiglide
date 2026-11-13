"""M6 first flash, reports A / B / C: reproduce in the emulator what the unit did.

The M3..M5 tests always gave track 1 six reserved voices (VOICE menu, VOICES = 6) and soloed it. The unit had neither.
Cases (8 trigs on track 1, notes C D E F G A B C, one per quarter note, VCNT 5, the same DEG):
  reserved   VOICES = 6 on track 1, the other tracks silent     (what the tests ran)
  dyn        VOICES left at its default, the other tracks silent
  dyn_busy   VOICES at its default, the demo's other tracks playing
For each trig block: the voices that got a note-on, whose they are, and whether DigiGlide took the trig.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python m6_repro.py"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest, G, U16
import osver
from osver import A

NOTES = [60, 62, 64, 65, 67, 69, 71, 72]
img = latest()
print('image', os.path.basename(img), 'OS', osver.OS)


def run(name, reserve, solo):
    s = Session(img, tag='m6_' + name, solo=solo, reserve=reserve)
    s.set_sound(G.Params(key=0, scl=1, deg=0, chrd=1, vcnt=5, glid=3))
    for st in range(128):
        s.k.call(A(0x40054690), [s.ctx0, st, 1, 0])
    for i, n in enumerate(NOTES):
        s.trig(4 * i, note=n, length=6)
    trigs = []
    fr = s.play(6200, bpm=120, each=lambda i: trigs.append(s.dg()['trigs']))
    print(f'-- {name}: VOICES {reserve or "default"}, other tracks {"silent" if solo else "playing"}')
    taken = stock = 0
    for i, f in enumerate(fr[:len(trigs)]):
        on = U16(f, 0x22)
        mine = [v for v in range(16) if on >> v & 1 and U16(f, 0xA5A + 2 * v) == 0]
        if not mine:
            continue
        dg = trigs[i] - (trigs[i - 1] if i else 0)
        words = {v: round(U16(f, 2 + 2 * v) / 256, 2) for v in mine}
        taken += bool(dg); stock += not dg
        print(f'   block {i:5d}: track-1 note-ons on voices {mine} notes {words}: '
              + ('DigiGlide chord' if dg else 'NOT taken: a plain stock note'))
    print(f'   => {taken} trigs became DigiGlide chords, {stock} played as stock notes')


for name, reserve, solo in (('reserved', 6, True), ('dyn', 0, True), ('dyn_busy', 0, False)):
    run(name, reserve, solo)
