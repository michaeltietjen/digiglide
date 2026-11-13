"""DigiGlide M4: which [FUNC] + page key combos does stock 1.11 leave unused? For each key K near SYN: from the SYN
page, tap K alone (session A) and hold FUNC + tap K (session B): an unused combo leaves the same screen as K alone."""
import os, sys, hashlib
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session
import cfkit
OUT = os.path.expanduser('~/glide/experiments/out/m4/combos')
os.makedirs(OUT, exist_ok=True)
FUNC = cfkit.KEYS['FUNC']
for key in ('TRIG', 'FLTR', 'AMP', 'FX', 'LFO'):
    res = {}
    for mode in ('plain', 'func'):
        s = Session(None, tag=f'combo_{key}_{mode}', solo=False)
        k = s.k; h = k.h; h.out = OUT
        k.tap('SYN'); h.frames(10)
        if mode == 'func':
            h.press(FUNC, 500_000); h.frames(20)
            k.tap(key); h.frames(20)
            h.release(FUNC); h.frames(20)
        else:
            k.tap(key); h.frames(40)
        h.run(100_000_000)
        h.png(f'{key}_{mode}.png')
        res[mode] = hashlib.md5(open(os.path.join(OUT, f'{key}_{mode}.png'), 'rb').read()).hexdigest()[:8]
    print(f'{key}: plain {res["plain"]} func {res["func"]} -> {"SAME as plain" if res["plain"] == res["func"] else "DIFFERENT"}')
