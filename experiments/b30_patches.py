"""DigiDrone, second set (image 30): five more FM TONE drones. Same method and measurements as b29_patches.py; the
note words come from that set's captures (named last in each entry).
    ~/dn2-workspace/repos/digikit/.venv/bin/python b30_patches.py NAME [...]   (organ undertow wire hollow storm)"""
from b29_sounds import SOUNDS, R, OFS
from b29_patches import RB, PAD, COUPLE

SOUNDS['organ'] = (
    'GLASS ORGAN', 'Four partials a voice, 1 2 3 4, each a hair off, almost no FM: a soft additive organ. Made for '
    'TUNE PURE, where the partials of the chord notes line up.',
    {**PAD, 'ALGO': 6, 'MIX': 58, 'RTOC': 3, 'RTOA': 7, 'RTOB': RB(3, 4), 'AOFF': OFS(0.6), 'B1OF': OFS(-0.4),
     'B2OF': OFS(0.9), 'A LEVEL': 8, 'B LEVEL': 10, 'FDBK': 0, 'FILTER.FREQ': 104, 'AMP.ATK': 80, 'AMP.REL': 104},
    COUPLE + '. Up: the partials start to bend each other and the organ turns reedy.',
    None,
    'VCNT 4, GLID 2 bars, HOLD on, DRFT 4, VIB 0, TUNE PURE, FAN 64, TYPE MAJ, EXT 9, VOIC 90', 'pure')

SOUNDS['undertow'] = (
    'UNDERTOW', 'The chain an octave down: every operator at 0.5, B2 with feedback, the filter low. A heavy floor '
    'that turns over slowly.',
    {**PAD, 'ALGO': 4, 'MIX': 0, 'RTOC': 1, 'RTOA': 1, 'RTOB': RB(0.5, 0.5), 'AOFF': OFS(0.8), 'B1OF': OFS(-0.7),
     'B2OF': OFS(1.5), 'A LEVEL': 40, 'B LEVEL': 34, 'FDBK': 22, 'FILTER.FREQ': 60, 'FILTER.RESO': 10,
     'AMP.ATK': 82, 'AMP.REL': 108},
    COUPLE + '. Up: the floor growls.',
    ('LVAB', 0x4000, 0x0c00, 16),
    'VCNT 4, GLID 2 bars, HOLD on, DRFT 10, VIB 2, TYPE MIN, VOIC 70', 'ring')

SOUNDS['wire'] = (
    'WIRE CHOIR', 'One modulator (A, with feedback) drives the three operators that are heard: the nearest thing here '
    'to a shared coupling line. The three are a hair apart, so they answer it differently.',
    {**PAD, 'ALGO': 2, 'MIX': 64, 'RTOC': 3, 'RTOA': 3, 'RTOB': RB(1, 2), 'AOFF': OFS(1.5), 'B1OF': OFS(-0.8),
     'B2OF': OFS(1.2), 'A LEVEL': 36, 'B LEVEL': 20, 'FDBK': 18, 'FILTER.FREQ': 108, 'AMP.ATK': 74, 'AMP.REL': 102},
    COUPLE + '. FDBK roughens the one modulator, and so all three at once.',
    ('LVAB', 0x4000, 0x1000, 16),
    'VCNT 4, GLID 1 bar, HOLD on, DRFT 12, VIB 3, TYPE MIN, EXT 7, VOIC 90', 'chain')

SOUNDS['hollow'] = (
    'HOLLOW FIFTHS', 'Each voice carries its own fifth: C at 1 with A at 1.5, and above them B1 at 2 and B2 at 3. '
    'Little FM. On fifth chords the stack is all open intervals.',
    {**PAD, 'ALGO': 6, 'MIX': 54, 'RTOC': 3, 'RTOA': 5, 'RTOB': RB(2, 3), 'AOFF': OFS(0.5), 'B1OF': OFS(1.0),
     'B2OF': OFS(-0.7), 'A LEVEL': 14, 'B LEVEL': 12, 'FDBK': 0, 'FILTER.FREQ': 106, 'AMP.ATK': 78, 'AMP.REL': 105},
    COUPLE + '. Up: A at the fifth puts a tone an octave under each note.',
    None,
    'VCNT 3, GLID 4 bars, HOLD on, DRFT 0, VIB 0, TYPE 5TH', 'beat')

SOUNDS['storm'] = (
    'STORM GLASS', 'The chain with its operators spread: B2 at 0.5 (with feedback) into B1 at 3 into A at 2 into C. '
    'The FM amount swells and falls every 8 bars, from glassy to weather.',
    {**PAD, 'ALGO': 4, 'MIX': 0, 'RTOC': 3, 'RTOA': 7, 'RTOB': RB(3, 0.5), 'AOFF': OFS(1.0), 'B1OF': OFS(-1.5),
     'B2OF': OFS(2.0), 'A LEVEL': 28, 'B LEVEL': 24, 'FDBK': 10, 'FILTER.FREQ': 104, 'AMP.ATK': 76, 'AMP.REL': 104,
     'REVERB SEND': 55},
    COUPLE + '. The LFO rides it; at the top of the swell it is meant to be rough.',
    ('LVAB', 0x3e00, 0x0e00, 8),
    'VCNT 4, GLID 2 bars, HOLD on, DRFT 30, VIB 2, TYPE MAJ, EXT 9, VOIC 90', 'still')

if __name__ == '__main__':
    import sys
    import b29_sounds
    for n in sys.argv[1:]:
        b29_sounds.sheet(n)
        b29_sounds.render(n)
