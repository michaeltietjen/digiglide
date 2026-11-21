"""Shared helpers for the sound pack: render WAVETONE voices in the SHARC emulator from explicit sound records (with a
filter type and per-voice pans), and measure spectra and envelopes."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
import dn2paths as P, dn2frame as D, dn2synth as S

FS = 48000
_SEC7, _SNAP = P.snap('stock')
NOISE = {'SYN.LEV1': 0, 'SYN.LEV2': 0, 'SYN.NLEV': 127, 'SYN.WDTH': 127, 'SYN.BASE': 0, 'AMP.ATK': 0, 'AMP.SUS': 127,
         'AMP.HOLD': 127, 'FX.REV': 0, 'FX.DEL': 0, 'FX.CHR': 0}
SINE = {'SYN.WAV1': 120, 'SYN.LEV1': 100, 'SYN.LEV2': 0, 'SYN.NLEV': 0, 'SYN.DRIF': 0, 'FILTER.FREQ': 127,
        'AMP.HOLD': 127, 'AMP.SUS': 127, 'FX.REV': 0, 'FX.DEL': 0, 'FX.CHR': 0}


def sound(slots):
    snd = S.Sound('WAVETONE')
    for k, v in slots.items():
        snd.set(k, v)
    return snd


def render(slots, ftype=0, notes=(60,), blocks=1500, off_at=None, fx=None, pans=None):
    snd = sound(slots)
    song = S.Song(bpm=120)
    for n_, v in (fx or {}).items():
        song.set_fx(n_, v)
    for i, n in enumerate(notes):
        s_ = S.Sound('WAVETONE'); s_.slots = dict(snd.slots)
        if pans:
            s_.set(89, int(0x4000 + pans[i] * 64 * 256))
        song.assign(i, s_).track(i, 0).note(2, i, n, 100, length=(off_at - 2) if off_at else None)
    out = []
    for f in song.frames(blocks):
        f = bytearray(D.swap16(f))
        for i in range(len(notes)):
            f[0xB4 + 2 * i:0xB6 + 2 * i] = ftype.to_bytes(2, 'big')
        out.append(D.swap16(bytes(f)))
    L, R, _ = D.render(D.Frame(D.image_from_sec7(_SEC7), _SNAP), out)
    return np.array(L), np.array(R)


def mono(x):
    return (x[0] + x[1]) / 2


def spectrum(x, start=FS // 4, n=65536):
    seg = x[start:start + n]
    w = np.hanning(len(seg))
    s = np.abs(np.fft.rfft(seg * w)) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / FS)
    return f, np.convolve(s, np.ones(32) / 32, 'same')


def cutoff(x, ref=(25, 50)):
    f, s = spectrum(x)
    db = 10 * np.log10(s + 1e-30)
    r = np.median(db[(f > ref[0]) & (f < ref[1])])
    above = np.where((f > ref[1]) & (db < r - 3))[0]
    return float(f[above[0]]) if above.size else float('nan')


def env(x, hop=240):
    n = len(x) // hop
    return np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1)), hop / FS
