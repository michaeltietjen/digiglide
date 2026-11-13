"""GLID is the time from the chord event until the last voice lands (GLIDE_SPEC.md, "GLID is the whole change").
The Python model and the C core (host build), every MOVE x TIME x ORDR, several GLID values, STAG and tempos:

  A  the last voice lands within one block of GLID, and no voice lands later (PATH changes from case to case)
  B  GLID 1 bar at 90 and 120 BPM: the chord has landed on the bar line, and not a block before
  C  GLID 0: every voice is on its note in the first block, with any Move
  D  TIME Together, ORDR Together, no Move: block for block what Brickglide's rule gives (model, FIT off)
  E  STAG keeps the order and equal spacing of the voice starts (model plan)

    python3 test_glid_fit.py
"""
import math, os, sys
from multiprocessing import Pool
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_equiv as T  # noqa: E402
G = T.G
NV = 6
C_MAJ, D_MIN = (60, (0, 4, 7)), (62, (2, 5, 9))
T0 = 200                                    # the block of the second chord (the first is laid out at block 0)


def glid_blocks(glid, tw):
    kind, x = G.GLIDS[glid]
    return x * 16 * 2700000.0 / tw if kind == 'bar' else x * G.HZ


def events(p, t0=T0):
    first = dict(G.Params.FIELDS)
    ev = []
    for b, (root, pcs), par in ((0, C_MAJ, first), (t0, D_MIN, p)):
        ev.append((b, 0, 0 if b == 0 else 16, sum(1 << x for x in pcs) | root << 12, par))
    return ev


def run_model(tw, ev, nb, fit=True):
    """-> (blocks each voice needs to land after the second chord (0 = it did not glide), pitch)."""
    m = G.DigiGlide(tw / 120.0, 0)
    m.FIT = fit
    by = {e[0]: e for e in ev}
    land = [0] * NV
    pitch = np.zeros((nb, NV))
    plan = None
    for b in range(nb):
        if b in by:
            _, _, step, val, p = by[b]
            m.trig(step, G.Params(**p), (val >> 12) & 0x7F, {x for x in range(12) if val >> x & 1})
            if b:
                plan = [(v.delay, v.dur) if v.path is not None and v.t0 == b else None for v in m.v]
        row = m.block()
        for i in range(NV):
            pitch[b, i] = row[i][0] if row[i][0] is not None else np.nan
    for i, x in enumerate(plan or []):                  # (the block in which path_at returns the last point)
        if x:
            land[i] = max(1, math.ceil((x[0] + x[1]) * G.HZ - 1e-6))
    return land, pitch, plan


_lib = None


def run_c(tw, ev, nb):
    global _lib
    if _lib is None:
        import ctypes
        _lib = ctypes.CDLL(T.LIB)
    import ctypes
    rows = [[b, kind, step, val] + [p[f] for f in T.FIELDS] for b, kind, step, val, p in ev]
    arr = np.array(rows, np.int32).reshape(-1)
    pitch = np.zeros(nb * NV, np.int32)
    mask = np.zeros(nb, np.uint32)
    notes = np.zeros(nb * NV, np.int32)
    gl = np.zeros(nb, np.uint32)
    P = ctypes.POINTER
    _lib.dg_sim2(arr.ctypes.data_as(P(ctypes.c_int32)), len(rows), nb, tw, 0,
                 pitch.ctypes.data_as(P(ctypes.c_int32)), mask.ctypes.data_as(P(ctypes.c_uint32)),
                 notes.ctypes.data_as(P(ctypes.c_int32)), gl.ctypes.data_as(P(ctypes.c_uint32)))
    t0 = max(e[0] for e in ev)
    land = [0] * NV
    for i in range(NV):
        w = np.nonzero(gl[t0:] >> i & 1)[0]
        if len(w):
            land[i] = int(w[-1]) + 2
    return land, pitch.reshape(nb, NV) / 65536.0


def case_a(args):
    n, tw, glid, move, time, ordr, stag = args
    p = dict(G.Params.FIELDS, glid=glid, move=move, time=time, ordr=ordr, stag=stag, path=n % 10, drft=0, vib=0,
             vcnt=3 + n % 4, bass=(2, 0)[n // 4 % 2])
    gb = glid_blocks(glid, tw)
    nb = T0 + int(gb) + 400
    ev = events(p)
    errs = []
    for name, land in (('model', run_model(tw, ev, nb)[0]), ('C', run_c(tw, ev, nb)[0])):
        last = max(land)
        if last == 0:
            errs.append(f'{name}: nothing glided')
        elif gb < 0.02 * G.HZ:                           # (under 20 ms a glide is a jump)
            if last > 1:
                errs.append(f'{name}: a jump took {last} blocks')
        elif not (gb - 1 <= last <= math.ceil(gb - 1e-6)):
            errs.append(f'{name}: last voice lands after {last} blocks, GLID is {gb:.2f} (voices {land})')
    return args, errs


def main():
    T.build()
    bad = 0

    def ok(c, msg):
        nonlocal bad
        bad += not c
        print(('  ok   ' if c else '  FAIL ') + msg)

    # A
    cases, n = [], 0
    for tw in (90 * 120, 120 * 120, 16044, 240 * 120, 60 * 120):
        for glid in (1, 3, 4, 5, 6, 10):
            if (tw in (240 * 120, 60 * 120) and glid not in (1, 5)) or (glid == 10 and tw != 16044):
                continue
            for move in range(10):
                for time in range(5):
                    for ordr in range(5):
                        for stag in ((0,) if ordr == 0 else (2, 6)):
                            cases.append((n, tw, glid, move, time, ordr, stag))
                            n += 1
    fails = []
    with Pool() as pool:
        for args, errs in pool.imap_unordered(case_a, cases, chunksize=8):
            if errs:
                fails.append((args, errs))
    for args, errs in sorted(fails)[:12]:
        print('       ', args, '; '.join(errs))
    ok(not fails, f'A: {len(cases)} cases (10 MOVE x 5 TIME x 5 ORDR, STAG 1 and 8 steps, GLID 1/16 1/4 1/2 1 2 bars '
       f'and 15 s, 60..240 BPM), model and C: the last voice lands within one block of GLID, none later '
       f'({len(fails)} failing)')

    # B
    for bpm in (90, 120):
        tw, bar = bpm * 120, 360000 // bpm
        for move, time, ordr, stag, label in ((0, 0, 0, 0, 'plain'), (1, 0, 0, 0, 'Bloom'), (2, 0, 0, 0, 'Cascade up'),
                                              (4, 2, 3, 3, 'Spiral, Bass lags, Outside in, STAG 2'),
                                              (0, 1, 1, 6, 'By distance, Low first, STAG 8')):
            p = dict(G.Params.FIELDS, glid=5, move=move, time=time, ordr=ordr, stag=stag, drft=0, vib=0)
            ev = events(p, t0=bar)                       # the second chord on the bar line of bar 2
            nb = 2 * bar + 200
            res = []
            for name, (land, pitch) in (('model', run_model(tw, ev, nb)[:2]), ('C', run_c(tw, ev, nb))):
                tgt = pitch[-1]
                on = np.nanmax(np.abs(pitch[2 * bar - 1] - tgt)) < 1e-6        # the block that ends on the bar line
                before = np.nanmax(np.abs(pitch[2 * bar - 2] - tgt)) < 1e-6
                res.append(max(land) == bar and on and not before)
            ok(all(res), f'B: {bpm} BPM, GLID 1 bar, {label}: landed on the bar line of bar 3 ({bar} blocks), not a '
               f'block before (model {res[0]}, C {res[1]})')

    # C
    worst = 0
    for move in range(10):
        for time in range(5):
            for ordr in range(5):
                p = dict(G.Params.FIELDS, glid=0, move=move, time=time, ordr=ordr, stag=6, drft=0, vib=0)
                ev = events(p)
                for land, pitch in (run_model(14400, ev, T0 + 300)[:2], run_c(14400, ev, T0 + 300)):
                    moved = np.nanmax(np.abs(pitch[T0:] - pitch[-1]))
                    worst = max(worst, max(land) - 1, 1 if moved > 1e-6 else 0)
    ok(worst == 0, 'C: GLID 0, every MOVE x TIME x ORDR with STAG 8: every voice is on its note in the first block, '
       'model and C')

    # D
    same = True
    for tw in (10800, 14400, 16044):
        for glid in range(13):
            for path in range(10):
                p = dict(G.Params.FIELDS, glid=glid, path=path)
                ev = events(p)
                nb = T0 + min(6000, int(glid_blocks(glid, tw)) + 300)
                a = run_model(tw, ev, nb, True)[1]
                b = run_model(tw, ev, nb, False)[1]
                same &= np.array_equal(a, b, equal_nan=True)
    ok(same, 'D: TIME Together, ORDR Together, no Move, every GLID and PATH at 3 tempos: block for block the same '
       'as Brickglide\'s rule')

    # E
    good, shown = True, None
    for ordr in (1, 2, 3, 4):
        for stag in range(1, 7):
            for glid in (3, 5, 7):
                p = dict(G.Params.FIELDS, glid=glid, ordr=ordr, stag=stag, drft=0, vib=0, bass=0)
                _, _, plan = run_model(14400, events(p), T0 + 2)
                d = sorted(x[0] for x in plan if x)
                gaps = [b - a for a, b in zip(d, d[1:])]
                nominal = G.STAGGERS[stag] * 15.0 / 120.0
                good &= len(d) >= 3 and max(gaps) - min(gaps) < 1e-9 and gaps[0] <= nominal + 1e-9
                good &= abs(max(x[0] + x[1] for x in plan if x) - G.GLIDS[glid][1] * 2.0) < 1e-9
                if (ordr, stag, glid) == (1, 2, 5):
                    shown = (nominal, gaps[0], plan[0][1])
    ok(good, 'E: ORDR with every STAG: the starts stay in order and evenly spaced, never wider than STAG, and the '
       'last voice lands at GLID (120 BPM, GLID 1 bar, STAG 1 step, 5 voices: spacing %.4f s for %.4f s nominal, '
       'each glide %.3f s)' % (shown[1], shown[0], shown[2]))
    print('FAIL' if bad else 'OK')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
