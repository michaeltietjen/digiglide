"""Stock 1.11: does [FUNC] + [ARP] (panel group 6, bit 4) change any state? Two sessions from the same snapshot, the
same emulated time: one presses FUNC + ARP, the control presses nothing. Diff: the app object (451,596 B at
*0x446478d0), the 16 live sounds, the arp state (0x405984a8, 40 B a track), the playing pattern (128 KB)."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session
from emu import panelin


def regions(h):
    app = h.u32(0x446478D0); snd = h.u32(0x800052A0); pat = h.u32(0x42C5A9A0)
    return {'app': (app, 451596), 'sounds': (snd, 52 + 1163 * 16), 'arp': (0x405984A8, 40 * 16), 'pattern': (pat, 131072)}


snaps = {}
for mode in sys.argv[1:] or ('control', 'funcarp'):
    s = Session(None, tag='funcarp_' + mode, solo=False)
    k = s.k; h = k.h
    k.tap('SYN'); h.frames(10)
    if mode.startswith('funcarp'):
        h.pc = panelin.press(h.m, h.profile, 2, 0); h.run(500_000); h.frames(20)
        h.pc = panelin.press(h.m, h.profile, 6, 4); h.run(500_000); h.frames(20)
        h.pc = panelin.release(h.m, h.profile, 6, 4); h.run(15_000_000); h.frames(20)
        h.pc = panelin.release(h.m, h.profile, 2, 0); h.run(15_000_000); h.frames(20)
    else:
        h.run(500_000); h.frames(20); h.run(500_000); h.frames(20); h.run(15_000_000); h.frames(20)
        h.run(15_000_000); h.frames(20)
    h.run(100_000_000)
    snaps[mode] = {n: bytes(h.r(a, ln)) for n, (a, ln) in regions(h).items()}
m1, m2 = list(snaps)
print('byte 403 of the sounds:', {m: snaps[m]['sounds'][403] for m in snaps})
for n in snaps[m1]:
    a, b = snaps[m1][n], snaps[m2][n]
    d = [i for i in range(len(a)) if a[i] != b[i]]
    print(f'{n:8s}: {len(d)} bytes differ' + (f' at offsets {d[:16]}' if d else ''))
