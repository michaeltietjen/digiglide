"""FM TONE in the SHARC emulator from explicit sound records (stock parameter table, dn2synth). render(knobs, notes)
gives stereo audio; partials() lists the strongest spectral lines as ratios of the note's frequency."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
import dn2paths as P, dn2frame as D, dn2synth as S

FS = 48000
_SEC7, _SNAP = P.snap('stock')
BASE = {'AMP.ATK': 0, 'AMP.HOLD': 127, 'AMP.SUS': 127, 'AMP.REL': 20, 'FILTER.FREQ': 127}


def sound(knobs):
    snd = S.Sound('FMTONE')
    for k, v in {**BASE, **knobs}.items():
        if isinstance(v, tuple):                        # ('raw', n): the stored word itself
            snd.slots[snd.names[k.upper()]] = v[1]
        else:
            snd.set(k, v)                               # a knob value 0..127 (stored << 8)
    return snd


def render(knobs, notes=(60,), blocks=1500, off_at=None, mod=None):
    """mod(block, voice) -> {slot name: raw value}: values written into the voice records of that block."""
    snd = sound(knobs)
    song = S.Song(bpm=120)
    for i, n in enumerate(notes):
        song.assign(i, snd).track(i, 0).note(2, i, n, 100, length=(off_at - 2) if off_at else None)
    out = []
    for b, f in enumerate(song.frames(blocks)):
        if mod:
            f = bytearray(D.swap16(f))
            for i in range(len(notes)):
                for name, raw in mod(b, i).items():
                    o = 0xda + 146 * i + S.slot_off(snd.names[name.upper()])
                    f[o:o + 2] = int(raw).to_bytes(2, 'big')
            f = D.swap16(bytes(f))
        out.append(f)
    L, R, _ = D.render(D.Frame(D.image_from_sec7(_SEC7), _SNAP), out)
    return np.array(L, float), np.array(R, float)


def partials(x, f0, start=16000, n=32768, top=10, floor_db=-50):
    seg = x[start:start + n] * np.hanning(n)
    s = np.abs(np.fft.rfft(seg))
    s /= s.max() + 1e-12
    out = []
    for i in np.argsort(-s):
        if 20 * np.log10(s[i] + 1e-12) < floor_db or len(out) >= top:
            break
        if 0 < i < len(s) - 1 and s[i] >= s[i - 1] and s[i] >= s[i + 1]:
            out.append((round(i * FS / n / f0, 2), round(20 * np.log10(s[i]), 1)))
    return sorted(out)
