"""Sound pack calibration, second pass (calibrate.py first): the low end of the cutoff curves (reference band 25..50
Hz), attack above knob 112, and the combs read from the autocorrelation: the comb's delay is the strongest |peak| after
lag 0; COMB+ (positive feedback) gives a positive peak there, COMB- a negative one; its frequency is 1 / delay.
Merges into pack/calibration.json.
    ~/dn2-workspace/repos/digikit/.venv/bin/python calibrate2.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dsplab import render, mono, cutoff, env, NOISE, SINE, FS

J = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calibration.json')
res = json.load(open(J))
res['combs'] = {}
for ft in (3, 5):
    for knob in (48, 64, 80):
        x = mono(render({**NOISE, 67: knob, 68: 110, 66: 127}, ftype=ft, blocks=1600))
        seg = x[FS // 4:FS // 4 + 32768] - np.mean(x[FS // 4:FS // 4 + 32768])
        ac = np.correlate(seg, seg, 'full')[len(seg) - 1:]
        ac /= ac[0]
        lo = 12                                          # skip the first lags (the noise's own width)
        k = lo + int(np.argmax(np.abs(ac[lo:4000])))
        res['combs'].setdefault(str(ft), {})[knob] = dict(delay_samples=k, freq_hz=FS / k, sign=float(np.sign(ac[k])),
                                                          strength=float(ac[k]))
        print(f'filter type {ft} FREQ {knob}: delay {k} samples ({FS / k:.0f} Hz), autocorrelation {ac[k]:+.2f}')
for ft, extra, name in ((0, {66: 0, 68: 0}, 'MULTIMODE'), (1, {68: 0}, 'LOWPASS 4')):
    for knob in (40, 48, 56, 64, 72, 80):
        res['cutoff_hz'][name][str(knob)] = cutoff(mono(render({**NOISE, **extra, 67: knob}, ftype=ft, blocks=1700)))
    print(name, {k: round(v) for k, v in sorted(res['cutoff_hz'][name].items(), key=lambda kv: int(kv[0]))})
for knob in (120, 127):
    x = mono(render({**SINE, 'AMP.ATK': knob, 'AMP.REL': 0}, blocks=int(16 * 1500)))
    e, dt = env(x)
    held = np.median(e[-200:])
    res['amp_attack_s'][str(knob)] = float(np.argmax(e >= 0.9 * held) * dt - 64 / FS)
print('attack', {k: round(v, 3) for k, v in sorted(res['amp_attack_s'].items(), key=lambda kv: int(kv[0]))})
json.dump(res, open(J, 'w'), indent=1)
print('wrote', J)
