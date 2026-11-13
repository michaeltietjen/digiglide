"""Shared emulator helpers for the GLIDE tests: boot stock or a GLIDE image, set up the GLIDE track, place a progression,
read GLIDE's state, decode frames."""
import glob, os, struct, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import dn2paths as P
os.chdir(P.DIGIKIT)
import cfkit

U16 = lambda f, o: struct.unpack_from('>H', f, o)[0]
CHRD = dict(maj=0, min=1, sus2=2, sus4=3, dom7=4, maj7=5, m7=6, add9=7, maj9=8, oct5=9, quartal=10)
GLID = {'0': 0, '1/32': 1, '1/16': 2, '1/8': 3, '1/4': 4, '1/2': 5, '1bar': 6, '2bar': 7, '4bar': 8, '8bar': 9}
CURV = dict(linear=0, ease_out=1, ease_in_out=2)
NOTE = dict(C=0, Db=1, D=2, Eb=3, E=4, F=5, Gb=6, G=7, Ab=8, A=9, Bb=10, B=11)


def latest():
    return sorted(glob.glob(str(P.BUILD / 'DN2_1.11_GLIDE_*.syx')), key=lambda p: int(p.rsplit('_', 1)[1][:-4]))[-1]


def symbols(img):
    return {l.split()[-1]: int(l.split()[0], 16) for l in open(img[:-4] + '/symbols.txt')}


BE = cfkit.BE
QUARTER = 21_600_000
GLID_Q = {'0': 0, '1/32': 1 / 8, '1/16': 1 / 4, '1/8': 1 / 2, '1/4': 1, '1/2': 2, '1bar': 4, '2bar': 8, '4bar': 16, '8bar': 32}


def glid_blocks(glid, bpm):
    return int(round(GLID_Q[glid] * QUARTER / (240 * bpm)))


def midi(name):
    return 12 * (int(name[-1]) + 1) + NOTE[name[:-1]]          # MIDI numbering (C4 = 60); the Digitone screen shows 60 as C5, 36 as C3


def params(root='C3', chrd='maj', voic=0, glid='1/4', curv='ease_out', drft=20, track=0):
    return bytes([track, 0, midi(root), CHRD[chrd], voic, GLID[glid], CURV[curv], drft])


class Session:
    """One emulator run. img=None -> stock. Track 1 = GLIDE track (VOICES 4), its demo trigs cleared, other tracks muted
    of trigs too when solo=True (clean renders)."""

    def __init__(self, img=None, tag='stock', solo=True, reserve=4):
        self.img = img
        sec3 = img[:-4] + '/section_3.bin' if img else str(P.SEC3_STOCK)
        out = img[:-4] + '/emu_' + tag if img else str(P.BUILD / ('stock_emu' if tag == 'stock' else 'stock_' + tag))
        self.k = k = cfkit.Kit(sec3, str(P.STOCK), None, out)
        self.app = k.call(0x4018A97A)
        cfg = k.call(0x40030AF8, [k.call(0x4003E41A, [self.app])])
        k.call(0x40029094, [cfg, 0, reserve])               # track 1: VOICES = reserve (stock setter; 0 = DYN)
        self.ctx0 = k.call(0x4003EFDE, [self.app])
        for t in (range(16) if solo else (0,)):
            for st in range(128):                           # the demo pattern is 128 steps long
                k.call(0x40054690, [self.ctx0 + 132 * t, st, 1, 0])
        self.sym = symbols(img) if img else {}

    def trig_defaults(self, t=0):
        k = self.k
        ctx = self.ctx0 + 132 * t
        return k.call(k.h.u32(k.h.u32(ctx) + 40), [ctx]) + 0x480   # VEL, LEN, .., .., .., NOTE, NOT2..NOT4

    def trig(self, step, note=60, length=127, t=0):
        """A trig on `step` (0-based) of track t with NOTE / LEN (127 = INF) taken from the TRIG page defaults."""
        d = self.trig_defaults(t)
        self.k.h.w(d + 1, bytes([length]))
        self.k.h.w(d + 5, bytes([note]))
        self.k.call(0x40054690, [self.ctx0 + 132 * t, step, 1, 1])

    def progression(self, chords):
        """chords: list of params(...) bytes, one per chord trig (the M1-M3 stand-in for p-locks)."""
        if not self.img:
            return
        tbl = b''.join(chords)
        self.k.h.w(self.sym['glide_seq'], tbl)
        self.k.h.w(self.sym['glide_seq_n'], struct.pack('>I', len(chords)))

    def set_param(self, b):
        if self.img:
            self.k.h.w(self.sym['G'] + 16, b)                # G.param (after blocks, src, n, active)

    def play(self, blocks, bpm=120, each=None):
        return self.k.play(blocks, bpm=bpm, each=each)

    def state(self):
        return self.k.h.u32(self.sym['G']) if self.img else None


def note_ons(frames, voices=range(16)):
    out = []
    for i, f in enumerate(frames):
        on = U16(f, 0x22)
        for v in voices:
            if on >> v & 1:
                out.append((i, v, U16(f, 0x02 + 2 * v) / 256, U16(f, 0xA5A + 2 * v)))
    return out


def note_offs(frames, voices=range(16)):
    return [(i, v) for i, f in enumerate(frames) for v in voices if U16(f, 0x24) >> v & 1]


def pitch_trace(frames, v):
    return [U16(f, 0x02 + 2 * v) / 256 for f in frames]
