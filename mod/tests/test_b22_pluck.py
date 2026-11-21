"""DigiGlide build 22: a string's turn in a strum or a harp run is plucked: its voice record has AMP RSET on (256) at
its note-on, so the amp envelope restarts from silence. Through image 21 a strum over a chord still sounding (HOLD
on) only changed each string's pitch in turn (experiments/b22_hold_audio.py). CHRD keeps RSET off at every note-on
(a held chord's strike rises from its level). HOLD on, TYPE MIN EXT 7, 4 voices, trigs on steps 1 5 9 13.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b22_pluck.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
for play, name, want in ((0, 'CHRD', {0}), (1, 'STRM', {256}), (2, 'STRU', {256}), (3, 'HARP', {256})):
    s = Session(img, tag=f'b22p{play}', solo=True)
    s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, pos=64, voic=64, play=play, hold=1), t=0, mach=None, atk=None)
    for st, n in [(0, 48), (4, 53), (8, 55), (12, 50)]:
        s.trig(st, note=n, length=30, t=0)
    fr = s.play(3000, bpm=120)
    rs, n_on = set(), 0
    for f in fr:
        on = U16(f, 0x22)
        for v in range(16):
            if on >> v & 1:
                n_on += 1
                rs.add(U16(f, 0xDA + 146 * v + 134))
    good = n_on >= 16 and rs == want
    ok &= good
    print(('  ok   ' if good else '  FAIL ') + f'{name} HOLD on: {n_on} note-ons, RSET at note-on {sorted(rs)}', flush=True)
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
