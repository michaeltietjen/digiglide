"""DigiGlide rev 5 (Orchid-style): one key = one chord. Everything runs the way the unit is: VOICES at its default
(DigiGlide reserves its own voices) and, where it says so, the demo's other tracks playing.

  A  switching on: VCNT 5 on a stock sound raises the track's VOICES to 5 and writes every parameter's default once
     (stock sounds hold leftovers in these slots: 39 where SCRB was, which stopped every glide a third of the way).
  B  twelve keys, the other tracks playing: C5 .. B5 chromatic, TYPE MAJ. No note-on of the track outside DigiGlide's
     voices and no other track on them; 12 chord events; only the first attacks, the 11 changes glide; every voice on
     the M1 model's note; twelve different chords, each the major triad of its key; the bass voice is the key an octave
     down; the chord's own lowest voice is the key itself; the name shown is the chord.
  C  KEY C major, the white keys: the seven diatonic qualities (names and pitch classes); with EXT 7 the diatonic
     sevenths; a p-locked TYPE on a step beats KEY.
  D  live keys against stock: the note stock plays for a key is DigiGlide's root (same pitch class and octave);
     three keys at once are one chord on the lowest.
  E  HOLD: on = the chord stays after release, the next key glides (no attack), the same key again releases, [STOP]
     releases; off = release on key-up.
  F  short notes: with a long amp release each chord attacks again and glides from the ringing one; GLID 0: every
     chord retriggers and jumps.
  G  VOIC and POS turned while a chord is held: the voices glide to the new voicing, no attack.
  H  BASS OFF: no bass voice; BASS SOLO: the bass voice alone.
  I  VCNT OFF on every track: frames byte-identical to stock OS.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_rev5.py [DIGIGLIDE.syx]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, G, U16, Ui, FIELDS, SLOTS, model, chord_event, slot_code
from osver import A
from emu import panelin

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
GAP = 1500                                               # a trig every 8 steps at 120 BPM


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def voices_of(s, t):
    k = s.k
    cfg = s.app + 244 + 17092
    data = k.call(k.h.u32(k.h.u32(cfg) + 40), [cfg])
    return k.h.r(data + 5 * t + 1, 1)[0], sum(k.h.r(data + 5 * j + 1, 1)[0] for j in range(t))


def redraw(s, n=3):
    for _ in range(n):
        s.k.tap('SYN')


def onsets(fr, t):
    out = []
    for i, f in enumerate(fr):
        on = U16(f, 0x22)
        vs = [v for v in range(16) if on >> v & 1 and U16(f, 0xA5A + 2 * v) == t]
        if vs:
            out.append((i, vs))
    return out


def notes_at(f, base, n):
    return [round(U16(f, 2 + 2 * (base + j)) / 256) for j in range(n)]


name_of = lambda s: bytes(s.k.h.r(s.sym['dg_name'], 16)).split(b'\0')[0].decode()
trigs_of = lambda s: s.k.h.u32(s.sym['DG'] + 4)
nn = lambda n: f'{G.NOTE_NAMES[n % 12]}{n // 12}'


def sequence(s, roots, ui, t=0, length=127, locks=None, tail=400, each=None):
    """trigs on steps 1, 9, 17, ... with the notes `roots`; -> frames."""
    for st in range(128):
        s.k.call(A(0x40054690), [s.ctx0 + 132 * t, st, 1, 0])
    for i, n in enumerate(roots):
        s.trig(8 * i, note=n, length=length, t=t)
    for st, lk in (locks or {}).items():
        s.lock(st, t=t, **lk)
    return s.play(len(roots) * GAP + tail, bpm=120, each=each)


# ---------------------------------------------------------------- A, B
s = Session(img, tag='r5_ab', solo=False, reserve=0)
k = s.k
pad0 = bytes(k.h.r(s.store(), 337))
k.slot(0, 54, 3 << 8)                                    # VCNT 5 on the demo's own track 1: nothing else touched
redraw(s)
have, base = voices_of(s, 0)
got = {f: k.slot(0, sl) >> 8 for f, sl in zip(FIELDS, SLOTS) if f != 'vcnt'}
want = {f: slot_code(f, v) for f, v in Ui().items() if f != 'vcnt'}
check(have == 5 and base == 0, f'A: VCNT 5 on a track never set up: VOICES raised to {have} (voices {base}..{base + have - 1})')
check(not any(pad0) and bytes(k.h.r(s.store(), 4)) == b'DGK2',
      'A: the kit record\'s spare bytes were all zero before, and hold the store ("DGK2") after the first setting')
check(got == want, 'A: every parameter has its default'
                   + ('' if got == want else f' DIFFER {[(f, got[f], want[f]) for f in got if got[f] != want[f]]}'))
ui = Ui(voic=64, glid=3, drft=0, vib=0)                           # GLID 1/4 bar: each glide is done before the next key
s.set_sound(ui)
ROOTS = list(range(60, 72))
names = []
fr = sequence(s, ROOTS, ui, each=lambda i: names.append(name_of(s)))
mine = set(range(base, base + have))
ons = onsets(fr, 0)
outside = [(b, vs) for b, vs in ons if any(v not in mine for v in vs)]
check(not outside, f'B: no note-on of track 1 outside its DigiGlide voices, the other tracks playing' + (f' {outside[:3]}' if outside else ''))
others = sorted({U16(f, 0xA5A + 2 * v) + 1 for f in fr for v in range(16) if U16(f, 0x22) >> v & 1} - {1})
stolen = [i for i, f in enumerate(fr) for v in mine if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) != 0]
check(len(others) >= 3 and not stolen, f'B: tracks {others} played meanwhile, never on a DigiGlide voice')
check(trigs_of(s) == 12 and len(ons) == 1, f'B: {trigs_of(s)} chord events for 12 keys; only the first attacks (attack blocks {[b for b, _ in ons]})')
b0 = ons[0][0]
mp, _, _ = model({GAP * i: [('trig', 8 * i, ui, n)] for i, n in enumerate(ROOTS)}, 12 * GAP, 14400)
good, chords, shown = True, [], []
for i, n in enumerate(ROOTS):
    at = GAP * i + GAP - 10
    got = notes_at(fr[b0 + at], base, 5)
    wantn = [round(mp[at][j] / 100) for j in range(5)]
    good &= got == wantn
    chords.append((got[4], got[0], tuple(sorted({x % 12 for x in got[:4]}))))
    shown.append(names[min(len(names) - 1, b0 + at)])
    print(f'      key {nn(n):4s}: chord {[nn(x) for x in got[:4]]} bass {nn(got[4])}  shows "{shown[-1]}"' + ('' if got == wantn else f'  MODEL {wantn}'))
check(good, 'B: every voice is on the M1 model\'s note for the key pressed')
tri = lambda n: tuple(sorted({(n + x) % 12 for x in (0, 4, 7)}))
check(all(c[2] == tri(n) for c, n in zip(chords, ROOTS)) and len({c[2] for c in chords}) == 12,
      'B: twelve keys give twelve different chords, each the major triad of its key')
check(all(c[0] == n - 12 and c[1] == n for c, n in zip(chords, ROOTS)),
      'B: the bass voice is the key an octave down, the chord\'s lowest voice the key itself')
check(shown == [G.NOTE_NAMES[n % 12].upper() + ' MAJ' for n in ROOTS], f'B: the name shown is the chord ({shown[0]} .. {shown[-1]})')
w = [[U16(f, 2 + 2 * (base + j)) * 100 / 256 for j in range(5)] for f in fr[b0 + 2:b0 + 12 * GAP]]
step = max(abs(a - b) for x, y in zip(w, w[1:]) for a, b in zip(x, y))
check(0 < step < 50, f'B: the voices glide between chords (largest pitch step {step:.2f} cent a block; a jump would be 100 or more)')

# ---------------------------------------------------------------- C: KEY
WHITE = [60, 62, 64, 65, 67, 69, 71]
for ext, want_names in ((0, ['C MAJ', 'D MIN', 'E MIN', 'F MAJ', 'G MAJ', 'A MIN', 'B DIM']),
                        (2, ['C MAJ7', 'D MIN7', 'E MIN7', 'F MAJ7', 'G 7', 'A MIN7', 'B MIN7B5'])):
    s = Session(img, tag='r5_c', solo=True, reserve=0)
    ui = Ui(voic=64, key=1, ext=ext, glid=3, drft=0, vib=0)
    s.set_sound(ui); redraw(s)
    have, base = voices_of(s, 0)
    names = []
    fr = sequence(s, WHITE, ui, each=lambda i: names.append(name_of(s)), locks={48: dict(type=1)} if not ext else None)
    b0 = onsets(fr, 0)[0][0]
    lock6 = not ext                                      # the B step: TYPE p-locked MIN (first pass only)
    mp, _, _ = model({GAP * i: [('trig', 8 * i, ui.copy(type=1) if lock6 and i == 6 else ui, n,
                                 ('type',) if lock6 and i == 6 else ())] for i, n in enumerate(WHITE)}, 7 * GAP, 14400)
    shown, good = [], True
    for i, n in enumerate(WHITE):
        at = GAP * i + GAP - 10
        got = notes_at(fr[b0 + at], base, 5)
        pcs = G.chord_for(n, 1 if lock6 and i == 6 else 0, ext, 1, type_locked=lock6 and i == 6)[0]
        good &= got == [round(mp[at][j] / 100) for j in range(5)] and {x % 12 for x in got} <= pcs
        shown.append(names[min(len(names) - 1, b0 + at)])
    if ext:
        check(shown == want_names and good, f'C: KEY C major, EXT 7: the diatonic sevenths, every voice on the model\'s note {shown}')
    else:
        check(shown[:6] == want_names[:6] and good, f'C: KEY C major: each white key gets its diatonic chord, every voice on the model\'s note {shown[:6]}')
        check(shown[6] == 'B MIN', f'C: TYPE p-locked MIN on the B step beats KEY (shows "{shown[6]}", not B DIM)')


# ---------------------------------------------------------------- D, E: live keys
def live(image, tag, **kw):
    s = Session(image, tag=tag, solo=True, reserve=0)
    if image:
        s.set_sound(Ui(voic=64, glid=0, drft=0, vib=0, **kw)); redraw(s)
    else:
        s.k.select(1, track=0)
    s.k.tap('KEYB')                                      # keyboard mode: the trig keys play the active track
    return s


def press(s, group, mask, frames=400):
    h = s.k.h
    st = len(h.sent)
    h.pc = panelin.buttons(h.m, h.profile, group, mask); h.run(3_000_000)
    h.frames(frames)
    return [x for x, _ in h.sent[st:]]


stock, dg = live(None, 'r5_live_stock'), live(img, 'r5_live_dg')
have, base = voices_of(dg, 0)
a = press(stock, 3, 0x01); press(stock, 3, 0x00)
o = onsets(a, 0)
snote = round(U16(a[o[0][0]], 2 + 2 * o[0][1][0]) / 256)
b = press(dg, 3, 0x01); c = press(dg, 3, 0x00)
dn = notes_at(b[-1], base, 5)
check(dn[0] == snote and dn[4] == snote - 12 and dn[0] % 12 == snote % 12,
      f'D: the same key: stock plays {nn(snote)} ({snote}); DigiGlide\'s root is {nn(dn[0])} ({dn[0]}), its bass {nn(dn[4])}: '
      f'same pitch class and octave, no offset; shows "{name_of(dg)}"')
t0 = trigs_of(dg)
d = press(dg, 3, 0x15); press(dg, 3, 0x00)
s3 = press(stock, 3, 0x15); press(stock, 3, 0x00)
low = min(round(U16(f, 2 + 2 * v) / 256) for i, vs in onsets(s3, 0) for v in vs for f in [s3[i]])
dn3 = notes_at(d[-1], base, 5)
check(trigs_of(dg) - t0 == 1 and dn3[0] == low, f'D: three keys at once are one chord, on the lowest ({nn(low)}): root {nn(dn3[0])}, {trigs_of(dg) - t0} event')
allv = [v for part in (b, c, d) for _, vs in onsets(part, 0) for v in vs]
check(all(base <= v < base + have for v in allv), f'D: live keys: no note-on outside DigiGlide\'s voices {base}..{base + have - 1}')
offs = lambda fr_: [i for i, f in enumerate(fr_) if U16(f, 0x24) & (((1 << have) - 1) << base)]
check(offs(c), 'E: HOLD off: releasing the key releases the chord')

h1 = live(img, 'r5_hold', hold=1)
a = press(h1, 3, 0x01); b = press(h1, 3, 0x00)
check(onsets(a, 0) and not offs(a) and not offs(b), 'E: HOLD on: the key is released and the chord keeps sounding')
h1.k.slot(0, 93, 3 << 8)                                 # GLID 1/4 from here: the next key glides
c = press(h1, 3, 0x04); d = press(h1, 3, 0x00)
w0, w1 = notes_at(b[-1], base, 5), notes_at(d[-1], base, 5)
oc = onsets(c, 0)
wc = [[U16(f, 2 + 2 * (base + j)) * 100 / 256 for j in range(5)] for f in c]
jump = max(abs(x - y) for x, y in zip(wc[oc[0][0]], wc[oc[0][0] - 1])) if oc and oc[0][0] else 999
check(len(oc) == 1 and jump < 50 and not offs(c) and not offs(d) and w0 != w1,
      f'E: another key, pressed on its own: the held chord is struck again and glides to it '
      f'({[nn(x) for x in w0]} -> {[nn(x) for x in w1]}, {jump:.1f} cent at the attack)')
e = press(h1, 3, 0x04); press(h1, 3, 0x00)
check(offs(e) and not onsets(e, 0), 'E: the same key again: the chord releases')
g = press(h1, 3, 0x01); press(h1, 3, 0x00)
check(onsets(g, 0), 'E: the next key starts a fresh chord')
st = press(h1, 2, 0x10) + press(h1, 2, 0x00)
check(offs(st), 'E: [STOP] releases the held chord')
h2 = live(img, 'r5_legato', hold=1)                       # (its own session: late in a long one the emulator drops keys)
h2.k.slot(0, 93, 3 << 8)
l0 = press(h2, 3, 0x01, frames=900)                      # legato: the second key goes down while the first is held
lg = press(h2, 3, 0x05, frames=900); l2 = press(h2, 3, 0x00)
w0, w1 = notes_at(l0[-1], base, 5), notes_at(l2[-1], base, 5)
check(onsets(l0, 0) and not onsets(lg, 0) and not offs(lg) and w0 != w1,
      f'E: overlapping keys: the chord glides to the new key without a new attack ({[nn(x) for x in w0]} -> {[nn(x) for x in w1]})')
h2.k.slot(0, 84, 0)                                      # AMP SUS 0: the sound fades while held
dk = press(h2, 3, 0x10, frames=900); press(h2, 3, 0x00)
oc = onsets(dk, 0)
wc = [[U16(f, 2 + 2 * (base + j)) * 100 / 256 for j in range(5)] for f in dk]
jump = max(abs(x - y) for x, y in zip(wc[oc[0][0]], wc[oc[0][0] - 1])) if oc and oc[0][0] else 999
check(len(oc) == 1 and jump < 50 and not offs(dk),
      f'E: a sound that does not sustain (AMP SUS 0): another key strikes the held chord again and glides ({jump:.1f} cent at the attack)')
h4 = live(img, 'r5_fastatk', hold=1)                      # (its own session, as above)
h4.k.slot(0, 93, 3 << 8)
h4.k.slot(0, 81, 0)                                      # AMP ATK 0: not a pad
f0 = press(h4, 3, 0x01, frames=900); press(h4, 3, 0x00)
fk = press(h4, 3, 0x10, frames=900); press(h4, 3, 0x00)
oc = onsets(fk, 0)
wc = [[U16(f, 2 + 2 * (base + j)) * 100 / 256 for j in range(5)] for f in fk]
jump = max(abs(x - y) for x, y in zip(wc[oc[0][0]], wc[oc[0][0] - 1])) if oc and oc[0][0] else 999
check(onsets(f0, 0) and len(oc) == 1 and jump < 50 and not offs(fk),
      f'E: a fast attack (AMP ATK 0), sustaining: another key strikes the held chord again and glides ({jump:.1f} cent at the attack)')
h3 = live(img, 'r5_preset', hold=1)                       # (its own session, as above)
p0 = press(h3, 3, 0x02, frames=900); press(h3, 3, 0x00)  # a held chord (HOLD on) to load the preset under
snd = h3.k.sound(0)                                      # a preset is loaded: the sound's name changes
h3.k.h.w(snd + 4, b'OTHER PRESET'.ljust(16, b'\0'))
pl = press(h3, 3, 0x00, frames=100)
nk = press(h3, 3, 0x10, frames=900) + press(h3, 3, 0x00)  # (the emulator can deliver the key late)
check(onsets(p0, 0) and offs(pl) and onsets(nk, 0), 'E: a preset is loaded under a held chord: the chord is dropped and the next key attacks')

# G: VOIC and POS turned under a held chord
g1 = live(img, 'r5_voic', hold=1)
press(g1, 3, 0x01); a = press(g1, 3, 0x00)
g1.k.slot(0, 93, 3 << 8)
v0 = notes_at(a[-1], base, 5)
g1.k.slot(0, 50, 1 << 8)                                 # TYPE MAJ -> MIN under the held chord
d_ = g1.k.h.frames(1400) or [x for x, _ in g1.k.h.sent[-1400:]]
v3 = notes_at(d_[-1], base, 5)
check(not onsets(d_, 0) and name_of(g1).endswith('MIN') and v3 != v0 and
      all((x - v0[4]) % 12 in (0, 3, 7) for x in v3[:4]),      # (VOIC is wide here: the third may sit in any voice or none)
      f'G: TYPE turned to MIN under a held chord: it glides to the minor chord at once, no attack (shows "{name_of(g1)}")')

v0 = v3
g1.k.slot(0, 53, 120 << 8)
b = g1.k.h.frames(1400) or [x for x, _ in g1.k.h.sent[-1400:]]
v1 = notes_at(b[-1], base, 5)
g1.k.slot(0, 55, 100 << 8)
c = g1.k.h.frames(1400) or [x for x, _ in g1.k.h.sent[-1400:]]
v2 = notes_at(c[-1], base, 5)
check(not onsets(b, 0) and v1[3] - v1[0] > v0[3] - v0[0] + 6 and v1[4] == v0[4],
      f'G: VOIC 64 -> 120 under a held chord: the voices glide apart, no attack ({[nn(x) for x in v0[:4]]} -> {[nn(x) for x in v1[:4]]})')
check(not onsets(c, 0) and min(v2[:4]) > min(v1[:4]) + 6 and v2[4] == v0[4],
      f'G: POS +36: the chord moves up through its inversions, the bass stays ({[nn(x) for x in v1[:4]]} -> {[nn(x) for x in v2[:4]]})')

# H: BASS
for bass, text in ((0, 'OFF'), (6, 'SOLO')):
    s = live(img, f'r5_bass{bass}', bass=bass)
    a = press(s, 3, 0x01)
    vs = sorted({v for _, x in onsets(a, 0) for v in x})
    ns = [round(U16(a[-1], 2 + 2 * v) / 256) for v in vs]
    if bass == 0:
        check(len(vs) == 5 and min(ns) == snote, f'H: BASS OFF: five chord voices, none under the key ({[nn(x) for x in sorted(ns)]})')
    else:
        check(len(vs) == 1 and ns == [snote], f'H: BASS SOLO: one voice, the root ({[nn(x) for x in ns]})')


# ---------------------------------------------------------------- F: short notes, GLID 0
def short_notes(rel, glid):
    s = Session(img, tag=f'r5_tail{rel}_{glid}', solo=True, reserve=0)
    ui = Ui(voic=64, glid=glid, drft=0, vib=0)
    s.set_sound(ui)
    s.k.slot(0, 85, rel << 8)                            # AMP REL
    redraw(s)
    have, base = voices_of(s, 0)
    fr = sequence(s, [60, 65, 67, 62, 60], ui, length=8 if glid else 127)
    ons = onsets(fr, 0)
    w = [[U16(f, 2 + 2 * (base + j)) * 100 / 256 for j in range(5)] for f in fr]
    jumps = [max(abs(a - b) for a, b in zip(w[b], w[b - 1])) for b, _ in ons[1:]]
    return ons, jumps, s.tails()


ons, jumps, tails = short_notes(100, 2)
check(len(ons) == 5 and tails == 0b01111 and max(jumps) < 50,
      f'F: short notes, long release: every chord attacks again and glides from the ringing one (pitch change at an attack {max(jumps):.1f} cent)')
ons, jumps, tails = short_notes(0, 2)
check(len(ons) == 5 and tails == 0 and max(jumps) >= 100, f'F: short notes, no release: each chord starts fresh (up to {max(jumps):.0f} cent at an attack)')
ons, jumps, tails = short_notes(100, 0)
check(len(ons) == 5 and tails == 0 and max(jumps) >= 100, f'F: GLID 0, notes held: every chord retriggers and jumps ({len(ons)} attacks, up to {max(jumps):.0f} cent)')

# ---------------------------------------------------------------- I: off = stock
runs = []
for im in (None, img):
    s = Session(im, tag='r5_off', solo=False, reserve=0)
    runs.append([bytes(f[:2688]) for f in s.play(3000, bpm=120)][:3000])
diff = sum(1 for x, y in zip(*runs) if x != y)
check(diff == 0, f'I: VCNT OFF on every track (the demo project): 3000 frames, {diff} differ from stock OS')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
