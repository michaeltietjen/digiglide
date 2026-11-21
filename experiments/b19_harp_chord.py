"""Build 19 HARP: which chord the engine built for the test's trig (dg_name, dg_ui, DG.last_cw) vs the run's notes."""
import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16
img = sys.argv[1]
s = Session(img, tag='b19chk', solo=True)
s.set_sound(Ui(vcnt=4, type=1, ext=2, glid=3, pos=64, voic=64, play=int(sys.argv[2])), t=0, mach=None, atk=None)
s.trig(0, note=48, length=60, t=0)
fr = s.play(400, bpm=120)
h = s.k.h
print('name', bytes(h.r(s.sym['dg_name'], 16)).split(b'\0')[0])
print('dg_ui', list(bytes(h.r(s.sym['dg_ui'], 18))))
