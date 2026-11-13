#!/usr/bin/env python3
"""List the p-locks of one track in the pattern that is playing (or selected), read over the read-only probe (OS 1.12).
The sequencer keeps one lane per (track, sound slot): 129 words, one a step. For every slot of the track that has a
lane, the steps whose value differs from the lane's most common value are printed (the common value is "no lock").

    python3 dglocks.py TRACK        (TRACK 1..16)"""
import collections, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgprobe import Probe

PLAYING, LT, IDX, SLOTS = 0x42C5B9A0, 97872, 20640, 101                 # OS 1.12 (mod/digiglide.c, par_at)
t = int(sys.argv[1]) - 1
p = Probe('Digitone II')
print('unit:', p.hello())
pat = int.from_bytes(p.peek(PLAYING, 4), 'big')
if not pat:
    sys.exit('no pattern pointer')
lt = pat + LT
idx = p.peek(lt + IDX + SLOTS * t, SLOTS)
n = 0
for slot, i in enumerate(idx):
    if i >= 128:
        continue
    lane = struct.unpack('>129h', p.peek(lt + 2 + 2 * 129 * i, 258))
    common = collections.Counter(lane).most_common(1)[0][0]
    locks = [(s, v) for s, v in enumerate(lane[:128]) if v != common]
    n += 1
    print('slot %3d lane %3d: no-lock value %d, %d locked steps' % (slot, i, common, len(locks)))
    for s, v in locks:
        print('     step %3d (page %d, trig %2d): %6d = knob %d' % (s + 1, s // 16 + 1, s % 16 + 1, v, v >> 8))
print('%d lanes on track %d' % (n, t + 1))
