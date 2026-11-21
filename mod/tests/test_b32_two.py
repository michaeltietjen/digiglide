"""Image 32: two DigiGlide tracks sound at once (owner, image 31: a drone on one track and glides on another; through
image 31 the second track played stock's single notes while the first one's chord sounded).
  A  the drone track: HOLD on, one long trig. The glide track: three short trigs on other steps. Both play chords,
     each on its own reserved voices; the drone is never released or retuned by the glide track's chords.
  B  the glide track's chords are the ones it plays alone (the drone track switched off): same notes, same voices.
  C  both tracks' chord names are shown; a third DigiGlide track that plays while both sound gets one stock note.
  D  played a second time after the stop: both play their chords again.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b32_two.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, U16, Ui, word
from osver import A

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


DRONE = Ui(vcnt=4, hold=1, glid=0, drft=0, vib=0, voic=64)
GLIDE = Ui(vcnt=3, hold=0, glid=0, drft=0, vib=0, voic=64, bass=0)
NOTES = {4: 60, 6: 62, 8: 65}                      # (early steps: the harness starts the bar up to a beat late)
TA, TB, TC = 1, 2, 3                               # (the harness does not play track 1's trigs in this setup,
                                                  # image 31 neither: the drone is on track 2, the glides on 3)


def session(tag, drone=True, third=False):
    s = Session(img, tag=tag, solo=True, reserve=4)
    s.set_sound(DRONE, t=TA, on=drone)
    s.set_sound(GLIDE, t=TB)
    if third:
        s.set_sound(GLIDE, t=TC)
    cfg = s.k.call(A(0x40030AF8), [s.k.call(A(0x4003E41A), [s.app])])
    for t, n in ((0, 0), (TA, 4), (TB, 3)) + (((TC, 3),) if third else ()):     # VOICES, as the owner sets them in the VOICE menu
        s.k.call(A(0x40029094), [cfg, t, n])
    s.k.h.frames(600)
    s.trig(2, note=48, length=127, t=TA)                # (a trig on step 1 is not played by the harness)
    for st, n in NOTES.items():
        s.trig(st, note=n, length=2, t=TB)
    if third:
        s.trig(7, note=72, length=2, t=TC)
    return s


def events(fr, lo, n):
    """note-on frames on voices lo..lo+n-1 -> [(frame, [voices], [notes at +3 frames])]"""
    m = ((1 << n) - 1) << lo
    out = []
    for i, f in enumerate(fr):
        b = U16(f, 0x22) & m
        if b:
            g = fr[min(i + 3, len(fr) - 1)]
            vs = [v for v in range(16) if b >> v & 1]
            out.append((i, vs, [round(word(g, v) / 256) for v in vs]))
    return out


s = session('b32_two')
(n0, b0), (n1, b1) = voices_of(s, TA), voices_of(s, TB)
check((n0, b0, n1, b1) == (4, 0, 3, 4), f'A voices reserved: track 2 has {n0} from {b0}, track 3 has {n1} from {b1}')
fr = s.play(2900, bpm=120)                      # one bar is 3,000 blocks: the pattern once
e0, e1 = events(fr, b0, n0), events(fr, b1, n1)
m0, m1 = ((1 << n0) - 1) << b0, ((1 << n1) - 1) << b1
check(len(e0) == 1 and len(e0[0][1]) == 4 and len(set(e0[0][2])) >= 3,
      f'A the drone: one chord on 4 voices {e0[0][1:] if e0 else e0}')
check(len(e1) == 3 and all(len(vs) == 3 and len(set(ns)) == 3 for _, vs, ns in e1),
      f'A the glide track while the drone sounds: three chords of three notes on its own voices {[x[1:] for x in e1]}')
other = [(i, hex(U16(f, 0x22))) for i, f in enumerate(fr) if U16(f, 0x22) & ~(m0 | m1)]
check(not other, f'A no note-on outside the two tracks\' voices {other[:3]}')
i0 = e0[0][0] if e0 else 0
offs0 = [i for i, f in enumerate(fr) if i > i0 and U16(f, 0x24) & m0]
drone_notes = {tuple(round(word(f, v) / 256) for v in range(b0, b0 + n0)) for f in fr[i0 + 3:]}
check(not offs0 and len(drone_notes) == 1,
      f'A the drone holds through the glide track\'s chords: no note-off on its voices ({offs0[:3]}), its notes stay {sorted(drone_notes)}')
offs1 = [i for i, f in enumerate(fr) if U16(f, 0x24) & m1]
check(len(offs1) >= 3, f'A the glide track\'s chords end with their trigs (HOLD off): {len(offs1)} note-off frames')
names = (s.chord_name(TA), s.chord_name(TB))
check(names[0] != '', f'C the drone\'s chord name is shown on its track: "{names[0]}"')

alone = session('b32_alone', drone=False)
fa = alone.play(2900, bpm=120)
a1 = events(fa, b1, n1)
check([x[1:] for x in a1] == [x[1:] for x in e1] and len(a1) == 3,
      f'B the glide track alone plays the same chords on the same voices {[x[1:] for x in a1]}')
check(not events(fa, b0, n0) or all(len(vs) == 1 for _, vs, _ in events(fa, b0, n0)),
      'B (the drone track switched off there: no chord on its voices)')

t3 = session('b32_three', third=True)
n2, b2 = voices_of(t3, TC)
f3 = t3.play(2900, bpm=120)
e2 = events(f3, b2, max(n2, 1))
check(len(events(f3, b0, n0)) == 1 and len(events(f3, b1, n1)) == 3,
      f'C with a third DigiGlide track: the drone and the glide track play as before ({len(events(f3, b0, n0))}, {len(events(f3, b1, n1))} chords)')
print(f'  info the third track (voices {n2} from {b2}) note-ons: {[x[1:] for x in e2]}', flush=True)
check(e2 and all(len(vs) <= len(e2[-1][1]) for _, vs, _ in e2),
      'C the third track sounds (a stock note while both slots hold other tracks, a chord when one is free)')

# D: the drone is let go, track 2 goes on; then track 1 again
h = s.k.h
h.frames(600)                                   # (play ends with [STOP]: the held drone is let go)
fr2 = s.play(2900, bpm=120)
d0, d1 = events(fr2, b0, n0), events(fr2, b1, n1)
check(len(d1) == 3 and all(len(vs) == 3 for _, vs, _ in d1) and len(d0) == 1 and len(d0[0][1]) == 4,
      f'D played again after the stop: the drone strikes once on 4 voices, the glide track plays three chords ({len(d0)}, {len(d1)})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
