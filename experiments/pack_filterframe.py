"""Sound pack groundwork: how does the frame tell the DSP a voice's filter machine? The demo plays; for every note-on:
the voice's track, that track's sound byte +0xDF, and the voice's per-voice frame words."""
import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, U16
s = Session(None, tag='pack_fframe', solo=False)
k = s.k
fb = {t: k.h.r(k.sound(t) + 0xDF, 1)[0] for t in range(16)}
fr = s.play(1500, bpm=120)
seen = {}
for i, f in enumerate(fr):
    on = U16(f, 0x22)
    for v in range(16):
        if (on >> v) & 1:
            t = U16(f, 0xA5A + 2 * v)
            if t in seen:
                continue
            seen[t] = (v, [hex(U16(f, o + 2 * v)) for o in (0x54, 0x74, 0x94, 0xB4)])
for t in sorted(seen):
    v, w = seen[t]
    print(f'track {t + 1:2d} filter byte {fb[t]}: voice {v:2d} words +0x54/+0x74/+0x94/+0xB4 {w}')
# other per-voice areas: look for any 32-byte block in the header whose values match the filter bytes of the voices
