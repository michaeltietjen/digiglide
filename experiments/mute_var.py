"""Track mute: [FUNC] + [TRIG 1] (quick mute of track 1). Trigs on steps 3 and 7; mode 'pre' mutes before PLAY, 'none'
does not. Prints note-ons / note-offs and which frame bytes outside the voice records differ from frame 300 on.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python mute_var.py stock|IMAGE.syx none|pre [hold]"""
import os, sys, pickle
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16

arg, mode = sys.argv[1], sys.argv[2]
img = None if arg == 'stock' else arg
hold = len(sys.argv) > 3
tag = ('st' if not img else 'dg') + ('h' if hold else '') + '_' + mode
s = Session(img, tag='mu_' + tag, solo=True, reserve=0)
k, h = s.k, s.k.h
if img:
    s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=int(hold)))
    for _ in range(3):
        k.tap('SYN')
else:
    k.select(1, track=0)
s.trig(2, note=60, length=14)
s.trig(6, note=64, length=14)
if mode == 'pre':
    s.func_with(3, 0)
fr = s.play(1500, bpm=120)
ons = [(i, hex(U16(f, 0x22))) for i, f in enumerate(fr) if U16(f, 0x22)]
offs = [(i, hex(U16(f, 0x24))) for i, f in enumerate(fr) if U16(f, 0x24)]
print(f'RES {tag:12s} ons {ons} offs {offs}')
pickle.dump([bytes(fr[300]), bytes(fr[400]), bytes(fr[1200])], open(os.path.expanduser(f'/tmp/digiglide/tv/mu_{tag}.pkl'), 'wb'))
