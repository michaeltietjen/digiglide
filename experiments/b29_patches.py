"""Build 29: the five FM TONE sounds (and STILL AIR again on a TUNE PURE, FAN 64 capture). Measured in the SHARC emulator
(b29_fm_algos.py, b29_fm_algos2.py, b29_fm_ratios.py, b29_fm_levels.py):
  - Operators heard / who modulates whom. Algorithm 5: X = C, Y = A; B2 -> B1 -> A -> C, FDBK on B2: the full chain.
    Algorithm 7: X = C + A (A also modulates C), Y = B1 + B2: all four heard. Algorithm 1: X = C, Y = B1; A -> C with
    FDBK on A, B2 -> B1 -> C. Algorithm 2: A -> C and B2 -> B1, two pairs.
  - Ratios: RTOC 0.25 0.5 0.75 1 2 .. 16 (index 3 = 1); RTOA in quarters at the bottom (index 3 = 1, 5 = 1.5, 7 = 2);
    RTOB's word is 2 x (19 x B1 index + B2 index) on the RTOC list. An offset word is the ratio in 1/16384 (164 = 1 %).
  - AB LEVEL (LVAB, slot 53) scales A LEVEL and B LEVEL together in the DSP: at 0x3000 and below no FM is left, 0x4000
    is the sound's own, 0x5000 about three times as bright, 0x6000 harsh. That is COUPLE on every sound here.
  - MIX: 0 = X only, 64 = both, 127 = Y only."""
from b29_sounds import SOUNDS, R, OFS
T = [0.25, 0.5, 0.75] + list(range(1, 17))
RB = lambda b1, b2: R(2 * (19 * T.index(b1) + T.index(b2)))
PAD = {'AMP.HOLD': 127, 'AMP.DEC': 127, 'AMP.SUS': 127, 'REVERB SEND': 45}
COUPLE = 'AB LEVEL (LVAB, FM TONE page 4): up for more FM between the operators, down to the centre for the sound as saved, below about -16 for none'

SOUNDS['still'] = (
    'STILL AIR', 'Four sines a voice near unison, each a hair off the others: pure, slowly beating.',
    {**PAD, 'ALGO': 6, 'MIX': 64, 'RTOC': 3, 'RTOA': 3, 'RTOB': RB(1, 1), 'COFF': OFS(0), 'AOFF': OFS(1.2),
     'B1OF': OFS(-1.0), 'B2OF': OFS(2.3), 'A LEVEL': 6, 'B LEVEL': 6, 'FDBK': 0, 'FILTER.FREQ': 112, 'AMP.ATK': 85,
     'AMP.REL': 105},
    COUPLE + '. On this sound a little goes far: it turns the beating sines into a slowly turning tone.',
    None,
    'VCNT 4, GLID 2 bars, HOLD on, DRFT 30, VIB 2, TYPE MAJ, EXT 9, VOIC 90', 'still')

SOUNDS['chain'] = (
    'SLOW CHAIN', 'B2 into B1 into A into C, low levels, the modulators a hair off pitch; the FM amount breathes '
    'from pure to restless once in 8 bars.',
    {**PAD, 'ALGO': 4, 'MIX': 0, 'RTOC': 3, 'RTOA': 3, 'RTOB': RB(1, 1), 'AOFF': OFS(0.7), 'B1OF': OFS(-0.5),
     'B2OF': OFS(1.1), 'A LEVEL': 34, 'B LEVEL': 30, 'FDBK': 0, 'FILTER.FREQ': 112, 'AMP.ATK': 72, 'AMP.REL': 102},
    COUPLE + '. The LFO already rides it; turn the LFO depth down to ride it by hand.',
    ('LVAB', 0x4000, 0x1000, 8),
    'VCNT 4, GLID 1 bar, HOLD on, DRFT 12, VIB 3, TYPE MIN, EXT 7, VOIC 90', 'chain')

SOUNDS['ring'] = (
    'DARK RING', 'The same chain with feedback on B2, its last operator, and more FM; the filter low, opening over '
    '16 bars and closing again.',
    {**PAD, 'ALGO': 4, 'MIX': 0, 'RTOC': 3, 'RTOA': 3, 'RTOB': RB(1, 1), 'AOFF': OFS(0.9), 'B1OF': OFS(-0.6),
     'B2OF': OFS(1.4), 'A LEVEL': 44, 'B LEVEL': 38, 'FDBK': 34, 'FILTER.FREQ': 48, 'FILTER.RESO': 20,
     'AMP.ATK': 78, 'AMP.REL': 104},
    COUPLE + '. FDBK is the second knob to ride: it is the ring.',
    ('FILTER.FREQ', 0x4200, 0x1200, 16),
    'VCNT 4, GLID 2 bars, HOLD on, DRFT 10, VIB 2, TYPE MIN, VOIC 70', 'ring')

SOUNDS['bells'] = (
    'IRON BELLS', 'High FM, the operators at the fifth (A 1.5), the octave (B1 2) and the twelfth (B2 3), each a '
    'little off; bright, the brightness falling to a held level.',
    {'ALGO': 0, 'MIX': 36, 'RTOC': 3, 'RTOA': 5, 'RTOB': RB(2, 3), 'AOFF': OFS(3.0), 'B1OF': OFS(-2.0),
     'B2OF': OFS(4.0), 'A LEVEL': 74, 'B LEVEL': 52, 'FDBK': 14, 'A ENV DECAY': 92, 'A ENV END': 60,
     'B ENV DECAY': 84, 'B ENV END': 48, 'FILTER.FREQ': 127, 'AMP.ATK': 4, 'AMP.HOLD': 127, 'AMP.DEC': 110,
     'AMP.SUS': 96, 'AMP.REL': 98, 'REVERB SEND': 55},
    COUPLE + '. Up: clangorous. Down: a soft organ bell.',
    None,
    'VCNT 4, GLID 1/2, HOLD on, DRFT 20, VIB 4, TYPE MAJ, EXT 6+9, VOIC 100', 'bells')

SOUNDS['beat'] = (
    'BEAT FIELD', 'Two pairs a voice: C with A, and B1 with B2 0.4 % above them. No FM from one pair to the other, a '
    'little inside each. Each voice beats at its own slow rate.',
    {**PAD, 'ALGO': 6, 'MIX': 64, 'RTOC': 3, 'RTOA': 3, 'RTOB': RB(1, 1), 'COFF': OFS(0), 'AOFF': OFS(0),
     'B1OF': OFS(4.0), 'B2OF': OFS(4.0), 'A LEVEL': 22, 'B LEVEL': 22, 'FDBK': 0, 'FILTER.FREQ': 115, 'AMP.ATK': 76,
     'AMP.REL': 105},
    COUPLE + '. It adds harmonics inside each pair, and each harmonic beats faster than the one below.',
    None,
    'VCNT 3, GLID 4 bars, HOLD on, DRFT 0, VIB 0, TYPE 5TH', 'beat')

SOUNDS['pure'] = SOUNDS['still'][:5] + ('as STILL AIR but DRFT 4, VIB 0, TUNE PURE, FAN 64 (image 29)', 'pure')

if __name__ == '__main__':
    import sys
    import b29_sounds
    for n in sys.argv[1:]:
        b29_sounds.sheet(n)
        b29_sounds.render(n)
