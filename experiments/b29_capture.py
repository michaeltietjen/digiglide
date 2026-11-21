"""Build 29 sounds: the frames the OS sends while a DigiGlide track plays two chords, four bars each, twice round
(128 steps, 120 BPM, 48,000 blocks). The note words, gates and velocities are DigiGlide's; the sound is put in later
(b29_sounds.py). Saved to ~/glide/renders/b29/cap_NAME.bin (2688 bytes a frame).
    DG_OS=1.12 python b29_capture.py IMAGE.syx NAME"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui
SETS = {  # the DigiGlide settings of each sound, and its two roots
    'still': (dict(vcnt=4, type=0, ext=4, glid=6, hold=1, drft=30, vib=2, voic=90, bass=0), (48, 53)),
    'chain': (dict(vcnt=4, type=1, ext=2, glid=5, hold=1, drft=12, vib=3, voic=90, bass=0), (45, 50)),
    'ring': (dict(vcnt=4, type=1, ext=0, glid=6, hold=1, drft=10, vib=2, voic=70, bass=0), (43, 39)),
    'bells': (dict(vcnt=4, type=0, ext=5, glid=4, hold=1, drft=20, vib=4, voic=100, bass=0), (48, 55)),
    'beat': (dict(vcnt=3, type=4, ext=0, glid=7, hold=1, drft=0, vib=0, voic=64, bass=0), (41, 43)),
    'pure': (dict(vcnt=4, type=0, ext=4, glid=6, hold=1, drft=4, vib=0, voic=90, bass=0), (48, 53)),
}
img, name = sys.argv[1], sys.argv[2]
ui, roots = SETS[name]
s = Session(img, tag='b29cap_' + name, solo=True)
s.set_sound(Ui(**ui), t=0, mach=None, atk=None)
if name == 'pure':                                      # TUNE PURE, FAN 64 (image 29)
    s.k.call(s.sym['dg_par_set'], [0, 24, 1 << 8])
    s.k.call(s.sym['dg_par_set'], [0, 25, 64 << 8])
s.trig(0, note=roots[0], length=127, t=0)
s.trig(64, note=roots[1], length=127, t=0)
fr = [bytes(f[:2688]) for f in s.play(int(sys.argv[3]) if len(sys.argv) > 3 else 48000, bpm=120)]
out = os.path.expanduser(f'~/glide/renders/b29/cap_{name}.bin')
open(out, 'wb').write(b''.join(fr))
print(name, len(fr), 'frames', out)
