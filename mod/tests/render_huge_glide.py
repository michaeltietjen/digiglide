"""A huge glide: C major around middle C (C4 E4 G4 C5 E5) up to D minor an octave and a tone higher (D5 F5 A5 D6 F6),
every voice 13 to 14 semitones, PATH Ease over 2 bars at 90 BPM, with DigiGlide's drift (8) and vibrato (4).
DigiGlide's voice leading would take the nearest D minor (a step or two per voice), so the voices are driven directly
with the model's glide engine (path_at, drift and vibrato as model/digiglide.py); the per-block pitch goes into the
frames' note words as the firmware sends them, rendered by the SHARC emulator on a BRICKGLIDE PAD-like WAVETONE pad.
    ~/dn2-workspace/repos/digikit/.venv/bin/python render_huge_glide.py"""
import json, math, os, sys
sys.path.insert(0, os.path.expanduser('~/glide/model'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
import digiglide as G
import dn2paths as P, dn2frame as D, dn2synth as S
OUT = os.path.expanduser('~/glide/renders/M5')
PAD = json.load(open(os.path.expanduser('~/glide/sounds/BRICKGLIDE_PAD.json')))
BPM, BAR = 90, 4000
FROM = [60, 64, 67, 72, 76]
TO = [74, 77, 81, 86, 89]
HOLD, GLIDE, AFTER = 2 * BAR, 2 * BAR, 2 * BAR
N = HOLD + GLIDE + AFTER + int(2.5 * BAR)

# voices: the model's Voice for drift / vibrato, a 2-point path with the Ease shape
m = G.DigiGlide(BPM)
pitch = np.zeros((N, 5))
for i, v in enumerate(m.v[:5]):
    v.started, v.on, v.note = True, True, FROM[i]
    v.cur = v.tgt = FROM[i] * 100.0
    v.drift, v.vib, v.rate = 8.0, 4.0, 0.15 + 0.05 * i
    v.rng = G.Rng(0, 0, i, G.R_DRIFT)
for b in range(N):
    if b == HOLD:
        for i, v in enumerate(m.v[:5]):
            v.note = TO[i]
            m.push(i, glide=GLIDE / 1500.0, shape=2)
    row = m.block()
    pitch[b] = [c for c, _, _, _ in row[:5]]

snd = S.Sound('WAVETONE')
for label, val in PAD['sound_slots'].items():
    snd.set(int(label.split('(')[1].rstrip(')')), int(val, 16))
snd.set('FILTER.FREQ', 84)
song = S.Song(bpm=BPM)
for n_, val in (('Reverb.DEC', 0x5800), ('Reverb.PRE', 0x1800), ('Delay.TIME', 0x2000), ('Delay.FDBK', 0x3000)):
    song.set_fx(n_, val)
pans = [0, -0.4, 0.4, -0.2, 0.2]
for i in range(5):
    s_ = S.Sound('WAVETONE'); s_.slots = dict(snd.slots)
    s_.set(89, int(0x4000 + pans[i] * 64 * 256))       # BRICKGLIDE's SPRD 77 pans
    song.assign(i, s_)
    song.note(2, i, FROM[i], 100)
frames = song.frames(N + 2)
out = []
release = HOLD + GLIDE + AFTER + 2
for b, f in enumerate(frames):
    f = bytearray(D.swap16(f))
    p = pitch[max(0, b - 2)]
    for i in range(5):
        f[2 + 2 * i:4 + 2 * i] = int(round(p[i] * 256 / 100)).to_bytes(2, 'big')
    if b == release:
        f[0x24:0x26] = (0x1F).to_bytes(2, 'big'); f[0x28:0x2A] = (0x1F).to_bytes(2, 'big')
    out.append(D.swap16(bytes(f)))
sec7, snap = P.snap('stock')
L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), out)
L, R = np.array(L), np.array(R)
g = 10 ** (-1 / 20) / max(np.abs(L).max(), np.abs(R).max())
path = os.path.join(OUT, 'huge_glide_Cmaj_to_Dmin.wav')
D.write_wav(path, L * g, R * g)
st = np.abs(np.diff(pitch[HOLD:HOLD + GLIDE + 2], axis=0)).max()
print(f'{len(L) / 48000:.1f} s; glide {GLIDE / 1500:.1f} s; largest step {st:.2f} cent per block -> {path}')
