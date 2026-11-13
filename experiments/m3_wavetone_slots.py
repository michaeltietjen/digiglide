"""DigiGlide M3: does the WAVETONE DSP engine ignore sound slots 50..64 (where M4 stores DigiGlide's parameters)?

Renders in the SHARC emulator, twice each: a WAVETONE voice (stock defaults, plus a second case with filter / LFO-ish
movement: a pitch glide in the note word and a non-default wave) with slots 50..64 left as the template has them, and
with slots 50..64 filled with random raw values (0x0000..0x7F00). Pass: the audio is bit-identical.
    python3 m3_wavetone_slots.py
"""
import os, random, sys
SK = os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts')
sys.path.insert(0, SK)
import numpy as np
import dn2paths as P
import dn2frame as D, dn2synth as S

SLOTS = range(50, 65)
rng = random.Random(50)
FILL = {s: rng.randrange(0, 0x7F01) for s in SLOTS}
sec7, snap = P.snap('stock')


def frames(case, fill):
    snd = S.Sound('WAVETONE')
    if case == 'moving':
        snd.set('WAV1', 40).set('WAV2', 90).set('FREQ', 70).set('RESO', 40)
    song = S.Song().assign(0, snd).track(0, 0).note(2, 0, 60, 110, length=900)
    out = []
    for k, f in enumerate(song.frames(1400)):
        f = bytearray(D.swap16(f))
        if fill:
            for s, v in fill.items():
                o = 0xda + S.slot_off(s)
                f[o:o + 2] = v.to_bytes(2, 'big')
        if case == 'moving' and k > 300:            # a glide in the note word, as DigiGlide sends
            w = int((60 + min(1.0, (k - 300) / 400) * 7) * 256)
            f[2:4] = w.to_bytes(2, 'big')
        out.append(D.swap16(bytes(f)))
    return out


ok = True
for case in ('default', 'moving'):
    a = D.render(D.Frame(D.image_from_sec7(sec7), snap), frames(case, None))
    b = D.render(D.Frame(D.image_from_sec7(sec7), snap), frames(case, FILL))
    same = np.array_equal(np.asarray(a[0]), np.asarray(b[0])) and np.array_equal(np.asarray(a[1]), np.asarray(b[1]))
    rms = float(np.sqrt(np.mean(np.asarray(a[0], float) ** 2)))
    print(f'{case:8s}: {len(a[0])} samples, rms {rms:.4f}, slots 50..64 filled -> bit-identical: {same}')
    ok &= same and rms > 1e-4
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
