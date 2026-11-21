"""DigiGlide build 29: TUNE (EQL / PURE) and FAN, both p-lockable, on the new TUNE page (the fourth DigiGlide page).
Pitches are read from the note words of the frames the DSP is sent (1/256 semitone, 0.39 cent a step).
  A  TUNE PURE, every TYPE x EXT: each chord note within 0.5 cent of its ratio above the root (5/4, 6/5, 4/3, 3/2,
     5/3, 8/5, 15/8, 9/5, octaves 2; also 9/8 and the DIM chord's 7/5), the root's pitch class equal tempered
  B  TUNE EQL: the same chords, every note word a whole semitone
  C  FAN 127: the chord voices evenly either side, 20 cents at the outer ones (4 voices: the inner two at a third);
     FAN 64 half of that; 3, 5 and 6 voices; the bass voice (BASS FOL) is not fanned
  D  FAN 0 and TUNE EQL: the frames' note, gate, velocity and level words are those of image 28, block for block,
     over a 4-chord progression with DRFT and VIB on
  E  a glide (GLID 1/4) with TUNE PURE runs from the first chord's tuned pitches to the second's, each voice one way
  F  locks: TUNE and FAN locked on a step are read on that step only; a FAN lock is one of 8 levels; BPAT and BLOOM
     locks in the same lane keep their values; a word an older image wrote reads as before; the step with the lock
     plays PURE and fanned, the step without EQL
  G  the store: the two bytes a track in the kit record's padding; a kit saved by image 28 reads EQL and 0; kept per
     track; the store's bytes copied out, cleared and put back give the same values (nothing is kept in RAM only);
     a DGK1 kit converts with EQL and 0
  H  the page: [SYN] reaches a fourth DigiGlide page; knob A turns TUNE and changes only its buffer word in the live
     kit; the TUNE and FAN rows are lockable
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b29_tune.py [DIGIGLIDE.syx] [IMAGE_28.syx]"""
import math, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
old = sys.argv[2] if len(sys.argv) > 2 else img.rsplit('_', 1)[0] + '_28.syx'
only = os.environ.get('ONLY', 'ABCDEFGH')
print('image', os.path.basename(img), ' against', os.path.basename(old))
K_TYPE, K_EXT, K_VCNT, K_BPAT, K_BLOOM, K_TUNE, K_FAN = 0, 1, 16, 19, 21, 24, 25
RATIO = [1, 16 / 15, 9 / 8, 6 / 5, 5 / 4, 4 / 3, 7 / 5, 3 / 2, 8 / 5, 5 / 3, 9 / 5, 15 / 8]
PURE = [1200 * math.log2(r) for r in RATIO]
TYPES = ['MAJ', 'MIN', 'SUS', 'DIM', '5TH']
EXTS = ['NONE', '6', '7', 'MAJ7', '9', '6+9', '7+9', 'M7+9']
ROOT = 48
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def session(image, tag, trigs=((0, ROOT),), **kw):
    s = Session(image, tag='b29' + tag, solo=True)
    u = dict(vcnt=4, type=0, ext=0, glid=0, voic=64, bass=0, hold=0, drft=0, vib=0); u.update(kw)
    s.set_sound(Ui(**u), t=0, mach=None, atk=None)
    for st, n in trigs:
        s.trig(st, note=n, length=127, t=0)
    return s


def par(s, k, v, t=0):
    s.k.call(s.sym['dg_par_set'], [t, k, v << 8])


cents = lambda f, v: U16(f, 2 + 2 * v) * 100 / 256
gates = lambda fr, n: [v for v in range(n) if any(U16(f, 0x22) >> v & 1 for f in fr)]


def interval(c, root=ROOT):
    """cents above the root's pitch class -> (interval class, error from its pure ratio, error from equal)."""
    d = (c - root * 100) % 1200
    k = round(d / 100) % 12
    wrap = lambda e: min(abs(e), 1200 - abs(e))
    return k, wrap(d - PURE[k]), wrap(d - 100 * k)


if 'A' in only or 'B' in only:
    s = session(img, 'a')
    worst, seen, bad, eq_bad = 0.0, set(), [], []
    for tune in (1, 0):
        par(s, K_TUNE, tune)
        for ty in range(5):
            for ex in range(8):
                par(s, K_TYPE, ty); par(s, K_EXT, ex)
                for _ in range(4):                      # (the emulated panel can drop the [PLAY] tap)
                    fr = s.play(260, bpm=120)
                    vs = gates(fr, 4)
                    if vs:
                        break
                got = [interval(cents(fr[-8], v)) for v in vs]
                if tune:
                    seen |= {k for k, _, _ in got}
                    worst = max([worst] + [e for _, e, _ in got])
                    if len(vs) < 2 or any(e > 0.5 for _, e, _ in got):
                        bad.append((TYPES[ty], EXTS[ex], [(k, round(e, 2)) for k, e, _ in got]))
                elif len(vs) < 2 or any(e > 0.001 for _, _, e in got):
                    eq_bad.append((TYPES[ty], EXTS[ex], [(k, round(e, 2)) for k, _, e in got]))
    stated = {0, 3, 4, 5, 7, 8, 9, 10, 11}
    check(not bad and worst <= 0.5, f'A PURE: 40 chords (5 TYPE x 8 EXT), every note within 0.5 cent of its ratio (worst {worst:.2f} cent; interval classes played {sorted(seen)}; failing {bad[:3]})')
    check(stated - {8} <= seen, f'A the chords play the thirds, fourth, fifth, sixth and sevenths (classes {sorted(seen)}; 8, the minor sixth 8/5, is in no chord type: {8 in seen})')
    check(not eq_bad, f'B EQL: the same 40 chords, every note word a whole semitone (failing {eq_bad[:3]})')

if 'C' in only:
    for n, fan, bass in ((4, 127, 0), (4, 64, 0), (3, 127, 0), (5, 127, 0), (6, 127, 0), (5, 127, 3)):
        s = session(img, f'c{n}{fan}{bass}', vcnt=n, bass=bass)
        par(s, K_FAN, fan)
        fr = s.play(260, bpm=120)
        f = fr[-8]
        nc = n - 1 if bass else n
        off = [cents(f, v) - round(cents(f, v) / 100) * 100 for v in range(n)]
        want = [20 * fan / 127 * (2 * i - (nc - 1)) / (nc - 1) for i in range(nc)] + ([0] if bass else [])
        check(all(abs(a - b) <= 0.3 for a, b in zip(off, want)),
              f'C FAN {fan}, {n} voices{", BASS FOL (the last is the bass)" if bass else ""}: cents from the note {[round(x, 1) for x in off]} (want {[round(x, 1) for x in want]})')

if 'D' in only:
    res = {}
    for name, image in (('new', img), ('old', old)):
        s = session(image, 'd' + name, trigs=((0, 48), (8, 53), (16, 55), (24, 50)), vcnt=5, type=1, ext=2, glid=3,
                    bass=3, hold=1, drft=8, vib=4)
        res[name] = [bytes(f[0x02:0x94]) for f in s.play(3400, bpm=120)]
    n = min(len(res['new']), len(res['old']))
    # (image 33: a chord event on a note frame is worked out a block later and caught up, so a glide may run one block
    #  early: pitch words within 6/256 semitone of image 28's, every other word equal)
    pw = lambda r: struct.unpack('>16H', r[0:0x20])
    # (image 34: a chord's note-ons and note-offs go out one block after they are worked out)
    diff = [i for i in range(n) if res['new'][i][0x20:] not in (res['old'][i][0x20:], res['old'][max(i - 1, 0)][0x20:])
            or max(abs(a - b) for a, b in zip(pw(res['new'][i]), pw(res['old'][i]))) > 6]
    edge = {i + j for i in range(n) for j in (0, 1) if res['old'][i][0x20:0x28] != bytes(8)}
    diff = [i for i in diff if i not in edge]            # (a voice keeps its note until its note-on's frame)
    near = sum(res['new'][i] != res['old'][i] for i in range(n))
    moving = len({r[0:12] for r in res['new']})
    check(n >= 3300 and not diff and moving > 500,
          f'D FAN 0, TUNE EQL: gate, velocity and level words as image 28 over {n} blocks, note words within 6/256 semitone ({near} blocks not identical, {len(diff)} differ, first {diff[:3]}; {moving} different pitch sets, so the chords glide and drift)')

if 'E' in only:
    s = session(img, 'e', trigs=((0, 48), (8, 53)), glid=3, type=1, ext=2, hold=1)
    par(s, K_TUNE, 1)
    fr = s.play(2600, bpm=120)
    a, b = fr[1480], fr[2500]
    e0 = max(interval(cents(a, v), 48)[1] for v in range(4))
    e1 = max(interval(cents(b, v), 53)[1] for v in range(4))
    mono = True
    for v in range(4):
        seq = [U16(f, 2 + 2 * v) for f in fr[1480:2500]]
        d = [y - x for x, y in zip(seq, seq[1:]) if y != x]
        mono &= bool(d) and (all(x > 0 for x in d) or all(x < 0 for x in d))
    moved = [round(cents(b, v) - cents(a, v)) for v in range(4)]
    check(e0 <= 0.5 and e1 <= 0.5 and mono,
          f'E a 1/4 glide from C MIN7 to F MIN7, PURE: starts {e0:.2f} cent and lands {e1:.2f} cent from the ratios, every voice moves one way (cents moved {moved})')

if 'F' in only:
    s = session(img, 'f', trigs=((0, 48), (8, 48)))
    k, h = s.k, s.k.h
    pat = h.u32(A(0x42C5A9A0)); lt = pat + 97872
    sgn = lambda x: struct.unpack('>i', struct.pack('>I', x & 0xFFFFFFFF))[0]
    get = lambda step, kk: sgn(k.call(s.sym['dg_lock_get'], [0, step, kk]))
    put = lambda step, kk, v: k.call(s.sym['dg_lock_put'], [0, step, kk, v & 0xFFFFFFFF]) & 0xFF

    def lane(step, slot=65):
        i = h.r(lt + 20640 + slot, 1)[0]
        return None if i >= 128 else struct.unpack('>h', bytes(h.r(lt + 2 + 258 * i + 2 * step, 2)))[0]

    def read(step):
        k.call(s.sym['dg_test_read'], [0, step])
        u = bytes(h.r(s.sym['dg_ui'], 26))
        return u[K_TUNE], u[K_FAN]

    r = (put(8, K_TUNE, 1), put(8, K_FAN, 100))
    w = lane(8)
    check(all(r) and w == 1161 * (2 + 3 * 7) and (get(8, K_TUNE), get(8, K_FAN)) == (1, 109) and read(8) == (1, 109)
          and read(0) == (0, 0),
          f'F TUNE PURE and FAN 100 locked on step 9: word {w}, read back {get(8, K_TUNE)} and {get(8, K_FAN)} (a FAN lock is one of 8 levels); step 9 plays {read(8)}, step 1 {read(0)}')
    levels = []
    for v in (0, 9, 18, 30, 60, 80, 100, 127):
        put(4, K_FAN, v); levels.append(get(4, K_FAN))
    put(4, K_FAN, -1)
    check(levels == [0, 0, 18, 36, 54, 73, 109, 127] and lane(4) == -1,
          f'F FAN locks 0 9 18 30 60 80 100 127 read {levels}; unlocked: word {lane(4)}')
    put(8, K_BPAT, 2); put(8, K_BLOOM, 70)
    w2 = lane(8)
    r2 = (get(8, K_BPAT), get(8, K_BLOOM), get(8, K_TUNE), get(8, K_FAN))
    put(8, K_BPAT, -1); put(8, K_BLOOM, -1)
    check(w2 == 3 + 9 * 71 + 1161 * 23 and r2 == (2, 70, 1, 109) and lane(8) == w and 0 < w2 < 32768,
          f'F with BPAT and BLOOM locked too: word {w2}, fields {r2}; those two unlocked again: word {lane(8)}')
    assert k.call(A(0x4004F8FE), [s.ctx0, 12, 65, 3 + 9 * 65]) & 0xFF          # as image 23..28 wrote it
    r3 = (get(12, K_BPAT), get(12, K_BLOOM), get(12, K_TUNE), get(12, K_FAN))
    put(12, K_TUNE, 1)
    r4 = (lane(12), get(12, K_BPAT), get(12, K_BLOOM), get(12, K_TUNE))
    check(r3 == (2, 64, -1, -1) and r4 == (3 + 9 * 65 + 1161 * 2, 2, 64, 1),
          f'F a word image 28 wrote (BPAT 2, BLOOM 64): {r3}; TUNE locked onto it: {r4}')
    k.call(A(0x4004F8FE), [s.ctx0, 12, 65, 0xFFFF])
    fr = s.play(2400, bpm=120)
    f0, f1 = fr[1400], fr[2300]
    first = [interval(cents(f0, v)) for v in range(4)]
    second = [cents(f1, v) for v in range(4)]
    eq0 = max(e for _, _, e in first)
    fan = [20 * 109 / 127 * (2 * i - 3) / 3 for i in range(4)]
    e1 = max(interval(c - fan[v])[1] for v, c in enumerate(second))
    spread = max(second) % 100, min(second) % 100
    check(eq0 <= 0.001 and e1 <= 0.6,
          f'F played: step 1 (no lock) equal tempered ({eq0:.2f} cent off), step 9 (locked) PURE and fanned ({e1:.2f} cent from ratio + fan)')

if 'G' in only:
    s = session(img, 'g')
    st, h = s.store(), s.k.h
    rd = lambda t, kk: s.k.call(s.sym['dg_par'], [t, kk]) >> 8
    h.w(st + 276, b'\0' * 32)                               # as image 28 left the padding
    r0 = (rd(0, K_TUNE), rd(0, K_FAN))
    par(s, K_TUNE, 1); par(s, K_FAN, 77); par(s, K_FAN, 127, t=3)
    b = bytes(h.r(st, 337))
    r1 = (rd(0, K_TUNE), rd(0, K_FAN), rd(3, K_TUNE), rd(3, K_FAN), rd(5, K_TUNE), rd(5, K_FAN))
    check(r0 == (0, 0) and r1 == (1, 77, 0, 127, 0, 0) and b[276] == 2 and b[292] == 78 and b[295] == 128
          and not any(b[308:]),
          f'G store: an image 28 kit reads {r0}; set: track 1 {r1[:2]}, track 4 {r1[2:4]}, track 6 {r1[4:]}; bytes +276 {b[276]}, +292 {b[292]}, +295 {b[295]}, nothing past +308')
    h.w(st, b'\0' * 337)
    gone = (rd(0, K_TUNE), rd(0, K_FAN), bool(s.marked(0)))
    h.w(st, b)
    back = (rd(0, K_TUNE), rd(0, K_FAN), rd(3, K_FAN), rd(0, 23), bool(s.marked(0)))
    check(gone == (0, 0, False) and back == (1, 77, 127, 64, True),
          f'G the store\'s bytes cleared: {gone}; put back: {back} (all of it is in the kit record)')
    oldkit = bytearray(4 + 18 * 16 + 16)
    oldkit[0:4] = b'DGK1'
    for kk, v in enumerate([2, 3, 5, 90, 70, 4, 1, 2, 3, 1, 2, 3, 4, 20, 10, 100, 3, 2]):
        oldkit[4 + kk] = v
    h.w(st, b'\0' * 337); h.w(st, bytes(oldkit))
    par(s, K_BLOOM, 40)
    r2 = (bytes(h.r(st, 4)), rd(0, K_TUNE), rd(0, K_FAN), rd(0, 2))
    check(r2 == (b'DGK2', 0, 0, 5), f'G a DGK1 kit converts with TUNE EQL, FAN 0: {r2}')

if 'H' in only:
    s = session(img, 'h')
    k, h = s.k, s.k.h
    h.out = os.path.expanduser('~/glide/renders/b29')
    os.makedirs(h.out, exist_ok=True)
    h.frames(3200)
    k.tap('SYN'); h.frames(2200)
    seen = []
    for _ in range(11):
        k.tap('SYN')
        seen.append(s.drawn_page())
    first = struct.unpack('>i', bytes(h.r(s.sym['dg_ui_first'], 4)))[0]
    check(first >= 0 and {first, first + 1, first + 2, first + 3} <= set(seen) and max(seen) == first + 3,
          f'H [SYN] reaches four DigiGlide pages after the machine\'s own {first} (pages drawn {seen})')
    s.syn_page(first + 3)
    h.png('page_tune.png')
    kit0 = bytes(h.r(h.u32(A(0x800052A0)), 0x5d71))
    rd = lambda kk: s.k.call(s.sym['dg_par'], [0, kk]) >> 8
    for burst in (11, 11, 7):
        if h.turn_to(0, lambda: rd(K_TUNE), 1, burst=burst, tries=80):
            break
    h.frames(300); h.run(400_000_000)
    kit1 = bytes(h.r(h.u32(A(0x800052A0)), 0x5d71))
    diff = [i for i in range(len(kit0)) if kit0[i] != kit1[i]]
    buf = 0x48e4 + 2 * 94
    check(rd(K_TUNE) == 1 and diff and set(diff) <= {buf, buf + 1},
          f'H knob A on the TUNE page: TUNE {rd(K_TUNE)} (PURE); in the live kit only its buffer word changed (bytes {[hex(x) for x in diff[:6]]})')
    h.png('page_tune_pure.png')
    for burst in (11, 11, 7):
        if h.turn_to(1, lambda: rd(K_FAN), 127, burst=burst, tries=80):
            break
    h.frames(300); h.run(400_000_000)
    kit2 = bytes(h.r(h.u32(A(0x800052A0)), 0x5d71))
    diff = [i for i in range(len(kit1)) if kit1[i] != kit2[i]]
    check(rd(K_FAN) >= 100 and diff and set(diff) <= {buf + 2, buf + 3},   # (the emulated knob lands near the top)
          f'H knob B: FAN {rd(K_FAN)}; only its buffer word changed (bytes {[hex(x) for x in diff[:6]]})')
    h.png('page_tune_fan.png')
    rows = [struct.unpack('>17I', bytes(h.r(k.call(s.sym['dg_row'], [kk]), 68))) for kk in range(26)]
    lockable = sorted(kk for kk in range(26) if not rows[kk][0] & 8)
    check(lockable == [0, 1, 3, 4, 5, 12, 24, 25], f'H lockable rows: {lockable} (TYPE EXT VOIC POS GLID MOVE, TUNE FAN)')

print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
