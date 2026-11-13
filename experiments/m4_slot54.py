"""DigiGlide M4: on STOCK OS, what does a WAVETONE sound hold in slots 50..64 (VCNT would be slot 54)?
Demo project tracks as loaded, then machine changes FM TONE -> WAVETONE and WAVETONE -> FM TONE -> WAVETONE."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session
s = Session(None, tag='slot54', solo=False)
k = s.k
NAMES = ['FMT', 'WAV', 'FMD', 'SWM', 'MID']
sl = lambda t: [k.slot(t, x) for x in range(50, 65)]
print('demo project, as loaded:')
for t in range(16):
    m = k.mach(t)
    print(f'  track {t + 1:2d} {NAMES[m] if m < 5 else m}: slot54 {k.slot(t, 54):#06x}  50..64', ' '.join(f'{v:04x}' for v in sl(t)))
fm = next(t for t in range(16) if k.mach(t) == 0)
wt = next(t for t in range(16) if k.mach(t) == 1)
k.select(1, track=fm)
print(f'track {fm + 1} FM TONE -> WAVETONE: machine {k.mach(fm)}, slot54 {k.slot(fm, 54):#06x}, 50..64', ' '.join(f'{v:04x}' for v in sl(fm)))
k.select(0, track=wt); k.select(1, track=wt)
print(f'track {wt + 1} WAVETONE -> FM TONE -> WAVETONE: machine {k.mach(wt)}, slot54 {k.slot(wt, 54):#06x}, 50..64', ' '.join(f'{v:04x}' for v in sl(wt)))
