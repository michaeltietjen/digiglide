"""A progression played the way DigiGlide plays it (the M1 model's voice leading, glides, drift and vibrato), its
per-block pitch written into the frames' note words as the firmware sends them (M3 / M4: within 0.2 cent), rendered by
the SHARC emulator on a BRICKGLIDE PAD-like WAVETONE pad with the SPRD pans.
    render_model_progression.py NAME KEY SCALE CHORD DEG,DEG,... [--bpm 90] [--bars 2] [--glid 5] [--path 0]
    e.g. render_model_progression.py G_Em_Am_C_D 7 0 0 0,5,1,3,4"""
import argparse, json, os, sys
sys.path.insert(0, os.path.expanduser('~/glide/model'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
import digiglide as G
import dn2paths as P, dn2frame as D, dn2synth as S
ap = argparse.ArgumentParser()
for n_ in ('name', 'key', 'scale', 'chord', 'degs'):
    ap.add_argument(n_)
ap.add_argument('--bpm', type=float, default=90)
ap.add_argument('--bars', type=int, default=2)
ap.add_argument('--glid', type=int, default=5)
ap.add_argument('--path', type=int, default=0)
ap.add_argument('--oct', type=int, default=0, help='shift every voice by this many octaves (a listening aid)')
ap.add_argument('--sound', choices=('pad', 'glass', 'analog'), default='pad')
a = ap.parse_args()
OUT = os.path.expanduser('~/glide/renders/M5')
PAD = json.load(open(os.path.expanduser('~/glide/sounds/BRICKGLIDE_PAD.json')))
BAR = int(round(240 / a.bpm * 1500))
degs = [int(x) for x in a.degs.split(',')]
base = G.Params(**PAD['digiglide']).copy(key=int(a.key), scl=int(a.scale), chrd=int(a.chord), glid=a.glid, path=a.path)
ev, nb = G.progression([base.copy(deg=d) for d in degs], a.bars, a.bpm, n_tail_bars=3)
pitch, gate, pan, level, m = G.run(ev, nb, a.bpm)
pitch, gate, pan = np.array(pitch), np.array(gate), np.array(pan)

snd = S.Sound('WAVETONE')
for label, val in PAD['sound_slots'].items():
    snd.set(int(label.split('(')[1].rstrip(')')), int(val, 16))
snd.set('FILTER.FREQ', 84)
if a.sound == 'glass':        # WAVETONE on the HARM table: a glassy pad, quicker attack, long release, more reverb
    for n_, v in (('SYN.TBL1', 0x100), ('SYN.WAV1', 40), ('SYN.TBL2', 0x100), ('SYN.WAV2', 92), ('SYN.PD1', 62),
                  ('SYN.LEV1', 100), ('SYN.LEV2', 70), ('SYN.DRIF', 20), ('FILTER.FREQ', 104), ('FILTER.RESO', 20),
                  ('AMP.ATK', 30), ('AMP.HOLD', 127), ('AMP.DEC', 127), ('AMP.SUS', 120), ('AMP.REL', 100),
                  ('FX.REV', 84), ('FX.DEL', 40), ('FX.CHR', 30)):
        snd.set(n_, v)
if a.sound == 'analog':       # two saws well apart, lots of osc drift, darker resonant low-pass, chorus: a vintage poly
    for n_, v in (('SYN.TBL1', 0), ('SYN.WAV1', 0), ('SYN.TBL2', 0), ('SYN.WAV2', 0), ('SYN.LEV1', 100),
                  ('SYN.LEV2', 96), ('SYN.DRIF', 70), ('FILTER.FREQ', 70), ('FILTER.RESO', 38), ('AMP.ATK', 70),
                  ('AMP.HOLD', 127), ('AMP.DEC', 127), ('AMP.SUS', 124), ('AMP.REL', 96), ('FX.REV', 56),
                  ('FX.DEL', 24), ('FX.CHR', 70)):
        snd.set(n_, v)
    snd.set('SYN.TUN2', 0x4014)
song = S.Song(bpm=a.bpm)
for n_, val in (('Reverb.DEC', 0x5800), ('Reverb.PRE', 0x1800), ('Delay.TIME', 0x2000), ('Delay.FDBK', 0x3000)):
    song.set_fx(n_, val)
NV = 6
for i in range(NV):
    s_ = S.Sound('WAVETONE'); s_.slots = dict(snd.slots)
    s_.set(89, int(0x4000 + pan[0][i] * 64 * 256))
    song.assign(i, s_)
out, was = [], np.zeros(NV, bool)
for b, f in enumerate(song.frames(nb)):
    f = bytearray(D.swap16(f))
    g = gate[b]
    on = sum(1 << i for i in range(NV) if g[i] and not was[i])
    off = sum(1 << i for i in range(NV) if was[i] and not g[i])
    was = g.copy()
    for i in range(NV):
        if np.isfinite(pitch[b][i]):
            f[2 + 2 * i:4 + 2 * i] = int(round((pitch[b][i] + 1200 * a.oct) * 256 / 100)).to_bytes(2, 'big')
            f[0x34 + 2 * i:0x36 + 2 * i] = (100 << 8).to_bytes(2, 'big')
    for o, v in ((0x22, on), (0x26, on), (0x24, off), (0x28, off)):
        f[o:o + 2] = v.to_bytes(2, 'big')
    out.append(D.swap16(bytes(f)))
sec7, snap = P.snap('stock')
L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), out)
L, R = np.array(L), np.array(R)
gn = 10 ** (-1 / 20) / max(np.abs(L).max(), np.abs(R).max())
path = os.path.join(OUT, a.name + '.wav')
D.write_wav(path, L * gn, R * gn)
names = lambda b: ' '.join(f'{G.NOTE_NAMES[int(round(c / 100 + 12 * a.oct)) % 12]}{int(round(c / 100 + 12 * a.oct)) // 12 - 1}'
                           for c in sorted(x for x, gg in zip(pitch[b], gate[b]) if gg and np.isfinite(x)))
print(f'{len(L) / 48000:.1f} s -> {path}')
for k, d in enumerate(degs):
    print(f'  chord {k + 1} ({G.ROMAN[d]}): {names((k + 1) * a.bars * BAR - 1)}')
