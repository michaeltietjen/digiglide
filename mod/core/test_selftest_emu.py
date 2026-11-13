"""M2: the core built for the ColdFire, run inside the emulated OS (cfkit), against the host build.
Every 200 blocks the ColdFire's running hash must equal the host's for the same blocks. Also counts instructions
per block (a plain block, and a trig block) with a code hook.
    $DIGIKIT/.venv/bin/python test_selftest_emu.py      (after build_selftest.py)"""
import ctypes, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
import dn2paths as P
import test_equiv as T

CHUNK = 200
src = open(os.path.join(HERE, 'selftest_events.h')).read()
cases = [tuple(int(x) for x in m.split(',')) for m in re.findall(r'\{(-?\d+(?:, -?\d+){4})\},', src.split('ST_EV')[0])]
seeds = [int(x) for x in re.search(r'seeds \[([^\]]*)\]', src).group(1).split(',')]
sym = {}
for line in open(P.BUILD / 'DG_SELFTEST' / 'symbols.txt'):
    a, n = line.split()[:2]
    sym[n] = int(a, 16)

T.build()
lib = ctypes.CDLL(T.LIB)


def host_hashes(seed, nb):
    tw, pat, ev, _ = T.case(seed)
    ev = [e for e in ev if e[0] < nb]
    rows = [[b, k, s, v] + ([p[f] for f in T.FIELDS] if p else [0] * 16) for b, k, s, v, p in ev]
    arr = np.array(rows, np.int32).reshape(-1)
    pitch = np.zeros(nb * 6, np.int32); mask = np.zeros(nb, np.uint32); notes = np.zeros(nb * 6, np.int32)
    Pt = ctypes.POINTER
    lib.dg_sim(arr.ctypes.data_as(Pt(ctypes.c_int32)), len(rows), nb, tw, pat, pitch.ctypes.data_as(Pt(ctypes.c_int32)),
               mask.ctypes.data_as(Pt(ctypes.c_uint32)), notes.ctypes.data_as(Pt(ctypes.c_int32)))
    started = (mask[:, None] >> np.arange(6)) & 1
    pitch = np.where(started == 1, pitch.reshape(nb, 6), 0).astype(np.uint32)
    h, out = 2166136261, []
    for b in range(nb):
        for v in pitch[b]:
            h = ((h ^ int(v)) * 16777619) & 0xFFFFFFFF
        h = ((h ^ int(mask[b])) * 16777619) & 0xFFFFFFFF
        if (b + 1) % CHUNK == 0 or b + 1 == nb:
            out.append(h)
    return out, [e[0] for e in ev if e[1] == 0]


os.chdir(P.DIGIKIT)
import cfkit  # noqa: E402
k = cfkit.Kit(str(P.BUILD / 'DG_SELFTEST' / 'section_3.bin'), str(P.STOCK), None, str(P.BUILD / 'dg_selftest_emu'))
ok = True
for c, ((tw, pat, first, nev, nb), seed) in enumerate(zip(cases, seeds)):
    want, trigs = host_hashes(seed, nb)
    k.call(sym['dg_selftest_start'], [c])
    got = []
    for _ in range(len(want)):
        got.append(k.call(sym['dg_selftest_run'], [CHUNK]) & 0xFFFFFFFF)
    same = got == want
    ok &= same
    bad = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), None)
    print(f'case {c} (seed {seed}, {nb} blocks, {len(trigs)} trigs, BPM {tw / 120:.2f}): ColdFire == host '
          f'{"yes" if same else "NO, first differing chunk %d (blocks %d..)" % (bad, bad * CHUNK)}')

# instruction counts: replay case 0 one block per call; fastemu.run_until returns the instructions it ran
fe = k.h.fastemu
orig = fe.run_until
last = [0]


def counting(*a, **kw):
    r = orig(*a, **kw)
    last[0] = r[0] if isinstance(r, tuple) else r
    return r


fe.run_until = counting
tw, pat, first, nev, nb = cases[0]
_, trigs = host_hashes(seeds[0], nb)
k.call(sym['dg_selftest_start'], [0])
per = []
for b in range(min(nb, 2400)):
    k.call(sym['dg_selftest_run'], [1])
    per.append((b, last[0]))
k.call(sym['dg_selftest_start'], [0])
base = []
for b in range(20):
    k.call(sym['dg_selftest_run'], [0])
    base.append(last[0])
fe.run_until = orig
off = int(np.median(base))                       # the call itself with no block run
per = [(b, n - off) for b, n in per]
plain = [n for b, n in per if b not in trigs]
trig = [n for b, n in per if b in trigs]
print(f'instructions per block (6 voices, self-test loop included, call overhead {off} removed): median {int(np.median(plain))}, max {max(plain)}; '
      f'trig blocks: {trig}')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
