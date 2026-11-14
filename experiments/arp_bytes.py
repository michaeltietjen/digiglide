"""Which sound bytes are the arp's SPEED and N.LEN (1.12)? One long trig, arp UP, stock image: change one byte of
+352..+375, print the gap between arp note-ons and the note length in blocks.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python arp_bytes.py"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, U16

def run(patch):
    s = Session(None, tag='arpb', solo=True, reserve=0)
    s.trig(0, note=48, length=127, t=0)
    snd = s.k.sound(0)
    base = bytes(s.k.h.r(snd + 340, 40))
    s.k.h.uc.mem_write(snd + 351, bytes([2])); s.k.h.uc.mem_write(snd + 374, bytes([2]))
    for o, v in patch:
        s.k.h.uc.mem_write(snd + o, bytes([v]))
    fr = s.play(1500, bpm=120)
    ons = [b for b, f in enumerate(fr) if U16(f, 0x22)]
    offs = [b for b, f in enumerate(fr) if U16(f, 0x24)]
    gap = [ons[i + 1] - ons[i] for i in range(min(4, len(ons) - 1))]
    ln = offs[0] - ons[0] if ons and offs else None
    return base, len(ons), gap, ln

base, n, gap, ln = run([])
print('sound +340..+379:', base.hex(' '))
print('base', n, gap, ln, flush=True)
for o in (352, 353, 354, 355, 356):
    v = base[o - 340]
    r = run([(o, (v + 3) & 0x7F)])
    print(f'+{o} {v} -> {(v + 3) & 0x7F}:', r[1:], flush=True)
