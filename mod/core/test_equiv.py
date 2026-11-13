"""M2 test: the C core (dg_core.c, host build) against the M1 Python model, block by block.

1,000 seeded random progressions: every value of every parameter (KEY, SCL, DEG, CHRD, VCNT, BASS, SPRD, MOVE, GLID,
PATH, TIME, ORDR, STAG, DRFT, VIB, SCRB), random tempo (60..240 BPM, fractional), trig notes, gate-offs and SCRB
moves between trigs. Pass: the same voices started and gated, the same target note on every voice in every block
("note for note"), and every pitch within 0.1 cent, except that a Semitones staircase step may land one block
earlier or later (counted and reported).
    python3 test_equiv.py [n] [first seed]
"""
import collections, ctypes, os, random, subprocess, sys, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'model'))
import numpy as np  # noqa: E402
import digiglide as G  # noqa: E402

LIB = os.path.join(HERE, 'build', 'libdgcore_host.dylib')
TOL = 0.1                       # cents
NV = 6
FIELDS = list(G.Params.FIELDS)
RANGES = dict(key=12, scl=4, voic=128, pos=128, vcnt=(3, 6), bass=7, sprd=128, move=10, glid=13, path=10, time=5,
              ordr=5, stag=7, drft=51, vib=51, scrb=128)


def build():
    os.makedirs(os.path.dirname(LIB), exist_ok=True)
    src = [os.path.join(HERE, f) for f in ('dg_core.c', 'dg_sim.c')]
    if not os.path.exists(LIB) or any(os.path.getmtime(s) > os.path.getmtime(LIB) for s in src + [os.path.join(HERE, 'dg_core.h')]):
        subprocess.check_call(['clang', '-O2', '-std=c11', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                               '-o', LIB] + src)


def case(seed):
    r = random.Random(seed)
    tw = r.randint(60 * 120, 240 * 120)
    sixteenth = 2700000.0 / tw
    ev, b = [], 0
    for k in range(r.randint(3, 8)):
        p = {}
        for f in FIELDS:
            rg = RANGES[f]
            p[f] = r.randint(*rg) if isinstance(rg, tuple) else r.randrange(rg)
        if r.random() < 0.4:
            p['move'] = 0
        if r.random() < 0.75:
            p['scrb'] = 127
        if r.random() < 0.5:
            p['glid'] = r.randrange(0, 8)
        # the chord word (dg_core.h DG_CW): the root as played, the chord's pitch classes (half from chord_for,
        # half any 2..5 classes), and the tail / revoice flags
        root = r.randint(24, 96) if r.random() < 0.9 else r.randint(0, 127)
        if r.random() < 0.5:
            pcs_set = G.chord_for(root, r.randrange(4), r.randrange(8), r.randrange(25))[0]
        else:
            pcs_set = set(r.sample(range(12), r.randint(2, 5)))
        pcs = sum(1 << x for x in pcs_set)
        flags = ((1 << 24) if r.random() < 0.3 else 0) | ((1 << 25) if r.random() < 0.15 else 0)
        ev.append((b, 0, k * 4 + r.randrange(4), pcs | root << 12 | flags, p))
        nxt = int(round(r.choice([1, 2, 4, 8, 16, 32]) * sixteenth))
        if r.random() < 0.2:
            ev.append((b + r.randint(1, max(1, nxt - 1)), 1, 0, 0, None))
        if r.random() < 0.15:
            ev.append((b + r.randint(1, max(1, nxt - 1)), 2, 0, r.randrange(128), None))
        b += max(2, nxt)
    ev.sort(key=lambda e: (e[0], e[1] != 0))         # a trig before an off / scrb in the same block
    n_blocks = b + r.randint(1500, 4500)
    return tw, r.randrange(128), ev, n_blocks


def run_python(tw, pattern, ev, n_blocks):
    m = G.DigiGlide(tw / 120.0, pattern)
    by = collections.defaultdict(list)
    for e in ev:
        by[e[0]].append(e)
    pitch = np.full((n_blocks, NV), np.nan)
    gate = np.zeros((n_blocks, NV), bool)
    notes = np.zeros((n_blocks, NV), np.int64)
    for b in range(n_blocks):
        for _, kind, step, val, p in by.get(b, []):
            if kind == 0:
                pcs = {x for x in range(12) if val >> x & 1}
                m.trig(step, G.Params(**p), (val >> 12) & 0x7F, pcs, bool(val >> 24 & 1), bool(val >> 25 & 1))
            elif kind == 1:
                m.gate_off()
            else:
                m.set_scrb(val)
        row = m.block()
        for i, (c, g, _, _) in enumerate(row):
            if c is not None:
                pitch[b, i] = c
            gate[b, i] = g
            notes[b, i] = m.v[i].note if m.v[i].note is not None else 0
    return pitch, gate, notes


def run_c(lib, tw, pattern, ev, n_blocks):
    rows = []
    for b, kind, step, val, p in ev:
        rows.append([b, kind, step, val] + ([p[f] for f in FIELDS] if p else [0] * 16))
    arr = np.array(rows, np.int32).reshape(-1)
    pitch = np.zeros(n_blocks * NV, np.int32)
    mask = np.zeros(n_blocks, np.uint32)
    notes = np.zeros(n_blocks * NV, np.int32)
    P = ctypes.POINTER
    lib.dg_sim(arr.ctypes.data_as(P(ctypes.c_int32)), len(rows), n_blocks, tw, pattern,
               pitch.ctypes.data_as(P(ctypes.c_int32)), mask.ctypes.data_as(P(ctypes.c_uint32)),
               notes.ctypes.data_as(P(ctypes.c_int32)))
    started = (mask[:, None] >> np.arange(NV)) & 1
    gate = (mask[:, None] >> (8 + np.arange(NV))) & 1
    c = pitch.reshape(n_blocks, NV) / 65536.0
    return np.where(started == 1, c, np.nan), gate == 1, notes.reshape(n_blocks, NV)


_lib = None


def check(seed):
    global _lib
    if _lib is None:
        _lib = ctypes.CDLL(LIB)
    tw, pattern, ev, nb = case(seed)
    pp, pg, pn = run_python(tw, pattern, ev, nb)
    cp, cg, cn = run_c(_lib, tw, pattern, ev, nb)
    errs = []
    if not np.array_equal(np.isnan(pp), np.isnan(cp)):
        b = int(np.argwhere(np.isnan(pp) != np.isnan(cp))[0][0])
        errs.append(f'started voices differ from block {b}')
    if not np.array_equal(pg, cg):
        b = int(np.argwhere(pg != cg)[0][0])
        errs.append(f'gates differ from block {b}')
    live = ~np.isnan(pp)
    if not np.array_equal(pn[live], cn[live]):
        w = np.argwhere((pn != cn) & live)[0]
        errs.append(f'note differs at block {w[0]} voice {w[1]}: python {pn[w[0], w[1]]} c {cn[w[0], w[1]]}')
    d = np.abs(np.where(live, pp - cp, 0.0))
    # Semitones staircase edges: where the model steps by a semitone, C may step one block earlier or later (the
    # two sit within 1e-4 cent of the half-semitone line). Allowed only if C then equals the model's neighbour block.
    edges = 0
    for b, v in np.argwhere(d > TOL):
        ok = False
        for nb_ in (b - 1, b + 1):
            if 0 <= nb_ < len(pp) and live[nb_, v] and abs(pp[nb_, v] - cp[b, v]) <= TOL:
                step = abs(pp[max(b, nb_), v] - pp[min(b, nb_), v])
                ok = abs(step - 100.0) < 2.0
        if ok:
            d[b, v] = 0.0
            edges += 1
    mx = float(np.nanmax(d)) if d.size else 0.0
    if mx > TOL:
        w = np.unravel_index(np.nanargmax(d), d.shape)
        errs.append(f'pitch off by {mx:.4f} cents at block {w[0]} voice {w[1]} (python {pp[w]:.4f}, c {cp[w]:.4f})')
    used = {f: set() for f in FIELDS}
    for e in ev:
        if e[4]:
            for f in FIELDS:
                used[f].add(e[4][f])
    return seed, errs, mx, nb, used, edges


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    first = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    build()
    t0 = time.time()
    lib = ctypes.CDLL(LIB)                               # the chord builder, every case
    lib.dg_chord_for.restype = ctypes.c_uint32

    def c_chord(root, typ, ext, key, tl, el):
        w = lib.dg_chord_for(root, typ, ext, key, tl | el << 1)
        return {x for x in range(12) if w >> x & 1}, (w >> 12) & 0xF, (w >> 16) & 0xF
    bad = [(n, t, e, k, tl, el) for n in range(24, 97) for t in range(4) for e in range(8) for k in range(25)
           for tl in (0, 1) for el in (0, 1) if c_chord(n, t, e, k, tl, el) != G.chord_for(n, t, e, k, bool(tl), bool(el))]
    print(f'dg_chord_for vs the model over 73 roots x 4 types x 8 exts x 25 keys x locks: {len(bad)} differ {bad[:3]}')
    fails, worst, blocks, n_edges = ([(-1, ['dg_chord_for differs'])] if bad else []), 0.0, 0, 0
    cover = {f: set() for f in FIELDS}
    with Pool() as pool:
        for seed, errs, mx, nb, used, ed in pool.imap_unordered(check, range(first, first + n), chunksize=4):
            worst, blocks, n_edges = max(worst, mx), blocks + nb, n_edges + ed
            for f in FIELDS:
                cover[f] |= used[f]
            if errs:
                fails.append((seed, errs))
    for seed, errs in sorted(fails)[:20]:
        print(f'FAIL seed {seed}: ' + '; '.join(errs))
    missing = {f: sorted(set(range(*(RANGES[f] if isinstance(RANGES[f], tuple) else (0, RANGES[f])))) - cover[f])
               for f in FIELDS}
    missing = {f: v for f, v in missing.items() if v and f not in ('vcnt',)} | (
        {'vcnt': sorted({3, 4, 5, 6} - cover['vcnt'])} if {3, 4, 5, 6} - cover['vcnt'] else {})
    print(f'{n} progressions, {blocks:,} blocks x 6 voices, {time.time() - t0:.0f} s')
    print(f'largest pitch difference: {worst:.5f} cents (limit {TOL})')
    print(f'Semitones staircase steps landing one block apart (allowed): {n_edges}')
    print('every value of every parameter used' if not missing else f'values never used: {missing}')
    print('FAIL' if fails or missing else 'OK', f'({len(fails)} failing progressions)')
    sys.exit(1 if fails or missing else 0)


if __name__ == '__main__':
    main()
