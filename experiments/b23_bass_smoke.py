"""Build 23 smoke run: a held C MIN7 chord (HOLD on, 5 voices, BASS FOL), BPAT and BRATE from argv, 120 BPM. Prints
the bass voice's note-ons: block, note, RSET, level word, gate length."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16

img, bpat, brate = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
bpm = int(sys.argv[4]) if len(sys.argv) > 4 else 120
K_BPAT, K_BRATE = 19, 20
s = Session(img, tag=f'b23bs_{bpat}_{brate}_{bpm}', solo=True)
s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, voic=64, bass=3, hold=1), t=0, mach=None, atk=None)
s.k.call(s.sym['dg_par_set'], [0, K_BPAT, bpat << 8])
s.k.call(s.sym['dg_par_set'], [0, K_BRATE, brate << 8])
print('read back', s.k.call(s.sym['dg_par'], [0, K_BPAT]) >> 8, s.k.call(s.sym['dg_par'], [0, K_BRATE]) >> 8)
s.trig(0, note=48, length=30, t=0)
fr = s.play(2400, bpm=bpm)
ons, offs = {}, {}
for b, f in enumerate(fr):
    on, off = U16(f, 0x22), U16(f, 0x24)
    for v in range(6):
        if on >> v & 1:
            ons.setdefault(v, []).append((b, (U16(f, 2 + 2 * v) + 128) >> 8, U16(f, 0xDA + 146 * v + 134), U16(f, 0x74 + 2 * v)))
        if off >> v & 1:
            offs.setdefault(v, []).append(b)
for v in sorted(ons):
    print('voice', v, 'ons', ons[v][:12])
    print('        offs', offs.get(v, [])[:12])
print('strikes', s.k.h.u32(s.sym['dg_bp_strikes']))
