"""DigiGlide on each machine, down to the sound (rev 6): a DigiGlide track with a WAVETONE, an FM TONE and an FM DRUM
sound (the demo project's tracks 1, 2 and 15; it has no SWARMER track) plays three short trigs, once with HOLD off and
once with HOLD on. The frames are checked and then rendered in the SHARC emulator.
  HOLD off: every trig is a 5-voice chord on the track's reserved voices; each chord is released (note-offs, no voice
            left gated); the render sounds, is finite and does not clip, and the level falls after the last release.
  HOLD on:  the chord is not released between trigs; the later chords glide (one attack block, the pitches move);
            the render sounds, is finite and does not clip. The level over time is printed (a held drum patch can
            keep rising: it is reported, not judged).
  Both:     the track's sound is byte for byte as before.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_machines_render.py [DIGIGLIDE.syx] [TRACK ...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, latest, U16, Ui
import dn2paths as P, dn2frame as D

img = sys.argv[1] if len(sys.argv) > 1 else latest()
tracks = [int(x) for x in sys.argv[2:]] or [0, 1, 14]
print('image', os.path.basename(img))
ok = True
NAMES = {0: 'FM TONE', 1: 'WAVETONE', 2: 'FM DRUM', 3: 'SWARMER'}
TRIGS = ((2, 64), (10, 59), (18, 55))
sec7, snap = P.snap('stock')


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def levels(frames):
    L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), [D.swap16(bytes(f)) for f in frames])
    x = (np.asarray(L, float) + np.asarray(R, float)) / 2
    w = len(x) // 40
    return [float(np.sqrt(np.mean(x[i:i + w] ** 2))) for i in range(0, len(x) - w + 1, w)], float(np.max(np.abs(x))), bool(np.all(np.isfinite(x)))


for t in tracks:
    for hold in (0, 1):
        s = Session(img, tag=f'mr_{t}_{hold}', solo=True, reserve=0)
        m = s.k.mach(t)
        nm = f'track {t + 1} ({NAMES.get(m, m)}), HOLD {"on" if hold else "off"}'
        s.k.h.frames(3200)
        before = bytes(s.k.h.r(s.k.sound(t), 1163))
        s.set_sound(Ui(vcnt=5, voic=64, glid=3, drft=0, vib=0, hold=hold), t=t, mach=None, atk=None)
        for _ in range(4):
            s.k.tap('SYN'); s.k.h.frames(120)
        d = s.k.h.u32(s.sym['DG'] + 80)
        v = [s.k.h.r(d + 5 * i + 1, 1)[0] for i in range(16)]
        have, base = v[t], sum(v[:t])
        mine = ((1 << have) - 1) << base
        for step, n in TRIGS:
            s.trig(step, note=n, length=6, t=t)
        fr = s.play(6000, bpm=120)                      # the trigs fall near blocks 1200, 2700, 4200
        ons = [(i, U16(f, 0x22)) for i, f in enumerate(fr) if U16(f, 0x22)]
        offs = [(i, U16(f, 0x24)) for i, f in enumerate(fr) if U16(f, 0x24) & mine]
        outside = [i for i, b in ons if b & ~mine]
        taken = s.k.h.u32(s.sym['DG'] + 96)
        moves = sum(1 for x, y in zip(fr, fr[1:]) if any(U16(x, 2 + 2 * (base + j)) != U16(y, 2 + 2 * (base + j)) for j in range(have)))
        check(have == 5 and taken == 3 and ons and not outside and bin(ons[0][1]).count('1') == 5,
              f'{nm}: 3 trigs taken as chords, 5 voices from voice {base}, no note-on outside them')
        if hold:
            # (a sound with a fast attack is struck again by every trig, by design: AMP ATK under 32; a pad is not)
            check(not offs and moves > 1000,
                  f'{nm}: the chord holds (no note-off) and glides to the next chords: pitches move in {moves} blocks, {len(ons)} attack block(s)')
        else:
            gated = 0
            for f in fr:
                gated = (gated | U16(f, 0x22)) & ~U16(f, 0x24)
            check(len(offs) >= 3 and not gated & mine,
                  f'{nm}: each chord is released ({len(offs)} note-off blocks), no voice left gated at the end')
        check(bytes(s.k.h.r(s.k.sound(t), 1163)) == before, f'{nm}: the sound is byte for byte as before')
        a, pk, fin = levels(fr)
        print('      rms per 100 ms (4 s):', ' '.join(f'{x:.4f}' for x in a), '| peak', round(pk, 4), flush=True)
        check(fin and 0.001 < max(a) and pk < 1.0, f'{nm}: the render sounds (largest rms {max(a):.4f}), is finite, peak {pk:.3f} below full scale')
        if not hold:
            check(a[-1] < 0.6 * max(a), f'{nm}: after the last release the level falls ({max(a):.4f} -> {a[-1]:.4f})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
