"""Owner, 2026-11-16: "arps on other tracks seem to be overwhelmed". A DigiGlide track (track 1: 5 voices, HOLD, two
long trigs) beside a stock arp on track 2 (one long trig, MODE UP). Measured on track 2: its note-ons, the voices they
land on, its level words, and note-offs / voices taken from it; the same with DigiGlide OFF on track 1.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b26_other_arp.py IMAGE.syx"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16

img = sys.argv[1]
n = os.path.basename(img)[:-4].rsplit('_', 1)[-1]


def run(tag, on):
    s = Session(img, tag=tag, solo=True, reserve=0)
    s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, hold=1, bass=2, voic=64, drft=0, vib=0), t=0, mach=None, atk=None, on=on)
    s.trig(0, note=48, length=127, t=0)
    s.trig(8, note=50, length=127, t=0)
    s.trig(0, note=60, length=127, t=1)
    h = s.k.h
    snd = s.k.sound(1)
    h.uc.mem_write(snd + 351, bytes([2])); h.uc.mem_write(snd + 374, bytes([2]))      # arp MODE UP
    fr = s.play(6400, bpm=120)
    own = lambda f, v: U16(f, 0xA5A + 2 * v)
    for t in (0, 1):
        ons = [(i, v) for i, f in enumerate(fr) for v in range(16) if U16(f, 0x22) >> v & 1 and own(f, v) == t]
        offs = [(i, v) for i, f in enumerate(fr) for v in range(16) if U16(f, 0x24) >> v & 1 and own(f, v) == t]
        vs = sorted({v for _, v in ons})
        lv = [U16(f, 0x74 + 2 * v) for i, f in enumerate(fr) for v in vs if own(f, v) == t and i > 1000]
        print(f'[{n}] DG {"on " if on else "OFF"} track {t + 1}: {len(ons):3d} note-ons on voices {vs}, {len(offs):3d} note-offs, '
              f'level {min(lv, default=0):#06x}..{max(lv, default=0):#06x}, first ons {[i for i, _ in ons[:6]]}', flush=True)
    allon = sorted({v for f in fr for v in range(16) if U16(f, 0x22) >> v & 1})
    print(f'[{n}] DG {"on " if on else "OFF"} all voices struck {allon}; DG ctl {s.k.h.u32(s.sym["DG"] + 56):#06x}', flush=True)


run('oa_on', True)
run('oa_off', False)
