"""M1 check: the DigiGlide model against Brickglide's own code (michaeltietjen/brickchord), called directly.

Covers every case without randomness: chord tones for every KEY x SCL x DEG x CHRD, voice leading from many
voicings, every PATH shape and multi-point path, the glide plan (targets, vias, delays, durations, shapes) for
every MOVE x PATH x TIME x ORDR (non-random) x STAG, and Scale-steps vias. Brickglide is imported with pygame
stubbed out; nothing in it runs except the functions called here.
    python3 test_vs_brickglide.py [path to brickchord/brickchord]
"""
import itertools, math, os, random, sys, types

BRICK = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/dn2-workspace/repos/brickchord/brickchord')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import digiglide as G  # noqa: E402


class _Stub(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return hash(name) & 0xFFFF


sys.modules['pygame'] = _Stub('pygame')
sys.path.insert(0, BRICK)
import main as BM  # noqa: E402
import ambient as BA  # noqa: E402
import engine as BE  # noqa: E402

fails = []


def check(ok, what):
    if not ok:
        fails.append(what)
        if len(fails) <= 20:
            print('FAIL', what)


SCALE_NAMES = list(BM.SCALES)
assert [n for n, _ in G.SCALES] == SCALE_NAMES and all(BM.SCALES[n] == s for n, s in G.SCALES)
assert G.CHORDS == BA.CHORDS and G.PATHS == BA.PATHS and G.TIMINGS == BA.TIMINGS and G.ORDERS == BA.ORDERS
assert G.MOVES[1:9] == BA.MOVES and G.STAGGERS == BA.STAGGERS


class Fake:
    """Just enough of Brickglide's App for the amb_ functions under test."""
    NCH = 5

    def __init__(self, key, scl, achord, curs=None):
        self.key, self.scale = key, SCALE_NAMES[scl]
        self.achord = dict(achord)
        self.av = [{"note": 60, "cents": 0, "glide": 4, "on": True} for _ in range(6)]
        self.aui = [{"cur": None} for _ in range(6)]
        for i, c in (curs or {}).items():
            self.aui[i]["cur"] = c
        self.pushed = {}

    def amb_push(self, i, jump=False, glide=None, shape=0, delay=0.0, via=None):
        self.pushed[i] = dict(note=self.av[i]["note"], glide=glide, shape=shape, delay=delay, via=via)

    def amb_sub_follow(self, moves, secs):
        self.sub = (moves, secs)

    def flash(self, *_):
        pass


for name in ('amb_voicelead', 'amb_chord_tones', 'amb_route', 'amb_steps_via', 'amb_glide_all'):
    setattr(Fake, name, getattr(BA.AmbientMixin, name))

# 1. chord tones
n = 0
for key, scl, deg, chrd in itertools.product(range(12), range(4), range(7), range(len(G.CHORDS))):
    f = Fake(key, scl, {"type": chrd})
    root_pc, pcs, _, _ = f.amb_chord_tones(deg, None)
    check(G.chord_tones(key, scl, deg, chrd) == (root_pc, pcs), f'chord_tones key {key} scl {scl} deg {deg} chrd {chrd}')
    n += 1
print(f'chord tones: {n} cases')

# 2. voice leading
rnd = random.Random(1)
n = 0
for _ in range(4000):
    key, scl, deg, chrd = rnd.randrange(12), rnd.randrange(4), rnd.randrange(7), rnd.randrange(len(G.CHORDS))
    nv = rnd.randint(1, 6)
    bass = rnd.random() < 0.7
    curs = {i: rnd.choice([rnd.randint(30, 80) * 100.0, rnd.uniform(3000, 8000)]) for i in range(nv)}
    f = Fake(key, scl, {"type": chrd, "root": bass}, curs)
    root_pc, pcs, _, _ = f.amb_chord_tones(deg, None)
    want = f.amb_voicelead(list(range(nv)), pcs, root_pc)
    check(G.voicelead(curs, pcs, root_pc, bass) == want, f'voicelead {curs} {sorted(pcs)} root {root_pc} bass {bass}')
    n += 1
print(f'voice leading: {n} cases')

# 3. shapes and paths
n = 0
for shape in range(9):
    for k in range(-5, 206):
        p = k / 200.0
        check(abs(G.shape_at(p, shape) - BE.Engine.amb_shape(p, shape)) < 1e-12, f'shape {shape} p {p}')
        n += 1
for _ in range(3000):
    pts = [rnd.uniform(3000, 8000) for _ in range(rnd.randint(2, 6))]
    dur, el, shape = rnd.choice([0.0, 0.01, 0.5, 2.0, 30.0]), rnd.uniform(-1, 35), rnd.randrange(9)
    check(abs(G.path_at(pts, el, dur, shape) - BE.Engine.amb_path_at(pts, el, dur, shape)) < 1e-9, f'path_at {pts} {el} {dur} {shape}')
    n += 1
print(f'shapes and paths: {n} cases')

# 4. glide plans (no randomness: ORDR Random, TIME Loose, Scatter and EVOL are checked for repeatability in test_model.py)
n = 0
bpm = 120.0
for move, path, timing, order, stag in itertools.product(range(0, 9), range(10), range(4), range(4), (0, 3)):
    if move == 6:
        continue
    key, scl, deg, chrd = rnd.randrange(12), rnd.randrange(4), rnd.randrange(7), rnd.randrange(len(G.CHORDS))
    curs = {i: rnd.randint(36, 76) * 100.0 for i in range(5)}
    m = G.DigiGlide(bpm)
    p = G.Params(key=key, scl=scl, deg=deg, chrd=chrd, move=move, path=path, time=timing, ordr=order, stag=stag, glid=5)
    m.p, m.key = p, key
    for i, c in curs.items():
        v = m.v[i]
        v.started, v.on, v.cur, v.note, v.tgt = True, True, c, int(c / 100), c
    root_pc, pcs = G.chord_tones(key, scl, deg, chrd)
    moves = G.voicelead(curs, pcs, root_pc, True)
    secs_m = m.glide_all(dict(moves), move)
    f = Fake(key, scl, {"type": chrd, "root": True, "path": path, "time": 2.0, "stagger": m.stag_secs(p),
                        "order": order, "timing": timing}, curs)
    f.amb_glide_all(dict(moves), "", move=None if move == 0 else move - 1)
    for i in moves:
        v, b = m.v[i], f.pushed[i]
        via_b = b['via'] or []
        want_path = [curs[i]] + list(via_b) + [moves[i] * 100.0]
        ok = (v.note == b['note'] and abs(v.dur - b['glide']) < 1e-9 and abs(v.delay - b['delay']) < 1e-9
              and v.shape == b['shape'] and v.path is not None and len(v.path) == len(want_path)
              and all(abs(x - y) < 1e-9 for x, y in zip(v.path, want_path)))
        if v.path is None and abs(moves[i] * 100.0 - curs[i]) <= 0.5 and not via_b:
            ok = v.note == b['note']
        check(ok, f'glide_all move {move} path {path} time {timing} order {order} stag {stag} voice {i}: '
                  f'model {v.note} {v.dur} {v.delay} {v.shape} {v.path} brick {b}')
        n += 1
    check(abs(secs_m - f.sub[1]) < 1e-9, f'glide secs move {move}')
print(f'glide plans: {n} voice cases')

print('FAIL' if fails else 'OK', f'({len(fails)} failures)')
sys.exit(1 if fails else 0)
