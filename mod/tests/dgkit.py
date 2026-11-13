"""Emulator helpers for the DigiGlide tests: boot stock or a DigiGlide image, set up the DigiGlide track (track 1,
VOICES = 6), place trigs, write the dg_seq test table (M3 stand-in for p-locks), read the frames, and run the M1
model on the same events for block-by-block comparison."""
import glob, os, struct, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
sys.path.insert(0, os.path.expanduser('~/glide/model'))
sys.path.insert(0, os.path.expanduser('~/glide/mod'))
import osver                                        # DG_OS: 1.12 (default) or 1.11; before cfkit
from osver import A
import dn2paths as P
import digiglide as G
os.chdir(P.DIGIKIT)
import cfkit

U16 = lambda f, o: struct.unpack_from('>H', f, o)[0]
# rev 6: the 18 parameters in page order (digiglide.c K_ order) and their defaults. They live in the kit now (the
# store: digiglide.c); SLOTS are the sound slots images <= 14 kept them in. Tests still name a parameter by that slot:
# Session wraps k.slot so that those slots read and write the track's store through the image's own dg_par /
# dg_par_set (k.sound_slot is the unwrapped call, for the sound's real slots).
FIELDS = ['type', 'ext', 'key', 'voic', 'pos', 'glid', 'play', 'hold', 'path', 'time', 'ordr', 'stag', 'move', 'drft',
          'vib', 'scrb', 'vcnt', 'bass']
SLOTS = [50, 51, 52, 53, 55, 93, 65, 94, 59, 60, 61, 62, 57, 63, 64, 58, 54, 56]
DEFAULTS = dict(type=0, ext=0, key=0, voic=127, pos=64, glid=2, play=0, hold=0, path=0, time=0, ordr=0, stag=0, move=0,
                drft=8, vib=4, scrb=127, vcnt=5, bass=2)      # vcnt: voices (3..6), 0 = OFF
MINE = 0x3F
SLOT0 = 50
SLOT_VCNT = 54                                      # VCNT, the switch: code 0 = OFF, 1..4 = 3..6 voices


class Ui(dict):
    """The DigiGlide parameters of a sound, by name: Ui(key=1, ext=2), .copy(glid=0). vcnt is in voices."""

    def __init__(self, **kw):
        super().__init__(DEFAULTS)
        for k, v in kw.items():
            if k not in DEFAULTS:
                raise KeyError(k)
            self[k] = v

    def copy(self, **kw):
        return Ui(**{**self, **kw})

    __getattr__ = dict.__getitem__


def slot_code(f, v):
    """a parameter's stored knob value."""
    return vcnt_code(v) if f == 'vcnt' else v + 2 if f == 'hold' else v     # HOLD: 2 = off, 3 = on
from emu import panelin  # noqa: E402


def vcnt_code(v):
    """VCNT as stored: 0 (OFF) or a voice count 3..6 -> its code."""
    return 0 if not v else v - 2


def latest():
    return sorted(glob.glob(str(P.BUILD / (osver.PREFIX + '*.syx'))), key=lambda p: int(p.rsplit('_', 1)[1][:-4]))[-1]


def symbols(img):
    return {l.split()[-1]: int(l.split()[0], 16) for l in open(img[:-4] + '/symbols.txt')}


def pbytes(p):
    return bytes(getattr(p, f) for f in FIELDS)


class Session:
    """img=None -> stock. Track 1 reserves `reserve` voices; every track's demo trigs are cleared when solo."""

    def __init__(self, img=None, tag='stock', solo=True, reserve=6):
        self.img = img
        sec3 = img[:-4] + '/section_3.bin' if img else osver.SEC3_STOCK
        out = img[:-4] + '/emu_' + tag if img else (osver.STOCK_EMU if tag == 'stock' else osver.STOCK_EMU.replace('_emu', '_' + tag))
        self.k = k = cfkit.Kit(sec3, osver.STOCK_SYX, None, out)
        self.app = k.call(A(0x4018A97A))
        cfg = k.call(A(0x40030AF8), [k.call(A(0x4003E41A), [self.app])])
        k.call(A(0x40029094), [cfg, 0, reserve])
        self.ctx0 = k.call(A(0x4003EFDE), [self.app])
        for t in (range(16) if solo else (0,)):
            for st in range(128):
                k.call(A(0x40054690), [self.ctx0 + 132 * t, st, 1, 0])
        self.sym = symbols(img) if img else {}
        k.sound_slot = k.slot
        if 'dg_par' in self.sym:
            k.slot = self._slot
        if 'dg_vchk' in self.sym:                         # a session starts mid-life: DigiGlide has looked at every
            k.h.w(self.sym['dg_vchk'], bytes([1] * 16))     # track's voices once (test_voices_pool clears it)

    def store(self):
        """the current kit's store: its record in the working image + 0x28af ("DGK1", then 18 bytes a track)."""
        kit = (self.k.h.u32(A(0x800052A0)) - A(0x4210C08C)) // 0x5d71
        return A(0x405CD96C) + 0xae0200 + 0x2a00 * kit + 0x28af

    def _slot(self, t, sl, value=None):
        k = self.k
        if sl not in SLOTS:
            return k.sound_slot(t, sl, value)
        i = SLOTS.index(sl)
        if value is None:
            return k.call(self.sym['dg_par'], [t, i]) & 0xFFFF
        if i == 7 and value not in (0x200, 0x300):      # not a HOLD value: the track was never set up
            k.h.w(self.store() + 4 + 18 * t + 7, bytes([0]))
        else:
            k.call(self.sym['dg_par_set'], [t, i, value])

    def marked(self, t=0):
        return bool(self.k.call(self.sym['dg_marked'], [t]))

    def active_track(self):
        return self.k.call(A(0x40046BFE), [self.app + 48])

    def select_track(self, t, tries=4):
        """[TRK] + [TRIG t + 1]: make track t (0-based) the active track."""
        h = self.k.h
        for _ in range(tries):
            if self.active_track() == t:
                return True
            h.press(cfkit.KEYS['TRK'], 500_000); h.frames(20)
            h.press(cfkit.TRIG(t + 1), 500_000); h.frames(20)
            h.release(cfkit.TRIG(t + 1)); h.frames(20)
            h.release(cfkit.KEYS['TRK']); h.frames(20)
            h.run(60_000_000)
        return self.active_track() == t

    def trig_defaults(self, t=0):
        k = self.k
        ctx = self.ctx0 + 132 * t
        return k.call(k.h.u32(k.h.u32(ctx) + 40), [ctx]) + 0x480

    def trig(self, step, note=60, length=127, t=0):
        d = self.trig_defaults(t)
        self.k.h.w(d + 1, bytes([length]))
        self.k.h.w(d + 5, bytes([note]))
        self.k.call(A(0x40054690), [self.ctx0 + 132 * t, step, 1, 1])

    def set_sound(self, p, t=0, on=True, atk=64, mach=1):
        """Make track t a DigiGlide track: parameters p (a Ui) in the kit's store, VCNT as its code (p.vcnt voices;
        on=False stores OFF). mach: the machine the track must have (1 = WAVETONE, as the older tests assume; None =
        whatever it has). atk: AMP ATK (64, a pad: a held chord glides to the next trig; under 32 every trig
        strikes it again; None = the sound's own)."""
        if mach is not None and self.k.mach(t) != mach:
            self.k.select(mach, track=t)
        if atk is not None:
            self.k.sound_slot(t, 81, atk << 8)
        if not self.sym:                                # stock: no store, and the sound's slots stay stock's
            return
        for i, f in enumerate(FIELDS):
            v = p[f]
            if f == 'vcnt' and not on:
                v = 0
            self.k.slot(t, SLOTS[i], slot_code(f, v) << 8)

    def lock(self, step, t=0, **fields):
        """P-lock DigiGlide parameters on a step (0-based) of track t, e.g. lock(4, deg=5, glid=0); vcnt=0 locks OFF."""
        ctx = self.ctx0 + 132 * t                       # (rev 6: honoured on a WAVETONE track, the lanes images <= 14 used)
        for f, v in fields.items():
            r = self.k.call(A(0x4004F8FE), [ctx, step, SLOTS[FIELDS.index(f)], slot_code(f, v) << 8])
            assert r & 0xFF, f'lock {f} on step {step} refused'

    def trig_log(self):
        """A per-ISR callback recording DG.trigs; .blocks(frames) maps the trigs to frame indices."""
        return TrigLog(self)

    def play(self, blocks, bpm=120, each=None):
        return self.k.play(blocks, bpm=bpm, each=each)

    def tails(self):
        """dg_tail_log: bit 0 = the last trig glided from a released chord that still rang, bit 1 the one before, ..."""
        return self.k.h.u32(self.sym['dg_tail_log'])

    def dg(self):
        """DG state: blocks, trigs, src, active, was_on, last_step, last_tempo, last_note, step_log[16], track, locks."""
        b = bytes(self.k.h.r(self.sym['DG'], 56))
        w = struct.unpack('>8I', b[:32])
        tr, lk = struct.unpack('>iI', b[48:56])
        return dict(blocks=w[0], trigs=w[1], src=w[2], active=w[3], was_on=w[4], last_step=w[5], last_tempo=w[6],
                    last_note=w[7], step_log=list(b[32:48]), track=tr, locks=lk)

    def syn_page(self, want, tries=8):
        """Tap [SYN] until the SYN page index `want` is drawn (3 = HARMONY, 4 = MOTION on a DigiGlide track)."""
        for _ in range(tries):
            self.k.tap('SYN')
            if self.drawn_page() == want:
                return True
        return False

    def drawn_page(self, settle=6):
        """dg_ui_page once the screen has caught up with the last key: it is set when a SYN page is drawn, and on
        1.12 the redraw can land well after the tap (read it until two reads 150M instructions apart agree)."""
        h = self.k.h
        rd = lambda: struct.unpack('>i', bytes(h.r(self.sym['dg_ui_page'], 4)))[0]
        last = rd()
        for _ in range(settle):
            h.frames(20); h.run(150_000_000)
            now = rd()
            if now == last:
                return now
            last = now
        return last

    # -- panel gestures (the panel sends a whole group's state: keys of one group are pressed together) --------------
    def _btn(self, group, mask, n):
        h = self.k.h
        h.pc = panelin.buttons(h.m, h.profile, group, mask); h.run(n); h.frames(12)

    def shortcut(self):
        """[FUNC] (2, 0) held, push encoder E (5, 4), release both: DigiGlide's on/off shortcut."""
        self._btn(2, 0x01, 500_000); self._btn(5, 0x10, 500_000)
        self._btn(5, 0x00, 15_000_000); self._btn(2, 0x00, 15_000_000)
        self.k.h.run(40_000_000)

    def func_with(self, group, bit):
        """[FUNC] + one key, e.g. func_with(1, 1) = [FUNC] + [YES] (stock's pattern save), (1, 3) = + [NO] (reload)."""
        both = 0x01 | (1 << bit) if group == 2 else None
        self._btn(2, 0x01, 500_000)
        if both is not None:
            self._btn(2, both, 500_000); self._btn(2, 0x01, 15_000_000)
        else:
            self._btn(group, 1 << bit, 500_000); self._btn(group, 0, 15_000_000)
        self._btn(2, 0x00, 15_000_000)
        self.k.h.run(60_000_000)

    def vcnt(self, t=0):
        return self.k.slot(t, SLOT_VCNT)

    def cur(self):
        """The parameters the last event read (dg_ui), as a Ui (vcnt in voices, 0 = OFF)."""
        b = bytes(self.k.h.r(self.sym['dg_ui'], 18))
        u = Ui(**dict(zip(FIELDS, b)))
        u['vcnt'] = u['vcnt'] + 2 if u['vcnt'] else 0
        return u

    def chord_name(self, t=0):
        """The chord name the pages show for track t ('' when none sounds)."""
        p = self.k.call(self.sym['dg_chord_name'], [t])
        return bytes(self.k.h.r(p, 16)).split(b'\0')[0].decode() if p else ''


class TrigLog:
    def __init__(self, s):
        self.s, self.counts, self.params, self.locks = s, [], [], []

    def __call__(self, i):
        d = self.s.dg()
        if self.counts and d['trigs'] != self.counts[-1]:
            self.params.append(self.s.cur())
            self.locks.append(d['locks'])
        elif not self.counts and d['trigs']:
            self.params.append(self.s.cur())
            self.locks.append(d['locks'])
        self.counts.append(d['trigs'])

    def isr_blocks(self):
        """ISR index where each trig was processed."""
        out, prev = [], 0
        for i, c in enumerate(self.counts):
            if c != prev:
                out.append(i)
                prev = c
        return out


def word(f, v):
    return U16(f, 0x02 + 2 * v)


def edges(frames):
    """-> (blocks with DigiGlide note-ons, blocks with DigiGlide note-offs)."""
    ons = [i for i, f in enumerate(frames) if U16(f, 0x22) & MINE]
    offs = [i for i, f in enumerate(frames) if U16(f, 0x24) & MINE]
    return ons, offs


def chord_event(u, note=60, locks=()):
    """What the hook makes of a key on a DigiGlide track (rev 5): the note is the root; TYPE / EXT / KEY give the
    tones (a p-locked TYPE / EXT, named in locks, beats KEY). u: a Ui. -> (engine Params, root, pitch classes)."""
    pcs, sk, sc = G.chord_for(note, u.type, u.ext, u.key, 'type' in locks, 'ext' in locks)
    p = G.Params(key=sk, scl=sc, voic=u.voic, pos=u.pos, vcnt=u.vcnt, bass=u.bass, sprd=77, move=u.move, glid=u.glid,
                 path=u.path, time=u.time, ordr=u.ordr, stag=u.stag, drft=u.drft, vib=u.vib, scrb=u.scrb)
    return p, max(G.ROOT_LO, min(G.ROOT_HI, note)), pcs


def model(events, n_blocks, tempo_word, pattern=0, tails=0):
    """events: {block: [('trig', step, Ui, note[, locks]) | ('off',) | ('revoice', Ui)]} -> (pitch cents [n][6],
    nan = not started; gate; the model). A trig is turned into the chord event the hook fires; with GLID 0 and a
    chord sounding the hook releases it first (the chord retriggers). tails: the hook's dg_tail_log."""
    ev2 = {}
    n_trigs = sum(1 for lst in events.values() for e in lst if e[0] == 'trig')
    k, last, sounding = 0, None, False
    for b in sorted(events):
        for e in events[b]:
            if e[0] == 'trig':
                p, root, pcs = chord_event(e[2], e[3], e[4] if len(e) > 4 else ())
                if p.glid == 0 and sounding:
                    ev2.setdefault(b, []).append(('off',))
                e = ('trig', e[1], p, root, pcs, bool(tails >> (n_trigs - 1 - k) & 1), False)
                last, sounding = (e[1], root, pcs), True
                k += 1
            elif e[0] == 'revoice':
                p, _, _ = chord_event(e[1], last[1])
                e = ('trig', last[0], p.copy(key=G.chord_for(last[1], e[1].type, e[1].ext, e[1].key)[1]), last[1], last[2], False, True)
            elif e[0] == 'off':
                sounding = False
            ev2.setdefault(b, []).append(e)
    pitch, gate, pan, level, m = G.run(ev2, n_blocks, tempo_word / 120.0, pattern)
    return pitch, gate, m
