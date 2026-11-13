"""DigiGlide M5 listening aid: a fast glide (PATH Bounce, GLID 1/16, i -> VI in C minor at 120 BPM), the worst case of
the per-block pitch steps (about 29 cents per block). The frames carry the M1 model's per-block pitch exactly as the
firmware sends it (note word = pitch rounded to 1/256 semitone, once per 32-sample block; the DSP steps to it): what
the unit will play, so the stepping can be judged by ear. Also the same change at GLID 1/2 (under 4 cents a block).
    ~/dn2-workspace/repos/digikit/.venv/bin/python render_fast_glide.py"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/model'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
import digiglide as G
import dn2paths as P, dn2frame as D, dn2synth as S
OUT = os.path.expanduser('~/glide/renders/M5')
BAR = 3000


def pad():
    snd = S.Sound('WAVETONE')
    for n, v in (('SYN.WAV1', 0), ('SYN.WAV2', 0), ('SYN.LEV1', 100), ('SYN.LEV2', 100), ('SYN.DRIF', 32),
                 ('FILTER.FREQ', 84), ('FILTER.RESO', 10), ('AMP.ATK', 60), ('AMP.HOLD', 127), ('AMP.DEC', 127),
                 ('AMP.SUS', 127), ('AMP.REL', 90), ('FX.REV', 50), ('FX.CHR', 40)):
        snd.set(n, v)
    snd.set('SYN.TUN2', 0x4008)
    return snd


sec7, snap = P.snap('stock')
import sys as _s
OCT = int(_s.argv[1]) if len(_s.argv) > 1 else 0
SETS = ((('fast_bounce_1-16', 1, 4), ('bounce_1-2', 4, 4)) if not OCT else
        (('fast_bounce_1-16_up12', 1, 4), ('bounce_1-2_up12', 4, 4), ('smooth_1bar_up12', 5, 0)))
for tag, glid, path in SETS:
    p0 = G.Params(key=0, scl=1, chrd=1, deg=0, glid=glid, path=path, drft=0, vib=0)
    ev = {0: [('trig', 0, p0)], BAR: [('trig', 16, p0.copy(deg=5))], 3 * BAR: [('off',)]}
    pitch = np.array(G.run(ev, 4 * BAR, 120.0)[0])[:, :5]
    song = S.Song(bpm=120)
    for v in range(5):
        song.assign(v, pad())
        song.note(2, v, 60, 100)
    fr = song.frames(4 * BAR + 2)
    out = []
    for b, f in enumerate(fr):
        f = bytearray(D.swap16(f))
        m = pitch[max(0, b - 2)] if b >= 2 else pitch[0]
        for v in range(5):
            f[2 + 2 * v:4 + 2 * v] = int(round((m[v] + 1200 * OCT) * 256 / 100)).to_bytes(2, 'big')
        if b == 3 * BAR + 2:
            f[0x24:0x26] = (0x1F).to_bytes(2, 'big'); f[0x28:0x2A] = (0x1F).to_bytes(2, 'big')
        out.append(D.swap16(bytes(f)))
    L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), out)
    L, R = np.array(L), np.array(R)
    g = 10 ** (-1 / 20) / max(np.abs(L).max(), np.abs(R).max())
    D.write_wav(os.path.join(OUT, tag + '.wav'), L * g, R * g)
    steps = np.abs(np.diff(pitch[BAR:BAR + 600], axis=0)).max()
    print(f'{tag}: largest step {steps:.1f} cents per block -> {tag}.wav')
