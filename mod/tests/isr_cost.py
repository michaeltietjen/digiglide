"""ColdFire audio-ISR cost of GLIDE: instructions per ISR, stock vs GLIDE, across a held chord change (GLID 1/4)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from glidekit import Session, params, latest

def measure(img):
    s = Session(img, tag='isr')
    s.trig(0); s.trig(4)
    s.progression([params('C3', 'maj', glid='1/4', drft=20), params('A2', 'min', glid='1/4', drft=20)])
    fe = s.k.h.fastemu; orig = fe.run_isr; counts = []
    def wrap(*a, **kw):
        n, ok = orig(*a, **kw); counts.append(n); return n, ok
    fe.run_isr = wrap
    s.play(1600, bpm=120)
    return np.array(counts[5:1500])

st, gl = measure(None), measure(latest())
for name, c in (('stock', st), ('GLIDE', gl)):
    print(f'{name:6s} instr/ISR: mean {c.mean():8.0f}  p99 {np.percentile(c, 99):8.0f}  max {c.max():8.0f}')
print(f'GLIDE adds mean {gl.mean() - st.mean():.0f}, max {gl.max() - st.max():.0f} instructions per ISR')
