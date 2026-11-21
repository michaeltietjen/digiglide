"""Which operator is heard and who modulates whom in each FM TONE algorithm: ratios C 1, A 3, B 0.5/…; levels one at a
time; MIX left / right. Prints the partials (ratio of the note, dB)."""
import sys, time
import numpy as np
from b29_fmlab import render, partials
f0 = 261.626
t = time.time()
for algo in range(8):
    for mix, mn in ((0, 'X'), (127, 'Y')):
        for a, b, fb in ((0, 0, 0), (60, 0, 0), (0, 60, 0), (0, 0, 80)):
            L, R = render({'ALGO': algo, 'RTOC': 1 << 8, 'RTOA': 0x300, 'MIX': mix, 'A LEVEL': a, 'B LEVEL': b,
                           'FDBK': fb}, blocks=1600)
            x = (L + R) / 2
            print(f'algo {algo + 1} mix {mn} A {a:2d} B {b:2d} FB {fb:2d} rms {20*np.log10(np.sqrt(np.mean(x[16000:]**2))+1e-9):6.1f}', partials(x, f0, top=8, floor_db=-40), flush=True)
print(time.time() - t)
