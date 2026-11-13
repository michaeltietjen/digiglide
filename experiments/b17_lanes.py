"""Build 17 measurement: the lock table. Which slots the stock lock setter accepts, the no-lock value, the lane pool,
and whether a lock on a slot no machine uses reaches the frame."""
import os, sys, struct
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest, Ui
from osver import A
MACH = int(os.environ.get('DG_MACH', '0'))
s = Session(os.path.expanduser('~/dn2-workspace/build/DN2_1.12_DIGIGLIDE_16.syx'), tag='lanes17_%d' % MACH, solo=True, reserve=0)
s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=0), atk=0, on=False, mach=MACH)
h = s.k.h
pat = h.u32(A(0x42C5A9A0)); lt = pat + 97872
def idx(t=0): return bytes(h.r(lt + 20640 + 101 * t, 101))
def lane(i): return struct.unpack('>129h', bytes(h.r(lt + 2 + 258 * i, 258)))
print('mach', MACH, 'lt head', bytes(h.r(lt, 2)).hex(), 'index before', sorted(set(idx())))
s.trig(2, note=60, length=14); s.trig(6, note=64, length=14)
ctx = s.ctx0
for slot in (0, 34, 49, 65, 100, 101, 110):
    r = s.k.call(A(0x4004F8FE), [ctx, 2, slot, 0x2A00])
    i = idx()[slot] if slot < 101 else None
    print('slot %3d: setter -> %#x, index byte %s, head %s' % (slot, r & 0xFF, i, bytes(h.r(lt, 2)).hex()))
    if i is not None and i < 128:
        L = lane(i); print('     lane', i, 'step2', L[2], 'others', sorted(set(L[:2] + L[3:])))
# pool size: lock distinct slots on tracks until refused
n = 0
for t in range(16):
    for slot in range(66, 100):
        r = s.k.call(A(0x4004F8FE), [s.ctx0 + 132 * t, 4, slot, 0x1000])
        if not r & 0xFF:
            break
        n += 1
    else:
        continue
    break
used = set()
for t in range(16): used |= {b for b in idx(t) if b < 128}
print('extra lanes made before a refusal:', n, 'lanes in use', len(used), 'max index', max(used), 'refused at track', t, 'slot', slot)
