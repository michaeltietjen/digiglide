"""DigiGlide M4 research: where do a sound's slots 50..65 and their p-locks show up, and when?

Stock OS, track 1 as WAVETONE: sound slots 50 / 55 / 65 set to 5 / 6 / 7 (knob << 8); trigs on steps 1 and 5; step 5
p-locks slot 50 = 9, 55 = 10, 65 = 11 through the held-trig recorder 0x4004f8fe(ctx, step, slot, value). The frames
show each voice record's slots 50 / 55 / 65 around both note-ons (ramped or immediate?).
    $DIGIKIT/.venv/bin/python m4_readpath.py"""
import os, struct, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, U16

s = Session(None, tag='m4read', reserve=6)
k = s.k
k.select(1, track=0)                                   # WAVETONE on track 1
for slot, v in ((50, 5), (55, 6), (65, 7)):
    k.slot(0, slot, v << 8)
print('sound slots after set:', [hex(k.slot(0, x)) for x in (50, 55, 65)], 'machine', k.mach(0))
s.trig(0, length=20); s.trig(4, length=20)
ctx = s.ctx0
for slot, v in ((50, 9), (55, 10), (65, 11)):
    r = k.call(0x4004F8FE, [ctx, 4, slot, v << 8])
    print('lock step 5 slot', slot, '->', r & 0xFF)
fr = s.play(1700, bpm=120)
off = lambda v, slot: 0xDA + 146 * v + 2 * (slot - 25)
ons = [(i, v) for i, f in enumerate(fr) for v in range(6) if (U16(f, 0x22) >> v) & 1]
print('note-ons (block, voice):', ons)
for i, v in ons:
    for b in range(i - 2, i + 6):
        f = fr[b]
        print(f'  block {b:5d} voice {v}: slot50 {U16(f, off(v, 50)):#06x} slot55 {U16(f, off(v, 55)):#06x} '
              f'slot65 {U16(f, off(v, 65)):#06x}  note {U16(f, 2 + 2 * v) / 256:.1f}')
print('sound slots at the end:', [hex(k.slot(0, x)) for x in (50, 55, 65)])
