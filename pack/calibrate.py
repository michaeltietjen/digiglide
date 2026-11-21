"""Sound pack calibration (DIGIGLIDE_SOUNDS_20.md, "Building them" 1 and 3): measure the Digitone II's own parameter
curves in the SHARC emulator, so musical targets (Hz, seconds) become knob values.

  - filter types: the per-voice frame word +0xB4 + 2v selects a voice's filter (the sound's byte +0xDF; type = the
    parameter group - 5). Noise through each type: COMB+ rings at whole multiples of its frequency, COMB- at the odd
    half multiples; LOWPASS 4 and MULTIMODE (TYPE 0) cut above FREQ.
  - cutoff: noise through MULTIMODE (TYPE 0, low-pass) and LOWPASS 4, FREQ swept: the -3 dB point of the spectrum
    relative to the pass band.
  - amp attack and release: a sine note, ATK / REL swept: attack = time to reach 90 % of the held level; release =
    time from the note-off until the level is down 40 dB.
Writes pack/calibration.json.
    ~/dn2-workspace/repos/digikit/.venv/bin/python calibrate.py"""
import json, math, os, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
import dn2paths as P, dn2frame as D, dn2synth as S

FS = 48000
sec7, snap = P.snap('stock')
OUT = os.path.dirname(os.path.abspath(__file__))


def render(slots, ftype=0, notes=(60,), blocks=1500, off_at=None, raw=False):
    """one WAVETONE voice per note; slots: {slot: raw value or knob}; ftype: the voices' filter type word."""
    snd = S.Sound('WAVETONE')
    for k, v in slots.items():
        snd.set(k, v)
    song = S.Song(bpm=120)
    for i, n in enumerate(notes):
        song.assign(i, snd).track(i, 0).note(2, i, n, 100, length=(off_at - 2) if off_at else None)
    out = []
    for f in song.frames(blocks):
        f = bytearray(D.swap16(f))
        for i in range(len(notes)):
            f[0xB4 + 2 * i:0xB6 + 2 * i] = ftype.to_bytes(2, 'big')
        for o in range(0x9C8 + 2 * 25, 0x9C8 + 2 * 70, 2):    # FX returns muted: dry measurements
            pass
        out.append(D.swap16(bytes(f)))
    L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), out)
    return (np.array(L) + np.array(R)) / 2


NOISE = {'SYN.LEV1': 0, 'SYN.LEV2': 0, 'SYN.NLEV': 127, 'SYN.WDTH': 127, 'SYN.BASE': 0, 'AMP.ATK': 0, 'AMP.SUS': 127,
         'AMP.HOLD': 127, 'FX.REV': 0, 'FX.DEL': 0, 'FX.CHR': 0}


def spectrum(x, start=FS // 4):
    seg = x[start:start + 32768]
    w = np.hanning(len(seg))
    S_ = np.abs(np.fft.rfft(seg * w)) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / FS)
    k = np.ones(64) / 64                                  # smooth
    return f, np.convolve(S_, k, 'same')


def cutoff(x):
    f, s = spectrum(x)
    db = 10 * np.log10(s + 1e-30)
    band = (f > 60) & (f < 200)
    ref = np.median(db[band])
    above = np.where((f > 200) & (db < ref - 3))[0]
    return float(f[above[0]]) if above.size else float('nan')


res = {'filter_types': {}, 'cutoff_hz': {}, 'amp_attack_s': {}, 'amp_release_s': {}}

# 1. filter types: comb polarity at FREQ 64 with high feedback, noise in
for ft in (3, 5):
    x = render({**NOISE, 67: 64, 68: 110, 66: 127}, ftype=ft, blocks=1600)
    f, s = spectrum(x)
    db = 10 * np.log10(s + 1e-30)
    lo = (f > 100) & (f < 6000)
    peaks = [i for i in np.where(lo)[0][1:-1] if db[i] > db[i - 1] and db[i] >= db[i + 1] and db[i] > np.median(db[lo]) + 6]
    pf = [float(f[i]) for i in peaks][:12]
    gaps = np.diff(pf) if len(pf) > 2 else []
    f0 = float(np.median(gaps)) if len(gaps) else float('nan')
    ratio = pf[0] / f0 if f0 == f0 and f0 > 0 else float('nan')
    kind = 'COMB+ (peaks at whole multiples)' if abs(ratio - round(ratio)) < 0.25 else 'COMB- (peaks at half multiples)'
    res['filter_types'][ft] = dict(first_peaks_hz=pf[:6], spacing_hz=f0, first_over_spacing=ratio, kind=kind)
    print(f'filter type {ft}: peaks {[round(p) for p in pf[:6]]} spacing {f0:.0f} Hz, first/spacing {ratio:.2f} -> {kind}')

# 2. cutoff vs FREQ for MULTIMODE (type 0, TYPE 0 = low-pass end) and LOWPASS 4 (type 1)
for ft, extra in ((0, {66: 0, 68: 0}), (1, {68: 0})):
    table = {}
    for knob in (16, 32, 48, 64, 80, 96, 112):
        x = render({**NOISE, **extra, 67: knob}, ftype=ft, blocks=1600)
        table[knob] = cutoff(x)
    res['cutoff_hz'][{0: 'MULTIMODE', 1: 'LOWPASS 4'}[ft]] = table
    print(f'cutoff, filter type {ft}:', {k: round(v) for k, v in table.items()})

# 3. amp attack and release (sine, filter open)
SINE = {'SYN.WAV1': 120, 'SYN.LEV1': 100, 'SYN.LEV2': 0, 'SYN.NLEV': 0, 'SYN.DRIF': 0, 'FILTER.FREQ': 127,
        'AMP.HOLD': 127, 'AMP.SUS': 127, 'FX.REV': 0, 'FX.DEL': 0, 'FX.CHR': 0}


def env(x, hop=240):
    n = len(x) // hop
    return np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1)), hop / FS


for knob in (16, 32, 48, 64, 80, 96, 112):
    x = render({**SINE, 'AMP.ATK': knob, 'AMP.REL': 0}, blocks=int(12 * 1500))
    e, dt = env(x)
    held = np.median(e[-200:])
    t90 = (np.argmax(e >= 0.9 * held) * dt) - 2 * 32 / FS
    res['amp_attack_s'][knob] = float(t90)
for knob in (16, 32, 48, 64, 80, 96, 112):
    x = render({**SINE, 'AMP.ATK': 0, 'AMP.REL': knob}, blocks=int(16 * 1500), off_at=1500)
    e, dt = env(x)
    held = np.median(e[int(0.5 / dt):int(0.95 / dt)])
    after = e[int((1500 * 32 / FS) / dt):]
    below = np.where(after < held * 0.01)[0]
    res['amp_release_s'][knob] = float(below[0] * dt) if below.size else float('nan')
print('attack (s):', {k: round(v, 3) for k, v in res['amp_attack_s'].items()})
print('release to -40 dB (s):', {k: round(v, 3) for k, v in res['amp_release_s'].items()})
json.dump(res, open(os.path.join(OUT, 'calibration.json'), 'w'), indent=1)
print('wrote', os.path.join(OUT, 'calibration.json'))
