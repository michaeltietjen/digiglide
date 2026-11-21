"""Build 18 arp on the unit: "gaps or goes silent". test_b18_arp ran with no voices reserved (reserve=0), the unit
reserves VCNT's voices. Arp UP on a DigiGlide track, one long trig, reserve 0 / 4 / 6: when each arp note-on and
note-off reaches the DSP, on which voice.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python arp_voices.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest, Ui, U16

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
UP = 2
for reserve in (0, 4, 6):
    s = Session(img, tag='arpv%d' % reserve, solo=True, reserve=reserve)
    s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, pos=64, voic=64), t=0, mach=None, atk=None)
    s.trig(0, note=48, length=127, t=0)
    snd = s.k.sound(0)
    s.k.h.uc.mem_write(snd + 351, bytes([UP])); s.k.h.uc.mem_write(snd + 374, bytes([UP]))
    fr = s.play(3000, bpm=120)
    ev = []
    for b, f in enumerate(fr):
        on, off = U16(f, 0x22), U16(f, 0x24)
        for v in range(16):
            if U16(f, 0xA5A + 2 * v) != 0:
                continue
            if on >> v & 1:
                ev.append((b, 'on', v, U16(f, 2 + 2 * v) >> 8))
            if off >> v & 1:
                ev.append((b, 'off', v))
    ons = [e for e in ev if e[1] == 'on']
    gaps = [ons[i + 1][0] - ons[i][0] for i in range(len(ons) - 1)]
    print(f'reserve {reserve}: {len(ons)} note-ons, notes {[e[3] for e in ons][:16]}')
    print(f'   voices {[e[2] for e in ons][:16]}')
    print(f'   gaps (blocks) {gaps[:16]}  dg {s.dg()}')
