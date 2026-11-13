"""DigiGlide reference model (spec rev 3, milestone M1). Host only, no firmware.

A port of Brickglide (michaeltietjen/brickchord, brickchord/ambient.py, engine.py, main.py) reduced to what
DigiGlide does on one Digitone track: chord building (KEY / SCL / DEG / CHRD), voice leading (amb_voicelead),
glide planning (amb_glide_all, amb_route, amb_steps_via, amb_sub_follow, amb_evolve) and per-block pitch
(amb_shape, amb_path_at, the engine's drift and vibrato). Time runs in Digitone audio blocks (1500 per second);
pitch is in cents (MIDI note * 100). The C port (M2) must match this module.

Changes from Brickglide, all forced by the Digitone or by the spec:
- Randomness is seeded from (pattern, step, voice, purpose), not free-running (spec: repeatable renders).
- GLID is tempo-synced (bars) or 15 / 30 / 60 s; STAG is in 1/16 steps instead of seconds.
- VCNT counts every voice including the sub (max 6 on the Digitone); BASS root+sub uses one of them.
- No re-render jump when a voice moves more than 2 octaves from its sample's base (Brickglide plays samples,
  the Digitone does not).
- A fresh trig (no voice sounding) ignores MOVE: voices attack on the chord. (Brickglide does a level bloom.)
- EVOL moves the drone voices only; the sub follows the new bass. (Brickglide also evolves the sub, which then
  drops one more octave below its evolved note on every evolve.)
- SCRB limits how far along its path each voice may go (spec), smoothed like Brickglide's 0.06 s scrub glide.

Pinned for the fixed-point C port (M2), so exact float ties can't tip differently in the two versions:
- Pitch comparisons that pick a voice order (voice leading, ORDR) sort on pitch rounded to 1/1024 cent (QKEY).
- Voice leading takes a later candidate only if it is better by more than TIE (1e-5 semitone); Brickglide takes
  it if better at all. Scale-steps vias keep TIE clear of the 0.3 margin.
- Semitones rounds half up (with TIE), not half to even.
- The drift interval is drawn with integer maths: 3000 + (6000 * r24 >> 24) blocks (Brickglide: int((2 + 4r) / DT)).
- SCRB smoothing (DigiGlide's own, not Brickglide's) is defined in Q30 integers (SCRB_Q, scrb_step), because the
  block where it snaps to 1 decides when a held glide may finish.
"""
import math

HZ = 1500.0                 # Digitone audio blocks per second (48 kHz / 32)
DT = 1.0 / HZ
TIE = 1e-5                  # semitones


def qkey(cents):
    """Pitch as a sort key, rounded to 64/65536 cent (the C port's (q16 + 32) >> 6)."""
    return math.floor(cents * 1024.0 + 0.5)

# ---------------------------------------------------------------- Brickglide tables
NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
SCALES = [("Major", [0, 2, 4, 5, 7, 9, 11]), ("Minor", [0, 2, 3, 5, 7, 8, 10]),
          ("Dorian", [0, 2, 3, 5, 7, 9, 10]), ("Mixolydian", [0, 2, 4, 5, 7, 9, 10])]
CHORDS = [("Triad", "deg", [0, 2, 4]), ("Seventh", "deg", [0, 2, 4, 6]), ("Ninth", "deg", [0, 2, 4, 6, 8]),
          ("Eleventh", "deg", [0, 2, 4, 6, 8, 10]), ("Sus2", "semi", [0, 2, 7, 14]), ("Sus4", "semi", [0, 5, 7, 12, 17]),
          ("Quartal", "semi", [0, 5, 10, 15, 20]), ("Lydian", "semi", [0, 4, 6, 11, 14, 18]),
          ("Minor 11", "semi", [0, 3, 7, 10, 14, 17]), ("Major 9", "semi", [0, 4, 7, 11, 14]),
          ("Fifths", "semi", [0, 7, 14, 21]), ("Cluster", "semi", [0, 2, 3, 5, 7]), ("Open", "semi", [0, 7, 16, 19, 26])]
BUILD_CHORD = {"Triad": {}, "Seventh": {"seventh": True}, "Ninth": {"ninth": True}, "Sus4": {"sus": True}}
PATHS = ["Smooth", "Linear", "Ease", "Swell", "Bounce", "Late", "Snap", "Wobble", "Semitones", "Scale steps"]
SEMITONES, SCALE_STEPS = 8, 9
TIMINGS = ["Together", "By distance", "Bass lags", "Bass leads", "Loose"]
MOVES = ["none", "Bloom", "Cascade up", "Cascade down", "Spiral", "Swoop", "Scatter", "Converge", "Fall", "EVOL"]
EVOL = 9
ORDERS = ["Together", "Low first", "High first", "Outside in", "Random"]
STAGGERS = [0, 0.5, 1, 2, 3, 5, 8]                       # in 1/16 steps
GLIDS = [("bar", 0), ("bar", 1 / 16), ("bar", 1 / 8), ("bar", 1 / 4), ("bar", 1 / 2), ("bar", 1), ("bar", 2),
         ("bar", 4), ("bar", 8), ("bar", 16), ("s", 15), ("s", 30), ("s", 60)]
GLID_NAMES = ["0", "1/16", "1/8", "1/4", "1/2", "1", "2", "4", "8", "16", "15s", "30s", "60s"]
BASS_MODES = ["OFF", "FOL-2", "FOL-1", "FOL", "SOL-2", "SOL-1", "SOLO"]   # mode and octave on one knob


def voic_step(voic):
    """Cents between neighbouring chord voices' places: VOIC 0 = 200 (a tight cluster), 64 = 420 (close position, the
    default: stock sounds hold 64 in this slot), 127 = 1000 (wide)."""
    return 200 + (220 * voic) // 64 if voic <= 64 else 420 + ((voic - 64) * 580) // 63


def bass_mode(b):
    """0 off, 1 follow, 2 solo."""
    return 0 if b == 0 else (1 if b <= 3 else 2)


def bass_oct(b):
    """octaves the bass voice plays under the root: -2, -1 or 0."""
    return (b - 1) % 3 - 2
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII"]

DEFAULT_NOTES = [36, 43, 48, 55, 60, 64]                  # Brickglide amb_init (+ key)
BASE_PANS = [0.0, -0.4, 0.4, -0.2, 0.2, 0.0]
LEVELS = [0.7, 0.6, 0.6, 0.6, 0.6, 0.6]
SUB_LEVEL = 0.6
PH0 = 1.7                                                 # engine: v.ph = k * 1.7
SCRUB_GLIDE = 0.06
ONE30 = 1 << 30
K_SCRB = 46676911                                         # round((1 - exp(-4 * DT / SCRUB_GLIDE)) * 2^30)


def scrb_q(value):
    """SCRB knob 0..127 -> Q30 fraction (floor, as the C core's muldiv)."""
    return (value * ONE30) // 127


def scrb_step(s, t):
    """One block of SCRB smoothing, Q30: s += (t - s) * K truncated toward zero; snap within 1074 (1e-6)."""
    d = t - s
    q = (abs(d) * K_SCRB) >> 30
    s += q if d >= 0 else -q
    return t if abs(t - s) < 1074 else s

# seeded random purposes
R_LOOSE, R_SCATTER, R_EVOL, R_ORDER, R_DRIFT = 1, 2, 3, 4, 5


# ---------------------------------------------------------------- seeded random (xorshift32, ports to C exactly)
def _fmix32(h):
    h &= 0xFFFFFFFF
    h ^= h >> 16; h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13; h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


class Rng:
    """One stream per (pattern, step, voice, purpose). rand() is in [0, 1) with 24-bit resolution."""
    def __init__(self, pattern, step, voice, purpose):
        h = _fmix32(pattern * 0x9E3779B1 + 0x7F4A7C15)
        h = _fmix32(h ^ (step * 0x85EBCA77 + 0x165667B1))
        h = _fmix32(h ^ (voice * 0xC2B2AE3D + 0x27D4EB2F))
        h = _fmix32(h ^ (purpose * 0x2545F491 + 0x61C88647))
        self.x = h or 0x6D2B79F5

    def u32(self):
        x = self.x
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        self.x = x
        return x

    def r24(self):
        return self.u32() >> 8

    def rand(self):
        return self.r24() / 16777216.0

    def below(self, n):
        return (self.r24() * n) >> 24

    def uniform(self, a, b):
        return a + (b - a) * self.rand()


# ---------------------------------------------------------------- chords (main.build_chord, amb_chord_tones)
def build_chord(key, scale, degree, m):
    sc = SCALES[scale][1]

    def tone(i):
        return sc[(degree + i) % 7] + 12 * ((degree + i) // 7)

    root = tone(0)
    third, fifth, sev = tone(2) - root, tone(4) - root, tone(6) - root
    ivals = [0, third, fifth]
    if m.get("sus"):
        ivals[1] = 5
    if m.get("seventh") or m.get("ninth"):
        ivals.append(sev)
    if m.get("ninth"):
        ivals.append(14)
    return (key + root) % 12, ivals


def chord_tones(key, scale, deg, chrd):
    """-> (root pitch class, set of chord pitch classes), as Brickglide's amb_chord_tones with no held modifiers."""
    name, kind, steps = CHORDS[chrd]
    root_pc, iv = build_chord(key, scale, deg, BUILD_CHORD.get(name, {}))
    if name in BUILD_CHORD:
        return root_pc, {(root_pc + i) % 12 for i in iv}
    sc = SCALES[scale][1]
    if kind == "deg":
        return root_pc, {(key + sc[(deg + s) % 7]) % 12 for s in steps}
    return root_pc, {(root_pc + s) % 12 for s in steps}


def voicelead(curs, pcs, bass_note):
    """amb_voicelead. curs: {voice: reference pitch in cents}. -> {voice: MIDI note}. bass_note: the note the lowest
    voice takes (rev 5: the chord's root as played), or None: every voice takes its nearest chord tone."""
    cand = [n for n in range(CAND_LO, CAND_HI + 1) if n % 12 in pcs]
    cur = [(curs[i] / 100.0, i) for _, i in sorted((qkey(c), i) for i, c in curs.items())]
    best, used, prev, rest = [], set(), 0, cur
    if bass_note is not None and len(cur) > 1:
        b = bass_note
        best, used, prev, rest = [b], {b % 12}, b, cur[1:]
    for c, _ in rest:
        opts = [n for n in cand if n > prev] or [cand[-1]]
        n, bc = None, None
        for o in opts:                                  # min(), but a later tie needs to win by more than TIE
            cost = abs(o - c) + (2.5 if o % 12 in used and len(used) < len(pcs) else 0)
            if n is None or cost < bc - TIE:
                n, bc = o, cost
        best.append(n)
        used.add(n % 12)
        prev = n
    return {i: n for n, (_, i) in zip(best, cur)}


CAND_LO, CAND_HI = 12, 108                              # the notes the voice leader may use
ROOT_LO, ROOT_HI = 24, 96                               # the roots it accepts (clamped)
LEASH = 700.0                                           # cents a voice's reference may be from its VOIC place

# ---------------------------------------------------------------- rev 5 chords (Orchid-style: one key = one chord)
TYPES = ["MAJ", "MIN", "SUS", "DIM"]
TRIADS = [(0, 4, 7), (0, 3, 7), (0, 5, 7), (0, 3, 6)]
EXTS = ["NONE", "6", "7", "MAJ7", "9", "6+9", "7+9", "M7+9"]
EXT_PARTS = [(), ("6",), ("7",), ("M7",), ("9",), ("6", "9"), ("7", "9"), ("M7", "9")]
EXT_SEMI = {"6": 9, "7": 10, "M7": 11, "9": 14}         # literal intervals over the root
EXT_DEG = {"6": 5, "7": 6, "M7": 6, "9": 8}             # scale steps over the root when KEY is set: 7 and MAJ7 both
                                                        # give the key's own seventh (a literal MAJ7 on a minor chord is harsh)
KEY_NAMES = ["OFF"] + [n + "MAJ" for n in NOTE_NAMES] + [n + "MIN" for n in NOTE_NAMES]


def chord_for(root, typ, ext, key, type_locked=False, ext_locked=False):
    """The chord one key plays. root: MIDI note; typ / ext: indices into TYPES / EXTS; key: 0 = OFF, 1..12 = C..B
    major, 13..24 = C..B (natural) minor. -> (pitch classes, scale key, scale index for Scale steps / EVOL).
    KEY set and the root in its scale: the triad and the 6 / 7 / 9 are the scale's own (so each root gets its
    diatonic quality, I a major seventh, V a dominant seventh, with EXT 7 or MAJ7 alike). A root outside the
    scale, KEY OFF, or a p-locked TYPE / EXT on the step: TYPE's triad / EXT's literal intervals."""
    r = root % 12
    tonic, minor = ((key - 1) % 12, (key - 1) // 12) if key else (r, 1 if typ in (1, 3) else 0)
    sc = SCALES[minor][1]
    d = sc.index((r - tonic) % 12) if key and (r - tonic) % 12 in sc else None
    deg = lambda k: (tonic + sc[(d + k) % 7]) % 12
    if d is not None and not type_locked:
        pcs = {deg(0), deg(2), deg(4)}
    else:
        pcs = {(r + x) % 12 for x in TRIADS[typ]}
    for part in EXT_PARTS[ext]:
        if d is not None and not ext_locked and part in EXT_DEG:
            pcs.add(deg(EXT_DEG[part]))
        else:
            pcs.add((r + EXT_SEMI[part]) % 12)
    return pcs, tonic, minor


# ---------------------------------------------------------------- shapes (engine.amb_shape, amb_path_at)
def shape_at(p, shape):
    p = 0.0 if p < 0 else (1.0 if p > 1 else p)
    if shape == 1 or shape == 8:
        return p
    if shape == 2:
        return p * p * (3 - 2 * p)
    if shape == 3:
        e = p * p * (3 - 2 * p)
        return e + 0.45 * math.sin(math.pi * p) * p
    if shape == 4:
        return 1.0 - (1.0 - p) ** 4 * math.cos(3.0 * math.pi * p)
    if shape == 5:
        q = max(0.0, (p - 0.65) / 0.35)
        return q * q * (3 - 2 * q)
    if shape == 6:
        q = min(1.0, p / 0.25)
        return q * q * (3 - 2 * q)
    if shape == 7:
        e = p * p * (3 - 2 * p)
        return e + 0.09 * math.sin(6 * math.pi * p) * math.sin(math.pi * p)
    return (1 - math.exp(-5 * p)) / (1 - math.exp(-5))


def path_at(path, el, dur, shape):
    if el <= 1e-9:                                       # (a delay that has just elapsed, to the block, has not:
        return path[0]                                   # float error must not start it a block before the C port)
    if dur <= 0.02 or el >= dur - 1e-9:                  # (and a glide that ends on this block has ended)
        return path[-1]
    n = len(path) - 1
    if n == 1:
        v = path[0] + (path[1] - path[0]) * shape_at(el / dur, shape)
        if shape == 8:
            v = path[0] + math.floor((v - path[0]) / 100.0 + 0.5 + TIE) * 100.0
        return v
    q = el / dur * n
    i = min(n - 1, int(q))
    return path[i] + (path[i + 1] - path[i]) * shape_at(q - i, 2)


# ---------------------------------------------------------------- parameters
class Params:
    """The 16 DigiGlide parameters as indices into the tables above (what the knobs store)."""
    FIELDS = dict(key=0, scl=1, voic=64, pos=64, vcnt=5, bass=2, sprd=77, move=0,
                  glid=5, path=0, time=0, ordr=0, stag=0, drft=8, vib=4, scrb=127)

    def __init__(self, **kw):
        for k, v in self.FIELDS.items():
            setattr(self, k, v)
        for k, v in kw.items():
            if k not in self.FIELDS:
                raise KeyError(k)
            setattr(self, k, v)

    def copy(self, **kw):
        p = Params(**{k: getattr(self, k) for k in self.FIELDS})
        for k, v in kw.items():
            setattr(p, k, v)
        return p

    def label(self):
        return "%s %s VOIC %d" % (NOTE_NAMES[self.key], SCALES[self.scl][0], self.voic)


class Voice:
    def __init__(self, k):
        self.k = k
        self.started = False
        self.on = False
        self.note = None                    # target MIDI note (int)
        self.tgt = self.cur = 0.0           # cents
        self.glide = 2.0
        self.path = None
        self.t0 = 0
        self.delay = self.dur = 0.0
        self.shape = 0
        self.dr = self.dr_t = 0.0
        self.dr_n = 0
        self.ph = k * PH0
        self.rng = None
        self.vib = self.drift = 0.0
        self.rate = 0.15 + 0.05 * k
        self.pan = BASE_PANS[k]
        self.level = LEVELS[k]


class DigiGlide:
    """One DigiGlide track. Call trig() / gate_off() / set_scrb() between blocks, block() once per audio block."""
    NV = 6
    FIT = True                              # GLID is the whole change (False: Brickglide's rule, for comparisons only)

    def __init__(self, bpm=120.0, pattern=0):
        self.bpm = float(bpm)
        self.pattern = pattern
        self.b = 0                          # current block
        self.v = [Voice(k) for k in range(self.NV)]
        self.p = Params()
        self.key = 0
        self.root = None                    # the last chord's root (MIDI note)
        self.aroot, self.avoic, self.apos = 60, 64, 64     # what anchor() is built on: this event's root and VOIC
        self.step = 0
        self.scrb = ONE30                   # smoothed SCRB fraction, Q30
        self.scrb_t = ONE30

    # ---- helpers
    def glid_secs(self, p):
        kind, x = GLIDS[p.glid]
        return x * 240.0 / self.bpm if kind == "bar" else float(x)

    def stag_secs(self, p):
        return STAGGERS[p.stag] * 15.0 / self.bpm

    def layout(self, p):
        """-> (chord voice count, bass voice on). The bass voice is the slot after the chord voices."""
        sub = bass_mode(p.bass) != 0
        return max(1, min(self.NV, p.vcnt) - (1 if sub else 0)), sub

    def rng(self, voice, purpose):
        return Rng(self.pattern, self.step, voice, purpose)

    def _ensure(self, i):
        v = self.v[i]
        if not v.started:
            v.started = True
            a = self.anchor(i)                           # where VOIC puts this voice over the root
            v.note = a // 100
            v.cur = v.tgt = float(a)
        if v.rng is None:
            v.rng = Rng(self.pattern, self.step, i, R_DRIFT)
        return v

    def push(self, i, jump=False, glide=None, shape=0, delay=0.0, via=None):
        """amb_push + engine c_amb for the pitch part."""
        v = self.v[i]
        old = v.tgt
        v.tgt = v.note * 100.0
        if glide is not None:
            v.glide = float(glide)
        if abs(v.tgt - old) > 0.5 or via:
            v.path = [v.cur] + [float(c) for c in (via or [])] + [v.tgt]
            v.t0, v.delay, v.dur, v.shape = self.b, float(delay), float(v.glide), int(shape)
        if jump:
            v.cur = v.tgt
            v.path = None

    # ---- Brickglide planning
    def route(self, order, items, st):
        rank = sorted(items, key=lambda t: math.floor(t[1] + 0.5))    # (to the cent: voices in unison tie)
        n = len(rank)
        if order == 0 or st <= 0 or n < 2:
            return {i: 0.0 for i, _ in items}
        if order == 1:
            seq = [i for i, _ in rank]
        elif order == 2:
            seq = [i for i, _ in reversed(rank)]
        elif order == 3:
            seq, lo, hi = [], 0, n - 1
            while lo <= hi:
                seq.append(rank[lo][0])
                if hi != lo:
                    seq.append(rank[hi][0])
                lo, hi = lo + 1, hi - 1
        else:
            seq = [i for i, _ in rank]
            r = self.rng(0xFF, R_ORDER)
            for a in range(len(seq) - 1, 0, -1):          # Fisher-Yates, as random.shuffle
                j = r.below(a + 1)
                seq[a], seq[j] = seq[j], seq[a]
        return {i: k * st for k, i in enumerate(seq)}

    def steps_via(self, frm, to):
        sc = SCALES[self.p.scl][1]
        lo, hi = sorted((frm / 100.0, to / 100.0))
        notes = [n * 100.0 for n in range(int(math.ceil(lo)), int(hi) + 1)
                 if (n - self.key) % 12 in sc and lo + 0.3 + TIE < n < hi - 0.3 - TIE]
        if frm > to:
            notes.reverse()
        return notes[:10]

    def glide_all(self, moves, move):
        """amb_glide_all, with DigiGlide's timing rule. moves: {voice: MIDI note}; move: index into MOVES (0 none,
        1..8 a Move).
        GLID is the time from the chord event until the last voice lands, and everything fits inside it: each
        voice's delay (ORDR / STAG, a Cascade) and duration (TIME) are planned as Brickglide does, relative to
        GLID, and then all of them are scaled by GLID / (the latest landing of a voice that moves). A Move's
        turning points keep their place within each voice's own glide. With TIME Together, ORDR Together and no
        Move nothing is scaled. GLID 0 is a hard change: no Move, no delays.
        (Brickglide: a Move lasts at least 2.5 s, Bloom / Spiral / Swoop / Scatter twice GLID, and delays and
        TIME's longer glides run past GLID.)"""
        p = self.p
        path = p.path
        shape = 2 if path == SCALE_STEPS else path
        secs = self.glid_secs(p)
        items = [(i, self.v[i].cur) for i in moves]
        delays = self.route(p.ordr, items, self.stag_secs(p))
        vias = {}
        if self.FIT and secs <= 0:
            move, delays = 0, {}
        if 1 <= move <= 8:
            name = MOVES[move]
            rank = sorted(moves, key=lambda i: moves[i])
            n = max(1, len(rank))
            if not self.FIT:
                secs = max(secs, 2.5) * (2.0 if name in ("Bloom", "Spiral", "Swoop", "Scatter") else 1.0)
            if name == "Bloom":
                low = min(moves.values()) * 100.0
                vias = {i: [low] for i in moves}
            elif name == "Cascade up":
                delays = {i: k * secs * 0.6 / n for k, i in enumerate(rank)}
            elif name == "Cascade down":
                delays = {i: k * secs * 0.6 / n for k, i in enumerate(reversed(rank))}
            elif name == "Spiral":
                vias = {i: [moves[i] * 100.0 + (1200.0 if k % 2 else -1200.0)] for k, i in enumerate(rank)}
            elif name == "Swoop":
                vias = {i: [moves[i] * 100.0 - 1200.0] for i in moves}
            elif name == "Scatter":
                sc = SCALES[p.scl][1]
                for i in moves:
                    c = int(moves[i])
                    opts = [m for m in range(c - 7, c + 8) if (m - self.key) % 12 in sc and m != c]
                    vias[i] = [opts[self.rng(i, R_SCATTER).below(len(opts))] * 100.0] if opts else []
            elif name == "Converge":
                mid = (min(moves.values()) + max(moves.values())) * 50.0
                vias = {i: [mid] for i in moves}
            elif name == "Fall":
                vias = {i: [moves[i] * 100.0 + 1200.0] for i in moves}
            if path in (SCALE_STEPS, SEMITONES):
                shape = 2
        timing = p.time
        rank = sorted(moves, key=lambda i: moves[i])
        plan, last = [], 0.0
        for i, note in moves.items():
            v = self.v[i]
            frm = v.cur
            v.note = int(note)
            via = vias.get(i) or (self.steps_via(frm, note * 100.0) if path == SCALE_STEPS else None)
            g = secs
            k = rank.index(i) / max(1, len(rank) - 1)
            if timing == 1:
                g = secs * max(0.35, min(2.5, abs(note * 100.0 - frm) / 500.0))
            elif timing == 2:
                g = secs * (1.8 - 0.9 * k)
            elif timing == 3:
                g = secs * (0.6 + 0.9 * k)
            elif timing == 4:
                g = secs * self.rng(i, R_LOOSE).uniform(0.6, 1.6)
            d = delays.get(i, 0.0)
            plan.append((i, g, d, via))
            if abs(v.note * 100.0 - v.tgt) > 0.5 or via:    # (a voice that stays where it is lands nowhere)
                last = max(last, d + g)
        for i, g, d, via in plan:
            if self.FIT and last > 0:                       # (the landing is scaled, then split: the last voice's
                end = (d + g) * secs / last                 # delay and glide add up to GLID exactly)
                d = d * secs / last
                g = end - d
            self.push(i, glide=g, shape=shape, delay=d, via=via)
        return secs

    def sub_follow(self, moves, secs, sub):
        """The mono bass voice (the slot after the chord voices; Brickglide's sub): the chord's root, BASS's
        octaves down. It jumps there when it starts and glides there when it sounds."""
        n, _ = self.layout(self.p)
        s = n
        for i in range(n + 1, self.NV):                     # slots past the layout stay off
            self.v[i].on = False
        if s >= self.NV:
            return
        if not sub or not moves:
            self.v[s].on = False
            return
        v = self._ensure(s)
        was_on = v.on
        v.vib, v.drift, v.pan, v.level, v.rate = 0.0, 0.0, 0.0, SUB_LEVEL, 0.15 + 0.05 * 5
        v.note, v.on = self.root + 12 * bass_oct(self.p.bass), True
        self.push(s, jump=not was_on, glide=secs, shape=2)

    # ---- sequencer events
    def anchor(self, i):
        """Where VOIC and POS aim chord voice i, in cents: stacked from the root moved by POS (64 = on the root,
        0 = two octaves down, 127 = almost two up), spaced by voic_step(VOIC). The voice leader then gives each voice its nearest chord tone, so sweeping
        VOIC walks through the inversions and spreads."""
        a = self.aroot * 100 + ((self.apos - 64) * 2400) // 64 + i * voic_step(self.avoic)
        return max(CAND_LO * 100, min(CAND_HI * 100, a))

    def trig(self, step, p, root=60, pcs=(0, 4, 7), tail=False, revoice=False):
        """A chord event on the DigiGlide track at the current block, with its (p-locked) parameters.
        root: the chord's root as played (MIDI note). The chord voices sit over it (VOIC, POS); the mono bass
        voice plays it BASS's octaves down (Follow), alone (Solo), or not at all (Off).
        pcs: the chord's pitch classes (chord_for). p.key / p.scl: the scale for Scale steps and EVOL.
        The other voices are led from where they are (Brickglide), but a voice further than LEASH (a fifth) from
        its VOIC place over the new root is led from that distance instead: the chord stays around the key played
        and cannot creep up or down over a progression.
        tail: the last chord was released but still rings (inside its amp release): its voices count as sounding,
        so this chord attacks again and glides from where they are instead of laying out fresh.
        revoice: VOIC was turned: every voice is led from its VOIC anchor instead of from where it is."""
        self.step = step
        self.p = p
        self.key = p.key % 12
        root = max(ROOT_LO, min(ROOT_HI, int(root)))
        self.root = root
        self.aroot, self.avoic, self.apos = root, p.voic, p.pos
        was = [v.started for v in self.v]

        def ref(i):                                         # a sounding voice leads from where it is, but never
            a = float(self.anchor(i))                       # from more than LEASH away from its VOIC place
            if revoice or not was[i]:
                return a
            return max(a - LEASH, min(a + LEASH, self.v[i].cur))
        solo = bass_mode(p.bass) == 2                       # BASS Solo: the bass voice alone, the chord muted
        tones = lambda: (None, set(pcs))
        self.scrb_t = scrb_q(p.scrb)
        n, sub = self.layout(p)
        if solo:
            for i in range(self.NV):
                if i != n:
                    self.v[i].on = False
            if tail and n < self.NV and self.v[n].started:
                self.v[n].on = True
            self.sub_follow({0: root}, self.glid_secs(p), True)
            return
        sprd = p.sprd / 77.0
        for i in range(self.NV):
            v = self.v[i]
            if i < n:
                v.vib, v.drift, v.rate = float(p.vib), float(p.drft), 0.15 + 0.05 * i
                v.pan, v.level = max(-1.0, min(1.0, BASE_PANS[i] * sprd)), LEVELS[i]
        for i in range(n + (1 if sub else 0), self.NV):     # slots past the layout stop (the sub is set below)
            self.v[i].on = False
        if tail:                                            # (the bass voice rings too)
            for i in range(n + (1 if sub else 0)):
                if i < self.NV and self.v[i].started:
                    self.v[i].on = True
        sounding = [i for i in range(n) if self.v[i].on]
        if not sounding:                                    # fresh: lay the chord out and attack, no glide
            root_pc, pcs = tones()
            for i in range(n):
                self._ensure(i)
            notes = voicelead({i: ref(i) for i in range(n)}, pcs, root_pc)
            for i, m in notes.items():
                v = self.v[i]
                v.note, v.on = int(m), True
                self.push(i, jump=True)
            self.sub_follow(notes, 0.5, sub)
            return
        fresh = [i for i in range(n) if not self.v[i].on]
        for i in fresh:
            self._ensure(i)
            self.v[i].on = True
            self.push(i, jump=True)
        if p.move == EVOL:                                  # amb_evolve: nearby scale notes instead of the chord
            sc = SCALES[p.scl][1]
            moves = {}
            for i in range(n):
                v = self.v[i]
                cands = [m for m in range(v.note - 5, v.note + 6) if (m - self.key) % 12 in sc and m != v.note]
                if cands:
                    moves[i] = cands[self.rng(i, R_EVOL).below(len(cands))]
            if moves:
                secs = self.glide_all(moves, 0)
                bass = {i: self.v[i].note for i in range(n)}
                self.sub_follow(bass, secs, sub)
            return
        root_pc, pcs = tones()
        moves = voicelead({i: ref(i) for i in range(n)}, pcs, root_pc)
        secs = self.glide_all(moves, p.move)
        self.sub_follow(moves, secs, sub)

    def gate_off(self):
        """The trig's length ran out: the amp envelopes release. Under DigiGlide's default (Brickglide's
        behaviour), released voices count as not sounding, so the next trig lays out a fresh chord."""
        for v in self.v:
            v.on = False

    def set_scrb(self, value):
        self.scrb_t = scrb_q(value)

    # ---- per block
    def block(self):
        """Advance one audio block. -> list of 6 (pitch cents or None, gate on, pan, level)."""
        self.scrb = scrb_step(self.scrb, self.scrb_t)
        sf = self.scrb / ONE30
        out = []
        for v in self.v:
            if not v.started:
                out.append((None, False, v.pan, v.level))
                continue
            if v.path is not None:
                el = (self.b - v.t0 + 1) / HZ - v.delay
                lim = el if self.scrb >= ONE30 else min(el, sf * v.dur)
                v.cur = path_at(v.path, lim, v.dur, v.shape)
                if el >= v.dur and self.scrb >= ONE30:
                    v.path = None
            elif v.glide > 0.02:
                v.cur = v.tgt + (v.cur - v.tgt) * math.exp(-4.0 * DT / v.glide)
            else:
                v.cur = v.tgt
            if v.drift > 0:
                v.dr_n -= 1
                if v.dr_n <= 0:
                    v.dr_t = (v.rng.rand() * 2 - 1) * v.drift
                    v.dr_n = 3000 + ((6000 * v.rng.r24()) >> 24)
                v.dr += (v.dr_t - v.dr) * min(1.0, DT / 1.5)
            v.ph = (v.ph + 2 * math.pi * v.rate * DT) % (2 * math.pi)
            out.append((v.cur + v.dr + v.vib * math.sin(v.ph), v.on, v.pan, v.level))
        self.b += 1
        return out


def run(events, n_blocks, bpm=120.0, pattern=0):
    """events: {block: [('trig', step, Params[, oct[, pcs, root]]) | ('off',) | ('scrb', value)]}.
    -> (pitch[n_blocks][6] (nan when never started), gate[n_blocks][6], pans[6], levels[6] per block, model)."""
    m = DigiGlide(bpm, pattern)
    pitch, gate, pan, level = [], [], [], []
    for b in range(n_blocks):
        for ev in events.get(b, []):
            if ev[0] == "trig":
                m.trig(ev[1], ev[2], *ev[3:])              # ('trig', step, Params, root, pcs[, tail, revoice])
            elif ev[0] == "off":
                m.gate_off()
            elif ev[0] == "scrb":
                m.set_scrb(ev[1])
        row = m.block()
        pitch.append([float("nan") if c is None else c for c, _, _, _ in row])
        gate.append([g for _, g, _, _ in row])
        pan.append([pn for _, _, pn, _ in row])
        level.append([lv for _, _, _, lv in row])
    return pitch, gate, pan, level, m


def progression(steps, bars_per_chord, bpm=120.0, gate_bars=None, n_tail_bars=2):
    """steps: list of Params (one trig each, every bars_per_chord bars). The gate stays open until the last
    chord has played for gate_bars (default: its full slot), then closes. -> (events, n_blocks)."""
    bar = int(round(240.0 / bpm * HZ))
    ev = {}
    for k, p in enumerate(steps):
        ev.setdefault(k * bars_per_chord * bar, []).append(("trig", k * 16 * bars_per_chord, p))
    end = len(steps) * bars_per_chord * bar if gate_bars is None else ((len(steps) - 1) * bars_per_chord + gate_bars) * bar
    ev.setdefault(end, []).append(("off",))
    return ev, end + n_tail_bars * bar
