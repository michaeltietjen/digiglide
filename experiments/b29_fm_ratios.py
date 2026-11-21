"""FM TONE ratio tables by ear of the emulator: RTOA (algorithm 5, MIX Y: A is heard), RTOC (MIX X), RTOB (B1: algorithm
2 MIX Y; B2: algorithm 3 MIX X, next to C), and the offsets' and DTUN's scale. Prints frequency / note frequency."""
import numpy as np
from b29_fmlab import render, FS
f0 = 261.626
def peaks(x, n=16384, top=3, floor=-30):
    seg = x[6000:6000 + n] * np.hanning(n)
    s = np.abs(np.fft.rfft(seg)); s /= s.max()
    out = []
    for i in np.argsort(-s):
        if 20 * np.log10(s[i] + 1e-12) < floor or len(out) >= top: break
        if 0 < i < len(s) - 1 and s[i] >= s[i - 1] and s[i] >= s[i + 1]:
            a, b, c = np.log(s[i - 1] + 1e-12), np.log(s[i]), np.log(s[i + 1] + 1e-12)
            out.append(round((i + 0.5 * (a - c) / (a - 2 * b + c)) * FS / n / f0, 4))
    return sorted(out)
def one(k):
    L, R = render(k, blocks=720)
    return peaks((L + R) / 2)
print('RTOC', [one({'ALGO': 4, 'MIX': 0, 'RTOC': ('raw', i << 8)})[0] for i in (0, 1, 2, 3, 4, 5, 17, 18)], flush=True)
print('RTOA', [one({'ALGO': 4, 'MIX': 127, 'RTOA': ('raw', i << 8)})[0] for i in (0, 1, 2, 3, 4, 5, 6, 7, 8, 20, 34, 35)], flush=True)
for raw in (0, 1, 2, 3, 24, 25, 26, 48, 96, 120, 121, 144, 145, 168, 240, 480, 719, 720):
    b1 = one({'ALGO': 1, 'MIX': 127, 'RTOB': ('raw', raw)})
    b2 = one({'ALGO': 2, 'MIX': 0, 'RTOB': ('raw', raw), 'RTOC': ('raw', 0x100)})
    print('RTOB raw', raw, 'B1', b1, 'C 0.5 + B2', b2, flush=True)
for name in ('COFF',):
    print('COFF raw +16, +164, -164:', [one({'ALGO': 4, 'MIX': 0, name: ('raw', 0x4000 + d)})[0] for d in (16, 164, -164)], flush=True)
print('DTUN 0, 20, 64, 127 (algo 2, X and Y):', [(one({'ALGO': 1, 'MIX': 0, 'DTUN': d}), one({'ALGO': 1, 'MIX': 127, 'DTUN': d})) for d in (1, 20, 64, 127)], flush=True)
