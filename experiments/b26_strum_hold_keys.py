"""Owner, 2026-11-16 (image 25 on the unit): "strum down still doesn't work with chord hold on". Live keys, HOLD on or
off, PLAY STRM (1) or STRU (2): key 1 down / up, key 3 down / up, key 1 again. Per press: DigiGlide's note-ons (block,
voice, note) and dg_pm_strums.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b26_strum_hold_keys.py IMAGE.syx PLAY HOLD [VCNT] [BASS]"""
import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16
from emu import panelin

img, play, hold = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
vcnt = int(sys.argv[4]) if len(sys.argv) > 4 else 4
bass = int(sys.argv[5]) if len(sys.argv) > 5 else 0
s = Session(img, tag=f'sk_{play}{hold}{vcnt}{bass}', solo=True, reserve=0)
s.set_sound(Ui(vcnt=vcnt, type=1, ext=2, glid=3, voic=64, drft=0, vib=0, hold=hold, play=play, bass=bass))
for _ in range(3):
    s.k.tap('SYN')
s.k.tap('KEYB')
h = s.k.h
h.frames(2200)
strums = lambda: struct.unpack('>I', bytes(h.r(s.sym['dg_pm_strums'], 4)))[0]


def press(mask, frames=900):
    st, s0 = len(h.sent), strums()
    h.pc = panelin.buttons(h.m, h.profile, 3, mask); h.run(3_000_000)
    h.frames(frames)
    fr = [x for x, _ in h.sent[st:]]
    ons = [(i, v, U16(f, 2 + 2 * v) >> 8) for i, f in enumerate(fr) for v in range(16) if U16(f, 0x22) >> v & 1]
    offs = sorted({i for i, f in enumerate(fr) if U16(f, 0x24)})
    dg = s.sym['DG']
    return ons, offs[:3], strums() - s0, (h.u32(dg + 4), h.u32(dg + 96), hex(h.u32(dg + 92)), h.u32(dg + 12))


tag = f'PLAY {["CHRD", "STRM", "STRU", "HARP"][play]} HOLD {hold} VCNT {vcnt} BASS {bass}'
for name, m in (('key 1 down', 1), ('up', 0), ('key 2 down', 2), ('up', 0), ('key 5 down', 16), ('up', 0), ('key 3 down', 4), ('up', 0), ('key 1 down', 1), ('up', 0)):
    ons, offs, st, dgs = press(m)
    print(f'{tag}: {name:10s} strums {st}  note-ons {ons}  offs {offs}  trigs/taken/held/active {dgs}', flush=True)
