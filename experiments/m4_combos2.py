"""DigiGlide M4: stock 1.11's [FUNC] + PAGE / VOICE / STACK / PRESET / ARP, against the plain key, from the SYN page.
FUNC is (2, 0); keys in FUNC's own button group are pressed with FUNC kept in the group's state byte."""
import os, sys, hashlib
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session
from emu import panelin
OUT = os.path.expanduser('~/glide/experiments/out/m4/combos')
os.makedirs(OUT, exist_ok=True)
CODES = {'PAGE': 22, 'VOICE': 50, 'STACK': 53, 'PRESET': 7, 'ARP': 51}
pos = lambda code: ((code - 1) // 8, (code - 1) % 8)


def press(h, ch, bit, held=0, n=500_000):
    h.pc = panelin.press(h.m, h.profile, ch, bit, held); h.run(n)


def release(h, ch, bit, held=0, n=15_000_000):
    h.pc = panelin.release(h.m, h.profile, ch, bit, held); h.run(n)


for name, code in CODES.items():
    ch, bit = pos(code)
    res = {}
    for mode in ('plain', 'func'):
        s = Session(None, tag=f'combo2_{name}_{mode}', solo=False)
        k = s.k; h = k.h; h.out = OUT
        k.tap('SYN'); h.frames(10)
        if mode == 'func':
            press(h, 2, 0); h.frames(20)
            held = 1 if ch == 2 else 0
            press(h, ch, bit, held); h.frames(20); release(h, ch, bit, held); h.frames(20)
            release(h, 2, 0); h.frames(20)
        else:
            press(h, ch, bit); h.frames(20); release(h, ch, bit); h.frames(20)
        h.run(100_000_000)
        h.png(f'{name}_{mode}.png')
        res[mode] = hashlib.md5(open(os.path.join(OUT, f'{name}_{mode}.png'), 'rb').read()).hexdigest()[:8]
    print(f'{name} ({ch},{bit}): plain {res["plain"]} func {res["func"]} -> '
          f'{"SAME as plain" if res["plain"] == res["func"] else "DIFFERENT"}')
