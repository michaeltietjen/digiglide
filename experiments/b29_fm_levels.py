"""FM TONE: how bright A LEVEL / B LEVEL / FDBK / LVAB make the chain of algorithm 5 (B2 -> B1 -> A -> C, MIX X) and
whether LVAB (slot 53, AB Level, the one knob for both) acts in the DSP. Prints the spectral centroid (Hz) and level."""
import numpy as np
from b29_fmlab import render, FS
def cen(k):
    L, R = render({'ALGO': 4, 'MIX': 0, **k}, notes=(48,), blocks=720)
    x = (L + R)[6000:6000 + 16384] / 2
    s = np.abs(np.fft.rfft(x * np.hanning(len(x)))); f = np.arange(len(s)) * FS / len(x)
    return round(float((s * f).sum() / s.sum())), round(float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)), 1)
print('A LEVEL (B 0):', [(a, cen({'A LEVEL': a})) for a in (0, 10, 20, 30, 40, 60, 90, 127)], flush=True)
print('B LEVEL (A 30):', [(b, cen({'A LEVEL': 30, 'B LEVEL': b})) for b in (0, 10, 20, 30, 40, 60, 90)], flush=True)
print('LVAB raw (A 30 B 30):', [(hex(v), cen({'A LEVEL': 30, 'B LEVEL': 30, 'LVAB': ('raw', v)})) for v in (0x0000, 0x2000, 0x3000, 0x4000, 0x5000, 0x6000, 0x7f00)], flush=True)
print('FDBK (A 30 B 30):', [(v, cen({'A LEVEL': 30, 'B LEVEL': 30, 'FDBK': v})) for v in (0, 20, 40, 60, 90, 127)], flush=True)
print('HARM raw (no FM):', [(hex(v), cen({'HARM': ('raw', v)})) for v in (0x0000, 0x2000, 0x3f00, 0x4a00, 0x5900)], flush=True)
print('FILTER FREQ (A 60 B 40):', [(v, cen({'A LEVEL': 60, 'B LEVEL': 40, 'FILTER.FREQ': v})) for v in (40, 60, 80, 100, 127)], flush=True)
print('A END 0 after 0.25 s (A 60, DEC 60):', cen({'A LEVEL': 60, 'A ENV END': 0, 'A ENV DECAY': 20}), flush=True)
