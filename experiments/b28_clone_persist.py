"""Does stock rewrite a voice's sound record in the frame every block? Probe image (dg_prof bit 0 = no clone_voice):
after block 2500 DigiGlide stops copying the source voice's record; per block, how many of the reserved voices'
records (146 B at 0xda + 146 v, minus pan +128 and RSET +134) and per-voice words still equal the source's.
    DG_OS=1.12 python b28_clone_persist.py PROBE.syx"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, Ui, U16
s = Session(sys.argv[1], tag='persist', solo=True, reserve=0)
s.set_sound(Ui(vcnt=6, type=1, ext=0, glid=3, hold=1, bass=0, voic=64, drft=8, vib=4), t=12, mach=None, atk=None)
for st, note in ((0, 48), (8, 53), (16, 55), (24, 50)):
    s.trig(st, note=note, length=127, t=12)
for st in range(0, 32, 1):  s.trig(st, note=42, length=1, t=2)
h = s.k.h
srcs = []
def each(i):
    if i == 2500: h.w(s.sym['dg_prof'], (1).to_bytes(4, 'big'))
    srcs.append(h.u32(s.sym['DG'] + 8))
fr = s.play(4500, bpm=120, each=each)
def rec(f, v):
    b = bytearray(f[0xda + 146 * v: 0xda + 146 * v + 146]); b[128:130] = b'\0\0'; b[134:136] = b'\0\0'
    return bytes(b)
for lo, hi in ((2000, 2500), (2500, 2510), (2510, 3000), (3000, 4500)):
    diff, words, chg = 0, 0, 0
    for i in range(lo, hi):
        f, src = fr[i], srcs[i] if srcs[i] < 6 else 0
        for v in range(6):
            diff += rec(f, v) != rec(f, src)
            words += any(U16(f, o + 2 * v) != U16(f, o + 2 * src) for o in (0x34, 0x54, 0x94, 0xa5a))
        chg += rec(f, src) != rec(fr[i - 1], src)
    print(f'blocks {lo}..{hi}: voice records differing from the source {diff}, per-voice words {words}; source record changed from the block before {chg}', flush=True)
