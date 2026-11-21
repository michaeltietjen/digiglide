"""Where DigiGlide's audio-ISR time goes: bytes of mod code executed per ISR, by function (unicorn block hook over the
mod's own address range), for the owner's layout (b28_isr.py). Bytes / ~3.3 = instructions.
    DG_OS=1.12 python b28_profile.py IMAGE.syx [key=val ...]"""
import os, sys, bisect
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
import numpy as np
from unicorn import UC_HOOK_BLOCK
from dgkit import Session, Ui

img = sys.argv[1]
kw = {k: int(v) for k, v in (a.split('=') for a in sys.argv[2:])}
dgt = 12
s = Session(img, tag='prof_' + '_'.join(f'{k}{v}' for k, v in kw.items()), solo=True, reserve=0)
u = dict(vcnt=6, type=1, ext=0, glid=3, hold=1, bass=0, voic=64, drft=8, vib=4); u.update(kw)
s.set_sound(Ui(**u), t=dgt, mach=None, atk=None)
for st, note in ((0, 48), (8, 53), (16, 55), (24, 50)):
    s.trig(st, note=note, length=127, t=dgt)
for st in range(0, 32, 4):  s.trig(st, note=36, length=2, t=0)
for st in range(4, 32, 8):  s.trig(st, note=38, length=2, t=1)
for st in range(0, 32, 1):  s.trig(st, note=42, length=1, t=2)
for st in range(0, 32, 2):  s.trig(st, note=36 + st % 12, length=6, t=3)
syms = sorted((a, n) for n, a in s.sym.items() if 0x40000000 <= a < 0x48000000)
addrs = [a for a, _ in syms]
lo, hi = addrs[0], addrs[-1] + 0x4000
print('symbols', len(syms), hex(lo), hex(hi))
tot, per, cur, inisr = {}, [], [0], [False]
one, spike = {}, {}
def blk(uc, addr, size, _):
    if not inisr[0]:
        return
    i = bisect.bisect_right(addrs, addr) - 1
    n = syms[i][1] if i >= 0 else '?'
    tot[n] = tot.get(n, 0) + size
    one[n] = one.get(n, 0) + size
    cur[0] += size
uc = s.k.h.m.uc
uc.hook_add(UC_HOOK_BLOCK, blk, begin=lo, end=hi)
fe = s.k.h.fastemu
orig = fe.run_isr
def wrap(*a, **k2):
    inisr[0] = True; cur[0] = 0; one.clear()
    r = orig(*a, **k2)
    inisr[0] = False; per.append(cur[0])
    if cur[0] > 38000:
        spike['_n'] = spike.get('_n', 0) + 1
        for a, b in one.items(): spike[a] = spike.get(a, 0) + b
    return r
fe.run_isr = wrap
fr = s.play(4000, bpm=120)
fe.run_isr = orig
p = np.array(per[-len(fr):]); p = p[p > 0]
n = os.path.basename(img)[:-4].rsplit('_', 1)[-1]
print(f'[{n}] {kw}: mod bytes per ISR: median {np.median(p):.0f} p90 {np.percentile(p, 90):.0f} p99 {np.percentile(p, 99):.0f} max {p.max()}')
T = sum(tot.values())
for name, b in sorted(tot.items(), key=lambda x: -x[1])[:22]:
    print(f'  {name:28s} {b:10d} bytes  {100 * b / T:5.1f} %')

ns = spike.pop('_n', 0)
print('spike ISRs (over 38000 mod bytes):', ns)
for name, b in sorted(spike.items(), key=lambda x: -x[1])[:14]:
    print(f'  {name:28s} {b / max(ns, 1):9.0f} bytes each   (all ISRs: {tot[name] / len(p):7.0f})')
