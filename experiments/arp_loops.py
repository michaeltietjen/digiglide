"""Build 18 arp, "gaps or goes silent" on the unit: patterns that loop. Arp UP, 120 BPM, 16-step pattern
(3000 blocks a loop), 3 loops. Prints every gap between arp note-ons longer than a step (187 blocks) and the
notes, per scenario, DigiGlide track against a stock track with the same trigs.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python arp_loops.py DIGIGLIDE.syx"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16

img = sys.argv[1]
UP = 2
SCEN = {
    'four short trigs': [(0, 48, 6), (4, 50, 6), (8, 53, 6), (12, 55, 6)],
    'one endless trig': [(0, 48, 127)],
    'two long trigs': [(0, 48, 40), (8, 53, 40)],
}
only = sys.argv[2:] or list(SCEN)
for name in only:
    for dg in (True, False):
        s = Session(img, tag='arpl', solo=True, reserve=4)
        if dg:
            s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, pos=64, voic=64), t=0, mach=None, atk=None)
        for st, n, ln in SCEN[name]:
            s.trig(st, note=n, length=ln, t=0)
        snd = s.k.sound(0)
        s.k.h.uc.mem_write(snd + 351, bytes([UP])); s.k.h.uc.mem_write(snd + 374, bytes([UP]))
        fr = s.play(9200, bpm=120)
        ons = [(b, U16(f, 2 + 2 * v) >> 8) for b, f in enumerate(fr) for v in range(16)
               if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) == 0]
        gaps = [(ons[i][0], ons[i + 1][0] - ons[i][0]) for i in range(len(ons) - 1) if ons[i + 1][0] - ons[i][0] > 200]
        print(f'{name} / {"DigiGlide" if dg else "stock"}: {len(ons)} note-ons; gaps > 1 step (at, blocks): {gaps[:12]}')
        for loop in range(3):
            print('   loop', loop, [n for b, n in ons if 3000 * loop <= b < 3000 * (loop + 1)])
        sys.stdout.flush()
