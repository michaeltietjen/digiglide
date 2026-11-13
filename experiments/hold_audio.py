"""End to end: the OS's own frames (sound records and all) into the SHARC emulator. HOLD on, short sequenced trigs:
does the chord actually sound between the trigs? RMS per 100 ms.
  hold_short  DigiGlide, HOLD on, trig LEN 2 (the unit's case: a live-recorded pattern)
  hold_long   DigiGlide, HOLD on, trig LEN 126
  off_long    DigiGlide, HOLD off, trig LEN 126
  stock_long  stock OS, the same trigs, LEN 126 (the control: the demo's track 1 sound as it is)
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python hold_audio.py IMAGE.syx CASE"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, U16, Ui
import dn2paths as P, dn2frame as D

img, case = sys.argv[1], sys.argv[2]
hold, length = {'hold_short': (1, 2), 'hold_long': (1, 126), 'off_long': (0, 126), 'off_short': (0, 2), 'stock_long': (0, 126)}[case]
s = Session(None if case == 'stock_long' else img, tag='ha_' + case, solo=True, reserve=0)
if case != 'stock_long':
    s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=hold))
    for _ in range(3):
        s.k.tap('SYN')
if os.environ.get('ATK') and case != 'stock_long':             # a slow amp attack (AMP ATK, slot 81)
    s.k.slot(0, 81, int(os.environ['ATK']) << 8)
for st, n in ((2, 64), (10, 59), (18, 55)):
    s.trig(st, note=n, length=length)
fr = s.play(3000, bpm=120)
ons = [(i, f'{U16(f, 0x22):04x}') for i, f in enumerate(fr) if U16(f, 0x22)]
offs = [(i, f'{U16(f, 0x24):04x}') for i, f in enumerate(fr) if U16(f, 0x24)]
print('RES', case, 'slot 91/92 record words:', [U16(fr[500], 0xDA + 2 * (sl - 25)) for sl in (91, 92)])
print('RES', case, 'record words for slots 81..85 on voice 0, frame 500:', [U16(fr[500], 0xDA + 2 * (sl - 25)) for sl in range(81, 86)],
      'sound slots:', [s.k.slot(0, sl) for sl in range(81, 86)])
if os.environ.get('ATK'):                                # the attack, straight into every voice's sound record
    out = []
    for f in fr:
        f = bytearray(f)
        for v in range(16):
            o = 0xDA + 146 * v + 2 * (81 - 25)
            f[o:o + 2] = (int(os.environ['ATK']) << 8).to_bytes(2, 'big')
            if os.environ.get('RSET'):                    # AMP RSET (slot 92): does the envelope restart from zero?
                o = 0xDA + 146 * v + 2 * (92 - 25)
                f[o:o + 2] = (int(os.environ['RSET']) << 8).to_bytes(2, 'big')
        out.append(bytes(f))
    fr = out
sec7, snap = P.snap('stock')
L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), [D.swap16(bytes(f)) for f in fr[:3000]])
x = (np.asarray(L, float) + np.asarray(R, float)) / 2
w = len(x) // 30
print('RES', case, 'on', ons, 'off', offs)
print('RES', case, 'rms', ' '.join(f'{float(np.sqrt(np.mean(x[i:i + w] ** 2))):.4f}' for i in range(0, len(x) - w + 1, w)))
