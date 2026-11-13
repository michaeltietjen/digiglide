"""DigiGlide audio-ISR cost: instructions per ISR, stock vs DigiGlide, across a fresh chord and a chord change (GLID
1/4, defaults otherwise: Seventh, VCNT 5, DRFT 8, VIB 4). Reports mean / p99 / max and the trig blocks separately.
    ~/dn2-workspace/repos/digikit/.venv/bin/python isr_cost_dg.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dgkit import Session, latest, G, edges


def measure(img):
    s = Session(img, tag='isr')
    s.trig(0); s.trig(4); s.trig(8)
    if img:
        s.set_sound(G.Params(key=0, scl=1, deg=0, vcnt=5, glid=3))
        for st_, d in ((0, 0), (4, 5), (8, 3)):
            s.lock(st_, deg=d)
    fe = s.k.h.fastemu
    orig = fe.run_isr
    counts = []

    def wrap(*a, **kw):
        n, ok = orig(*a, **kw)
        counts.append(n)
        return n, ok
    fe.run_isr = wrap
    fr = s.play(2600, bpm=120)
    fe.run_isr = orig
    return np.array(counts), fr


img = sys.argv[1] if len(sys.argv) > 1 else latest()
st, _ = measure(None)
dg, fr = measure(img)
n = min(len(st), len(dg))
st, dg = st[:n], dg[:n]
add = dg.astype(int) - st.astype(int)
print(f'ISRs measured: {n}')
for name, c in (('stock', st), ('DigiGlide', dg)):
    print(f'{name:9s} instr/ISR: mean {c.mean():8.0f}  p99 {np.percentile(c, 99):8.0f}  max {c.max():8.0f}')
order = np.argsort(add)[::-1][:6]
print('DigiGlide adds: mean %.0f, median %.0f; largest additions (ISR index: instructions): %s' % (
    add.mean(), np.median(add), ', '.join(f'{i}: {add[i]}' for i in order)))
