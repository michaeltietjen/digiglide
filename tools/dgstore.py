#!/usr/bin/env python3
"""Which kits and tracks hold DigiGlide settings on the unit (image 15 or later, OS 1.12), read over USB MIDI.
Only reads (the probe has no command that writes). Use it before and after a power cycle, a project save and load,
a kit copy or clear: the lines should be the same, or changed the way the operation should change them.

    python3 dgstore.py [--port "Digitone II"] [--all]

For every kit record of the working project (129) it reads the 292 bytes DigiGlide keeps after the record
(GLIDE_SPEC.md, Rev 6): "DGK1", then 18 bytes a track. Prints the kits that hold settings and, per track that was set
up, ON / OFF and the values. --all also lists kits whose spare bytes are neither empty nor DigiGlide's."""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgprobe import Probe

IMAGE_KITS, REC, USED = 0x405CE96C + 0xAE0200, 0x2A00, 0x28AF       # OS 1.12
LIVE_KITS, KIT, SOUNDS_PTR = 0x4210D08C, 0x5D71, 0x800052A0
NAMES = ['TYPE', 'EXT', 'KEY', 'VOIC', 'POS', 'GLID', 'PLAY', 'HOLD', 'PATH', 'TIME', 'ORDR', 'STAG', 'MOVE', 'DRFT',
         'VIB', 'SCRB', 'VCNT', 'BASS']

a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
a.add_argument('--port', default='Digitone II')
a.add_argument('--all', action='store_true')
a = a.parse_args()
p = Probe(a.port)
print('unit:', p.hello())
cur = (int.from_bytes(p.peek(SOUNDS_PTR, 4), 'big') - LIVE_KITS) / KIT
print('current kit: %s' % (int(cur) + 1 if cur == int(cur) and 0 <= cur < 129 else 'unknown (%r)' % cur))
found = 0
for kit in range(129):
    rec = IMAGE_KITS + REC * kit
    if p.peek(rec, 4) != b'\xbe\xef\xba\xce':
        print(f'kit {kit + 1}: no valid record')
        continue
    b = p.peek(rec + USED, 292)
    if b[:4] != b'DGK1':
        if a.all and any(b):
            print(f'kit {kit + 1}: spare bytes not empty and not DigiGlide\'s: {b[:16].hex()} ...')
        continue
    found += 1
    print(f'kit {kit + 1}:')
    for t in range(16):
        v = b[4 + 18 * t:22 + 18 * t]
        if v[7] not in (2, 3):
            continue
        on = f'ON, {v[16] + 2} voices' if 1 <= v[16] <= 4 else 'OFF'
        print(f'   track {t + 1:2}: {on:13} HOLD {"on" if v[7] == 3 else "off"}  '
              + ' '.join(f'{n} {x}' for n, x in zip(NAMES, v) if n not in ('PLAY', 'HOLD', 'VCNT')))
print(f'{found} kit(s) with DigiGlide settings')
