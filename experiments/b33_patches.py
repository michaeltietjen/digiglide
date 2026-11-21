"""DigiDrone, the deep set (image 33). Owner on image 32: "the digidrones are too shallow sounding". Measured on the
first renders (scratch depth.py): eight of ten had nothing under 90 Hz, most nothing over 1 kHz, 16 to 70 partials.
Each sound is reworked for body: an operator an octave down where the voice had none, more FM and feedback under a
lower filter, wider operator offsets (slow beating), overdrive, and chorus, delay and more reverb. Same names, same
order, same COUPLE knob. Renders: ~/glide/renders/b33/NAME.wav.
    ~/dn2-workspace/repos/digikit/.venv/bin/python b33_patches.py NAME [...]"""
import b29_sounds
from b29_sounds import SOUNDS, R, OFS
import b29_patches, b30_patches
from b29_patches import RB, PAD, COUPLE

OLD = dict(SOUNDS)
FX = lambda rev, chr_, dly=0, od=0: {'REVERB SEND': rev, 'CHORUS SEND': chr_, 'DELAY SEND': dly, 'OVERDRIVE': od}


def deep(name, text, knobs, lfo='same', dg=None):
    title, _, old, couple, olfo, odg, cap = OLD[name]
    SOUNDS[name] = (title, text, {**old, **knobs}, couple, olfo if lfo == 'same' else lfo, dg or odg, cap)


deep('still', 'Four sines a voice: one an octave down, two near unison and one an octave up, each a little off, a '
     'little FM inside each pair. Slow wide beating over a low floor.',
     {'ALGO': 6, 'MIX': 64, 'RTOC': 1, 'RTOA': 3, 'RTOB': RB(1, 2), 'AOFF': OFS(2.5), 'B1OF': OFS(-2.0),
      'B2OF': OFS(3.5), 'A LEVEL': 20, 'B LEVEL': 18, 'FILTER.FREQ': 104, **FX(75, 70, 15)})
deep('chain', 'B2 (an octave down) into B1 into A into C, more level than before and a little feedback; the FM amount '
     'breathes from warm to growling once in 8 bars.',
     {'RTOB': RB(1, 0.5), 'AOFF': OFS(1.6), 'B1OF': OFS(-1.2), 'B2OF': OFS(2.4), 'A LEVEL': 46, 'B LEVEL': 42,
      'FDBK': 14, 'FILTER.FREQ': 98, 'FILTER.RESO': 14, **FX(68, 50, 20, 18)}, ('LVAB', 0x4000, 0x1400, 8))
deep('ring', 'The chain with strong feedback on B2 and B2 an octave down; the filter opens wide over 16 bars with '
     'resonance and closes again.',
     {'RTOB': RB(1, 0.5), 'A LEVEL': 54, 'B LEVEL': 48, 'FDBK': 46, 'FILTER.FREQ': 56, 'FILTER.RESO': 38,
      **FX(72, 40, 28, 24)}, ('FILTER.FREQ', 0x4c00, 0x1e00, 16))
deep('bells', 'High FM at the fifth, the octave and the twelfth, more of it and more feedback; bright, falling to a '
     'held level, long tails through delay and reverb.',
     {'A LEVEL': 80, 'B LEVEL': 58, 'FDBK': 20, 'AMP.REL': 108, **FX(84, 34, 44)})
deep('beat', 'Two pairs a voice: C an octave down with A, and B1 with B2 an octave up, the second pair 0.4 % sharp. '
     'More FM inside each pair; every voice beats at its own slow rate over a sub.',
     {'RTOC': 1, 'RTOA': 3, 'RTOB': RB(1, 2), 'A LEVEL': 34, 'B LEVEL': 30, 'FILTER.FREQ': 106,
      **FX(72, 62, 12, 10)}, dg='VCNT 3, GLID 4 bars, HOLD on, DRFT 6, VIB 0, FAN 30, TYPE MIN')
deep('organ', 'Five-foot organ: partials at 0.5, 1, 2 and 3, each a hair off, a little FM so the pipes speak; '
     'chorus for the tremulant.',
     {'RTOC': 1, 'RTOA': 3, 'RTOB': RB(2, 3), 'A LEVEL': 16, 'B LEVEL': 16, 'MIX': 60, 'FILTER.FREQ': 108,
      **FX(62, 78, 0, 8)}, dg='VCNT 4, GLID 2 bars, HOLD on, DRFT 4, VIB 0, TUNE PURE, FAN 40, TYPE MAJ, VOIC 90')
deep('undertow', 'The chain an octave down with strong feedback and overdrive, the filter half open: a floor with '
     'teeth that turns over slowly.',
     {'A LEVEL': 54, 'B LEVEL': 46, 'FDBK': 42, 'FILTER.FREQ': 84, 'FILTER.RESO': 18, **FX(66, 42, 18, 44)},
     ('LVAB', 0x4000, 0x1200, 16))
deep('wire', 'One modulator (A, strong feedback) drives the three operators that are heard, one of them an octave '
     'down; they answer it differently, so the choir shifts as it swells.',
     {'RTOC': 1, 'RTOB': RB(1, 2), 'A LEVEL': 50, 'B LEVEL': 30, 'FDBK': 32, 'FILTER.FREQ': 102,
      **FX(68, 66, 20, 12)}, ('LVAB', 0x4000, 0x1400, 16))
deep('hollow', 'Each voice is an open stack: 0.5, 1, 2 and 3, a little FM, wide offsets. On fifth chords '
     'everything is octaves and fifths over a sub.',
     {'RTOC': 1, 'RTOA': 3, 'RTOB': RB(2, 3), 'A LEVEL': 24, 'B LEVEL': 20, 'AOFF': OFS(1.5),
      'B1OF': OFS(2.2), 'B2OF': OFS(-1.8), 'FILTER.FREQ': 108, **FX(74, 60, 16, 8)},
     dg='VCNT 4, GLID 4 bars, HOLD on, DRFT 6, VIB 0, FAN 24, TYPE 5TH')
deep('storm', 'The chain with its operators spread and more of everything: B2 at 0.5 with feedback into B1 at 3 '
     'into A at 2 into C. The FM swells and falls every 8 bars, from glass to weather, through delay.',
     {'A LEVEL': 40, 'B LEVEL': 34, 'FDBK': 24, 'FILTER.FREQ': 100, 'FILTER.RESO': 12, **FX(78, 52, 34, 14)},
     ('LVAB', 0x3e00, 0x1500, 8))

# the DigiGlide settings each sound sets (mod/tests/make_drones_tab.py holds the codes)
_ST = 'VCNT 4, GLID 2 bars, HOLD on, DRFT 30, VIB 2, TYPE MAJ, EXT MAJ7, VOIC 90, FAN 24'
_CH = 'VCNT 4, GLID 1 bar, HOLD on, DRFT 12, VIB 3, TYPE MIN, EXT 7, VOIC 90'
_RI = 'VCNT 4, GLID 2 bars, HOLD on, DRFT 10, VIB 2, TYPE MIN, VOIC 70'
DG33 = {'still': _ST, 'storm': _ST, 'chain': _CH, 'wire': _CH, 'ring': _RI, 'undertow': _RI,
        'bells': 'VCNT 4, GLID 1/2, HOLD on, DRFT 20, VIB 4, TYPE MAJ, EXT 6, VOIC 100',
        'beat': 'VCNT 4, GLID 4 bars, HOLD on, DRFT 6, VIB 0, TYPE MIN, VOIC 70, FAN 30',
        'organ': 'VCNT 4, GLID 2 bars, HOLD on, DRFT 4, VIB 0, TUNE PURE, FAN 40, TYPE MAJ, EXT MAJ7, VOIC 90',
        'hollow': 'VCNT 4, GLID 4 bars, HOLD on, DRFT 6, VIB 0, TYPE 5TH, VOIC 127, FAN 24'}
for _n, _d in DG33.items():
    SOUNDS[_n] = SOUNDS[_n][:5] + (_d,) + SOUNDS[_n][6:]

if __name__ == '__main__':
    import sys, os
    b29_sounds.OUT_WAV = os.path.expanduser('~/glide/renders/b33')
    for n in sys.argv[1:]:
        b29_sounds.render(n)
