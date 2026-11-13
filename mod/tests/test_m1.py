"""M1: a trig on the GLIDE track plays ROOT + CHRD as stacked notes; the right note numbers reach the DSP frame.

Same gesture on stock (control) and on GLIDE: track 1 reserves 4 voices (stock VOICE setter), its demo trigs are cleared,
one trig on step 1; the rest of the demo pattern plays as is. Checks, from the SPI frames the OS sends:
  - stock: track 1 starts ONE voice (the trig note n);
  - GLIDE: on that block voices 0..2 start together with ROOT + (n - 60) + {0, 4, 7}, all on track 1, each carrying the
    source voice's sound record, velocity, level and machine; voice 3 silent;
  - every other track's note-ons are identical to stock (track, note), and stay on voices 4..15.
    ~/dn2-workspace/repos/digikit/.venv-fast/bin/python test_m1.py [GLIDE.syx]
"""
import glob, os, struct, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import dn2paths as P
os.chdir(P.DIGIKIT)
import cfkit

U16 = lambda f, o: struct.unpack_from('>H', f, o)[0]
ROOT, CHORD = 48, (0, 4, 7)


def latest():
    return sorted(glob.glob(str(P.BUILD / 'DN2_1.11_GLIDE_*.syx')), key=lambda p: int(p.rsplit('_', 1)[1][:-4]))[-1]


def run(sec3, out, blocks=400):
    k = cfkit.Kit(sec3, str(P.STOCK), None, out)
    app = k.call(0x4018A97A)
    cfg = k.call(0x40030AF8, [k.call(0x4003E41A, [app])])
    k.call(0x40029094, [cfg, 0, 4])                         # track 1: VOICES = 4 (stock setter)
    ctx = k.call(0x4003EFDE, [app])
    for st in range(64):
        k.call(0x40054690, [ctx, st, 1, 0])                 # clear track 1's demo trigs
    k.call(0x40054690, [ctx, 0, 1, 1])                      # one trig on step 1
    fr = k.play(blocks, bpm=120)
    ons = []
    for i, f in enumerate(fr):
        on = U16(f, 0x22)
        for v in range(16):
            if on >> v & 1:
                ons.append((i, v, U16(f, 0x02 + 2 * v), U16(f, 0xA5A + 2 * v)))
    return k, fr, ons


img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
_, sfr, s_on = run(str(P.SEC3_STOCK), str(P.BUILD / 'stock_emu'))
k, gfr, g_on = run(img[:-4] + '/section_3.bin', img[:-4] + '/emu_out')

ok = True
def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg)

s1 = [e for e in s_on if e[3] == 0]
check(len(s1) == 1, f'stock: track 1 starts one voice {[(v, n / 256) for _, v, n, _ in s1]}')
n = s1[0][2] >> 8 if s1 else 60
want = [(ROOT + n - 60 + c) * 256 for c in CHORD]
g1 = [e for e in g_on if e[3] == 0]
blk = {e[0] for e in g1}
check(len(blk) == 1, f'GLIDE: track 1 note-ons all in one block {sorted(blk)}')
check(sorted(v for _, v, _, _ in g1) == [0, 1, 2], f'GLIDE: voices {sorted(v for _, v, _, _ in g1)} (want 0 1 2)')
check(sorted(x for _, _, x, _ in g1) == want,
      f'GLIDE: notes {[x / 256 for _, _, x, _ in sorted(g1, key=lambda e: e[2])]} (want {[w / 256 for w in want]})')
if g1:
    f = gfr[g1[0][0]]
    src = [v for v in (0, 1, 2) if True]
    rec = lambda v: f[0xDA + 146 * v:0xDA + 146 * (v + 1)]
    same = all(rec(v) == rec(0) and U16(f, 0x34 + 2 * v) == U16(f, 0x34) and U16(f, 0x74 + 2 * v) == U16(f, 0x74)
               and U16(f, 0x94 + 2 * v) == U16(f, 0x94) for v in (1, 2))
    check(same, 'GLIDE: chord voices carry the same sound record, velocity, level, machine')
    check(not (U16(f, 0x22) >> 3 & 1), 'GLIDE: voice 3 silent for a triad')
others = lambda ons: sorted((t, x) for _, _, x, t in ons if t != 0)
check(others(s_on) == others(g_on), f'other tracks: same (track, note) note-ons as stock ({len(others(s_on))})')
check(all(v >= 4 for _, v, _, t in g_on if t != 0), 'other tracks stay on voices 4..15')
G = int([l.split()[0] for l in open(img[:-4] + '/symbols.txt') if l.split()[-1] == 'G'][0], 16)
check(k.h.u32(G) > 300, f'hook live: {k.h.u32(G)} blocks')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
