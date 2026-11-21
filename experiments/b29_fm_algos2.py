"""FM TONE algorithms, second pass. Carriers by exact frequency (ratio offsets: C +0.010, A +0.020, B1 +0.030,
B2 +0.040 if an offset unit is 1/1000 ratio... measured here), and what FDBK acts on (A 40 or B 40, FDBK 0 / 90)."""
import numpy as np
from b29_fmlab import render, FS
f0 = 261.626
def peaks(x, n=65536, top=6, floor=-45):
    seg = x[12000:12000 + n] * np.hanning(n)
    s = np.abs(np.fft.rfft(seg)); s /= s.max()
    out = []
    for i in np.argsort(-s):
        if 20 * np.log10(s[i] + 1e-12) < floor or len(out) >= top: break
        if 0 < i < len(s) - 1 and s[i] >= s[i - 1] and s[i] >= s[i + 1]:
            a, b, c = np.log(s[i - 1] + 1e-12), np.log(s[i]), np.log(s[i + 1] + 1e-12)
            d = 0.5 * (a - c) / (a - 2 * b + c)
            out.append((round((i + d) * FS / n / f0, 4), round(20 * np.log10(s[i]), 1)))
    return sorted(out)
OFF = {'COFF': 0x4000 + 1000, 'AOFF': 0x4000 + 2000, 'B1OF': 0x4000 + 3000, 'B2OF': 0x4000 + 4000}
def hf(x):
    s = np.abs(np.fft.rfft(x[12000:12000 + 32768] * np.hanning(32768)))
    f = np.arange(len(s)) * FS / 32768
    return round(float((s * f).sum() / s.sum()))
for algo in range(8):
    for mix, mn in ((0, 'X'), (127, 'Y')):
        L, R = render({'ALGO': algo, 'MIX': mix, **OFF}, blocks=2500)
        print(f'algo {algo + 1} {mn} carriers', peaks((L + R) / 2), flush=True)
    for a, b in ((50, 0), (0, 50)):
        row = []
        for fb in (0, 90):
            for mix in (0, 127):
                L, R = render({'ALGO': algo, 'MIX': mix, 'A LEVEL': a, 'B LEVEL': b, 'FDBK': fb}, blocks=1500)
                row.append(hf((L + R) / 2))
        print(f'algo {algo + 1} A {a} B {b}: centroid Hz  FB0 X {row[0]} Y {row[1]}   FB90 X {row[2]} Y {row[3]}', flush=True)
