"""DigiGlide's own work per audio frame, split by what the frame carries: mod code bytes run inside the audio ISR
(unicorn block hook over the mod's address range; about 3.3 bytes an instruction), on frames with note-ons (stock's
before the hook, or any after it) and on quiet frames. The owner's layout: DigiGlide on track 13, kick / snare /
16th hats / bass on tracks 1..4, the chord trigs on the same steps as kick and bass.
    DG_OS=1.12 python b28_hook.py IMAGE.syx [key=val ...]     (Ui fields: play=2 bass=2 bloom=100 ...)"""
import os, sys, bisect
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
import numpy as np
from unicorn import UC_HOOK_BLOCK
from dgkit import Session, Ui, U16
from osver import A

def measure(img, blocks=6000, **kw):
    dgt = 12
    s = Session(img, tag='hook_' + '_'.join(f'{k}{v}' for k, v in kw.items()), solo=True, reserve=0)
    u = dict(vcnt=6, type=1, ext=0, glid=3, hold=1, bass=0, voic=64, drft=8, vib=4); u.update(kw)
    s.set_sound(Ui(**u), t=dgt, mach=None, atk=None)
    for st, note in ((0, 48), (8, 53), (16, 55), (24, 50)):
        s.trig(st, note=note, length=127, t=dgt)
    for st in range(0, 32, 4):  s.trig(st, note=36, length=2, t=0)
    for st in range(4, 32, 8):  s.trig(st, note=38, length=2, t=1)
    for st in range(0, 32, 1):  s.trig(st, note=42, length=1, t=2)
    for st in range(0, 32, 2):  s.trig(st, note=36 + st % 12, length=6, t=3)
    addrs = sorted(a for a in s.sym.values() if 0x40000000 <= a < 0x48000000)
    lo, hi = addrs[0], addrs[-1] + 0x4000
    per, pre, cur, inisr = [], [], [0], [False]
    def blk(uc, addr, size, _):
        if inisr[0]:
            cur[0] += size
    h = s.k.h
    h.m.uc.hook_add(UC_HOOK_BLOCK, blk, begin=lo, end=hi)
    fe = h.fastemu
    orig = fe.run_isr
    FR = A(0x80005E60)
    def wrap(*a, **k2):
        inisr[0] = True; cur[0] = 0
        pre.append(int.from_bytes(h.r(FR + 0x22, 2), 'big'))
        r = orig(*a, **k2)
        inisr[0] = False; per.append(cur[0])
        return r
    fe.run_isr = wrap
    fr = s.play(blocks, bpm=120)
    fe.run_isr = orig
    n = len(fr)
    per, pre = np.array(per[-n:]), np.array(pre[-n:])
    post = np.array([U16(f, 0x22) for f in fr])
    dgon = np.array([sum(1 for v in range(16) if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) == dgt) for f in fr])
    lost = {}
    ons = [0] * 16
    for f in fr:
        for v in range(16):
            if U16(f, 0x22) >> v & 1:
                ons[min(U16(f, 0xA5A + 2 * v), 15)] += 1
    extra = {}
    for nm in ('dg_forced', 'dg_defer_max', 'dg_events_deferred'):
        if nm in s.sym:
            extra[nm] = h.u32(s.sym[nm])
    return per, pre, post, dgon, ons, extra

if __name__ == '__main__':
    img = sys.argv[1]
    kw = {k: int(v) for k, v in (a.split('=') for a in sys.argv[2:])}
    per, pre, post, dgon, ons, extra = measure(img, **kw)
    n = os.path.basename(img)[:-4].rsplit('_', 1)[-1]
    note = (pre != 0) | (post != 0)
    stock = pre != 0
    def st(x):
        return f'n {len(x):5d}  median {np.median(x):6.0f}  p99 {np.percentile(x, 99):6.0f}  max {x.max():6d}' if len(x) else 'none'
    tag = f'[{n}] {kw}'
    print(f'{tag}: all frames            {st(per)}')
    print(f'{tag}: frames with note-ons  {st(per[note])}')
    print(f'{tag}:   with stock note-ons {st(per[stock])}')
    print(f'{tag}: quiet frames          {st(per[~note])}')
    print(f'{tag}: note-ons kick {ons[0]} snare {ons[1]} hats {ons[2]} bass {ons[3]} DigiGlide {ons[12]}  {extra}', flush=True)
