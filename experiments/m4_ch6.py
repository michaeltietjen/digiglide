"""Stock 1.11: what each button of panel group 6 does (plain press), and the same with [FUNC] held."""
import os, sys, hashlib
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session
from emu import panelin
OUT = os.path.expanduser('~/glide/experiments/out/m4/combos')
mode = sys.argv[1]
for bit in range(8):
    s = Session(None, tag=f'ch6_{bit}_{mode}', solo=False)
    k = s.k; h = k.h; h.out = OUT
    k.tap('SYN'); h.frames(10)
    if mode == 'func':
        h.pc = panelin.press(h.m, h.profile, 2, 0); h.run(500_000); h.frames(20)
    h.pc = panelin.press(h.m, h.profile, 6, bit); h.run(500_000); h.frames(20)
    h.pc = panelin.release(h.m, h.profile, 6, bit); h.run(15_000_000); h.frames(20)
    if mode == 'func':
        h.pc = panelin.release(h.m, h.profile, 2, 0); h.run(15_000_000); h.frames(20)
    h.run(100_000_000)
    h.png(f'ch6_{bit}_{mode}.png')
    print(mode, bit, hashlib.md5(open(os.path.join(OUT, f'ch6_{bit}_{mode}.png'), 'rb').read()).hexdigest()[:8])
