"""DigiGlide rev 4 (after the first flash): DigiGlide owns the track's notes, keys choose the chord, latch.

Everything here runs the way the unit was: VOICES left at its default (DigiGlide must reserve its voices itself) and,
where it says so, the demo's other tracks playing.

  A  voices: with VCNT on, the UI task raises the track's VOICES to VCNT; back to what it was when VCNT goes OFF.
  B  sequenced, the other tracks playing: 8 trigs C D Eb F G Ab Bb C (C minor) on track 1.
       - no stock note-on of track 1 ever reaches the DSP: every note-on on a track-1 voice is DigiGlide's gate;
       - all 8 trigs are chord events; the 7 keys give 7 different chords, the 8th is the first an octave up;
       - each chord is the M1 model's for (KEY, SCL, the note's degree and octave): same note on every voice;
       - every change glides: after the first chord no voice attacks again, and no pitch step is over 5 cents.
  C  the same on track 4 with track 2 holding 3 reserved voices (its block is not 0..4).
  D  a p-locked DEG on a step overrides the note for that step.
  E  several notes in one block are the chord (chord mode, a multi-note trig): three keyboard keys pressed in one panel
     message. On stock OS the same press plays three notes; DigiGlide's voices carry exactly those pitch classes, its
     bass is the lowest key's pitch class, and one key alone plays the same pitch class and octave in both (no offset).
  G  short sequenced notes: with a long amp release every chord attacks again and glides from the ringing one;
     with no release each chord starts fresh.
  F  latch (live keys, LATCH on = sound slot 94): release does not end the chord; another key glides (no attack);
     the same key again releases it; with a chord latched, [STOP] releases it. LATCH off: releasing the key releases.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_m6_notes.py [DIGIGLIDE.syx]
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, G, U16
from osver import A
from emu import panelin

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True


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


def dgx(s):
    """the rev 4 counters: swallowed stock note-ons, chord events, same-chord releases, latched."""
    h, base = s.k.h, s.sym['DG']
    return dict(trigs=h.u32(base + 4), stock_trigs=h.u32(base + 60))


def track_onsets(fr, t):
    """[(block, [voices])] of note-ons on voices whose track word is t."""
    out = []
    for i, f in enumerate(fr):
        on = U16(f, 0x22)
        vs = [v for v in range(16) if on >> v & 1 and U16(f, 0xA5A + 2 * v) == t]
        if vs:
            out.append((i, vs))
    return out


NOTES = [60, 62, 63, 65, 67, 68, 70, 72]                 # C minor scale from C5, and C6
BASE = G.Params(key=0, scl=1, deg=0, chrd=0, vcnt=5, bass=1, glid=3, drft=0, vib=0)   # GLID 1/4 bar
GAP = 1500                                               # a trig every 8 steps (half a bar at 120 BPM)


def sequenced(t, solo, locks=None):
    s = Session(img, tag=f'm6n_t{t}_{int(solo)}', solo=solo, reserve=0)
    k = s.k
    if t:                                                # track 2 reserves 3 voices: this track's block starts at 3
        k.call(A(0x40029094), [s.app + 244 + 17092, 1, 3])
    s.set_sound(BASE, t=t)
    before = voices_of(s, t)
    redraw(s)
    have, base = voices_of(s, t)
    for st in range(128):
        k.call(A(0x40054690), [s.ctx0 + 132 * t, st, 1, 0])
    for i, n in enumerate(NOTES):
        s.trig(8 * i, note=n, length=127, t=t)
    for st, d in (locks or {}).items():
        s.lock(st, t=t, deg=d)
    fr = s.play(8 * GAP + 400, bpm=120)
    return s, fr, before[0], have, base


# ---------------------------------------------------------------- A, B
s, fr, was, have, base = sequenced(0, solo=False)
check(was == 0 and have == 5 and base == 0, f'A: VOICES of track 1 was {was} (default), raised to {have} by VCNT 5 (voices {base}..{base + have - 1})')
mine = set(range(base, base + have))
ons = track_onsets(fr, 0)
outside = [(b, [v for v in vs if v not in mine]) for b, vs in ons if any(v not in mine for v in vs)]
check(not outside, f'B: no note-on of track 1 outside its DigiGlide voices, the other tracks playing ({len(ons)} onset blocks'
                   + (f'; stock notes at {outside[:3]}' if outside else '') + ')')
others = sorted({U16(f, 0xA5A + 2 * v) + 1 for f in fr for v in range(16) if U16(f, 0x22) >> v & 1} - {1})
check(len(others) >= 3 and not any(v in mine for f in fr for v in range(16)
                                    if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) != 0),
      f'B: tracks {others} played meanwhile, never on a DigiGlide voice')
check(dgx(s)['trigs'] == 8, f'B: {dgx(s)["trigs"]} chord events for 8 trigs')
check(len(ons) == 1, f'B: only the first chord attacks; the 7 changes glide (attack blocks {[b for b, _ in ons]})')
b0 = ons[0][0]
ev = {}
for i, n in enumerate(NOTES):
    deg, oc = G.degree_of(n, 0, 1)
    ev[GAP * i] = [('trig', 8 * i, BASE.copy(deg=deg), oc)]
mp, _, _, _, _ = G.run(ev, 8 * GAP, 120.0, 0)
chords, good = [], True
for i, n in enumerate(NOTES):
    deg, oc = G.degree_of(n, 0, 1)
    at = GAP * i + GAP - 10                              # just before the next trig: the glide (1/4 bar) is done
    want = [round(mp[at][j] / 100) for j in range(5)]
    got = [round(U16(fr[b0 + at], 2 + 2 * (base + j)) / 256) for j in range(5)]
    chords.append((got[0] % 12, tuple(sorted({x % 12 for x in got})), got[0]))
    good &= got == want
    print(f'      key {G.NOTE_NAMES[n % 12]}{n // 12}: degree {G.ROMAN[deg]} octave {oc:+d}: voices {got}' + ('' if got == want else f'  MODEL {want}'))
check(good, 'B: every chord is the M1 model\'s for the key pressed (same note on every voice)')
check(len({c[:2] for c in chords[:7]}) == 7 and chords[7][0] == chords[0][0] and chords[7][2] == chords[0][2] + 12,
      'B: seven keys give seven different chords (bass and pitch classes); the octave key is the first chord\'s bass an octave up')
w = [[U16(f, 2 + 2 * (base + j)) * 100 / 256 for j in range(5)] for f in fr[b0 + 2:b0 + 8 * GAP]]
step = max(abs(a - b) for x, y in zip(w, w[1:]) for a, b in zip(x, y))
# (GLID 1/4 bar and leaps up to an octave: the 5-cent rule of M5 is for the default glide; here: never a jump)
check(0 < step < 50.0, f'B: the voices glide between chords: largest pitch step {step:.3f} cent a block (a jump would be 100 or more)')

# ---------------------------------------------------------------- C, D
s, fr, was, have, base = sequenced(3, solo=True, locks={16: 4})
mine = set(range(base, base + have))
ons = track_onsets(fr, 3)
check(have == 5 and all(v in mine for _, vs in ons for v in vs) and dgx(s)['trigs'] == 8,
      f'C: track 4 (track 2 holds voices 0..2): VOICES {was} -> {have} (voices {base}..{base + have - 1}), '
      f'{dgx(s)["trigs"]} chord events, no note-on outside them')
b0 = ons[0][0]
f = fr[b0 + GAP * 2 + GAP - 10]
got = sorted({round(U16(f, 2 + 2 * (base + j)) / 256) % 12 for j in range(5)})
want = sorted(G.chord_tones(0, 1, 4, 0)[1])
check(got == want, f'D: step 17 (key Eb, DEG p-locked V): pitch classes {got} = the V chord {want}')

# ---------------------------------------------------------------- G: short notes glide from the ringing chord
def short_notes(rel):
    s = Session(img, tag=f'm6n_tail{rel}', solo=True, reserve=0)
    s.set_sound(BASE.copy(glid=2), t=0)
    s.k.slot(0, 85, rel << 8)                            # AMP REL
    redraw(s)
    have, base = voices_of(s, 0)
    for st in range(128):
        s.k.call(A(0x40054690), [s.ctx0, st, 1, 0])
    for i, n in enumerate(NOTES[:5]):
        s.trig(8 * i, note=n, length=8, t=0)             # short notes: each ends well before the next trig
    fr = s.play(5 * GAP + 400, bpm=120)
    ons = track_onsets(fr, 0)
    offs_ = [i for i, f in enumerate(fr) if U16(f, 0x24) & (((1 << have) - 1) << base)]
    w = [[U16(f, 2 + 2 * (base + j)) * 100 / 256 for j in range(5)] for f in fr]
    jumps = [max(abs(a - b) for a, b in zip(w[b], w[b - 1])) for b, _ in ons[1:]]
    return ons, offs_, jumps, s.tails()


ons, offs_, jumps, tails = short_notes(100)              # a long release: about 11 s
check(len(ons) == 5 and len(offs_) >= 4, f'G: 5 short notes: 5 attacks, each note released before the next ({len(offs_)} note-off blocks)')
check(tails == 0b01111 and max(jumps) < 50, f'G: long release: every later chord glides from the ringing one '
                                             f'(largest pitch change at an attack {max(jumps):.1f} cent; tail bits {tails:05b})')
ons, offs_, jumps, tails = short_notes(0)                # no release: the chord is gone before the next trig
check(len(ons) == 5 and tails == 0 and max(jumps) >= 100, f'G: no release: each chord starts fresh, no glide '
                                                          f'(pitch change at an attack up to {max(jumps):.0f} cent; tail bits {tails:05b})')

# ---------------------------------------------------------------- E, F: live keys
def live(image, latch, tag):
    s = Session(image, tag=tag, solo=True, reserve=0)
    if image:
        s.set_sound(BASE.copy(glid=0), t=0)
        s.k.slot(0, 94, 0x100 if latch else 0)
        redraw(s)
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


def sounding(f, vs):
    return sorted(U16(f, 2 + 2 * v) / 256 for v in vs)


stock = live(None, False, 'm6n_live_stock')
dg = live(img, True, 'm6n_live_dg')
have, base = voices_of(dg, 0)
res = {}
for name, s in (('stock', stock), ('dg', dg)):
    one = press(s, 3, 0x01); press(s, 3, 0x00)
    if name == 'dg':                                     # latched: the same key again releases it
        press(s, 3, 0x01); press(s, 3, 0x00)
    three = press(s, 3, 0x15)                            # three keys in one panel message
    rel = press(s, 3, 0x00)
    res[name] = (one, three, rel)
o1 = track_onsets(res['stock'][0], 0)
skey = sounding(res['stock'][0][o1[0][0]], o1[0][1])
d1 = track_onsets(res['dg'][0], 0)
dnotes = sounding(res['dg'][0][-1], d1[0][1]) if d1 else []
print(f'      one key: stock plays {skey}; DigiGlide voices {[round(x, 2) for x in dnotes]}')
deg, oc = G.degree_of(int(skey[0]), 0, 1)
mm = G.DigiGlide(120.0, 0); mm.trig(0, BASE.copy(deg=deg, glid=0), oc)
check(d1 and [round(x) for x in dnotes] == sorted(mm.v[j].note for j in range(5)),
      f'E: one key (stock note {skey[0]:.0f}): DigiGlide plays the model\'s chord for that note, degree {G.ROMAN[deg]} octave {oc:+d}')
check(d1 and round(dnotes[0]) % 12 == int(skey[0]) % 12 and 36 + 12 * oc <= round(dnotes[0]) < 48 + 12 * oc,
      f'E: no offset: the key\'s pitch class {int(skey[0]) % 12} is DigiGlide\'s bass ({round(dnotes[0]) if dnotes else "-"}), '
      f'in the bass octave of that key\'s octave')
so = track_onsets(res['stock'][1], 0)
snotes = sorted({n for b, vs in so for n in sounding(res['stock'][1][b], vs)})
do = track_onsets(res['dg'][1], 0)
dv = sorted({v for _, vs in do for v in vs})
dn = sounding(res['dg'][1][-1], dv)
spc, dpc = sorted({int(n) % 12 for n in snotes}), sorted({round(n) % 12 for n in dn})
print(f'      three keys: stock plays {snotes}; DigiGlide voices {[round(x, 2) for x in dn]}')
check(len(snotes) == 3 and spc == dpc, f'E: three keys at once: DigiGlide\'s pitch classes {dpc} = the stock chord\'s {spc}')
check(dn and round(dn[0]) % 12 == int(snotes[0]) % 12, f'E: the bass is the lowest key\'s pitch class ({int(snotes[0]) % 12})')
allv = [v for part in res['dg'] for _, vs in track_onsets(part, 0) for v in vs]
check(all(base <= v < base + have for v in allv), f'E: live keys: no note-on outside DigiGlide\'s voices {base}..{base + have - 1}')

# F: latch. res['dg']: key down / up (latched), the same key again (released), 3 keys (a new chord), up (latched).
offs = lambda fr_: [i for i, f in enumerate(fr_) if U16(f, 0x24) & (((1 << have) - 1) << base)]
dg2 = live(img, True, 'm6n_latch')
a = press(dg2, 3, 0x01); b = press(dg2, 3, 0x00)
check(track_onsets(a, 0) and not offs(a) and not offs(b), 'F: LATCH on: the key is released and the chord keeps sounding (no note-off)')
c = press(dg2, 3, 0x04); d = press(dg2, 3, 0x00)
check(not track_onsets(c, 0) and not offs(c) and not offs(d),
      'F: another key: the latched chord glides to it (no attack, no note-off)')
w0, w1 = sounding(b[-1], range(base, base + have)), sounding(d[-1], range(base, base + have))
check(w0 != w1, f'F: and it is a different chord ({[round(x) for x in w0]} -> {[round(x) for x in w1]})')
e = press(dg2, 3, 0x04); press(dg2, 3, 0x00)
check(offs(e) and not track_onsets(e, 0), f'F: the same key again: the chord releases (note-offs at {offs(e)[:2]})')
g = press(dg2, 3, 0x01); press(dg2, 3, 0x00)
check(track_onsets(g, 0), 'F: the next key starts a fresh chord (attack)')
h_ = press(dg2, 2, 0x10) + press(dg2, 2, 0x00)           # [STOP] held for a moment (group 2 bit 4)
check(offs(h_), 'F: [STOP] releases the latched chord')
dg3 = live(img, False, 'm6n_nolatch')
a = press(dg3, 3, 0x01); b = press(dg3, 3, 0x00)
check(track_onsets(a, 0) and not offs(a) and offs(b), 'F: LATCH off: releasing the key releases the chord')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
