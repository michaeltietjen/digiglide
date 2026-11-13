"""One trig-default variant per fresh session (a long session drops events): trigs on steps 3 and 7 of track 1, the
track's trig defaults changed as given, 1500 blocks played; prints note-on blocks (voices, note, velocity) and
note-off blocks. On DigiGlide the sound is a DigiGlide sound (HOLD from the 3rd argument).
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python trig_var.py stock|IMAGE.syx OFF=VAL[,OFF=VAL] [hold] [atk]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16
from osver import A

arg, var = sys.argv[1], sys.argv[2]
img = None if arg == 'stock' else arg
hold = len(sys.argv) > 3 and sys.argv[3] == 'hold'
atk = int(sys.argv[4]) if len(sys.argv) > 4 else 64
tag = ('st' if not img else 'dg') + ('h' if hold else '') + (f'a{atk}' if atk != 64 else '') + '_' + var.replace('=', 'x').replace(',', '_')
s = Session(img, tag='tv_' + tag, solo=True, reserve=0)
k, h = s.k, s.k.h
if img:
    s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=int(hold)), atk=atk)
    for _ in range(3):
        k.tap('SYN')
else:
    k.select(1, track=0)
d = s.trig_defaults(0)
s.trig(2, note=60, length=14)
s.trig(6, note=64, length=14)
for kv in var.split(','):
    if kv.startswith('w'):                              # wSTEP=WORD: the step's 2-byte word in the pattern
        o, v = kv[1:].split('=')
        h.w(h.u32(A(0x42C5A9A0)) + 2 * int(o), int(v, 0).to_bytes(2, 'big'))
    elif '=' in kv:
        o, v = kv.split('=')
        h.w(d + int(o), bytes([int(v, 0)]))
fr = s.play(1500, bpm=120)
ons = [(i, hex(U16(f, 0x22)), min(U16(f, 2 + 2 * v) >> 8 for v in range(16) if U16(f, 0x22) >> v & 1),
        max(U16(f, 0x34 + 2 * v) for v in range(16) if U16(f, 0x22) >> v & 1) >> 8) for i, f in enumerate(fr) if U16(f, 0x22)]
offs = [(i, hex(U16(f, 0x24))) for i, f in enumerate(fr) if U16(f, 0x24)]
print(f'RES {tag:22s} ons(block,voices,note,vel) {ons[:14]} n={len(ons)} offs {offs[:14]} n={len(offs)}')
