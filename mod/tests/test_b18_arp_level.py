"""DigiGlide's arp is as loud as stock's. A DigiGlide track (TYPE MIN, EXT 7) with the stock arp on UP, a trig every
4 steps (C3 D3 C#4 F#4, so the chord changes under the running arp), against the stock OS playing the same trigs
with the same chord notes put into its arp's note set from outside. Both reserve 5 voices on the track. The OS's
own frames go through the SHARC emulator; the level of a note is the RMS from its note-on to the next one.
  A  arp SPEED slow (10)     B  arp SPEED fast (19)
For each: the same notes at the same blocks; every arp note's voice record is byte for byte stock's (velocity,
level, AMP RSET and the rest); every note's level is within 1 dB of the stock note's.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b18_arp_level.py [DIGIGLIDE.syx]"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dgkit import Session, latest, Ui, U16
import dn2paths as P, dn2frame as D

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
ARP_SET, UP, T, BLOCKS = 0x40599728, 2, 0, 3000          # OS 1.12: the arp's held notes, 16 bytes a track
MODE, MODE2, SPEED = 351, 374, 352                       # sound bytes (N.LEN is +354)
ROOTS, CH = (48, 50, 61, 66), (0, 3, 7, 10)              # no root is a note of another root's chord


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def run(dg, speed):
    s = Session(img if dg else None, tag='b18lv' + ('d' if dg else 's'), solo=True, reserve=5)
    if dg:
        s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, pos=64, voic=64), t=T, mach=None, atk=None)
    for i, r in enumerate(ROOTS):
        s.trig(4 * i, note=r, length=30, t=T)
    h, snd = s.k.h, s.k.sound(T)
    for o, v in ((MODE, UP), (MODE2, UP), (SPEED, speed)):
        h.uc.mem_write(snd + o, bytes([v]))

    def inject(i):                                       # stock: the chord of each trig's note into the arp's set
        w = struct.unpack('>4I', bytes(h.r(ARP_SET + 16 * T, 16)))
        have = {32 * a + b for a in range(4) for b in range(32) if w[a] >> b & 1}
        want = {r + c for r in have & set(ROOTS) for c in CH}
        if want != have:
            w = [0, 0, 0, 0]
            for n in want:
                w[n // 32] |= 1 << (n % 32)
            h.w(ARP_SET + 16 * T, struct.pack('>4I', *w))

    fr = s.play(BLOCKS, bpm=120, each=None if dg else inject)[:BLOCKS]
    ons = [(b, v, U16(f, 2 + 2 * v) >> 8) for b, f in enumerate(fr) for v in range(16)
           if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) == T]
    recs = [bytes(fr[b][0xDA + 146 * v:0xDA + 146 * (v + 1)]) for b, v, n in ons]
    sec7, snap = P.snap('stock')
    L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), [D.swap16(bytes(f)) for f in fr])
    x = (np.asarray(L, float) + np.asarray(R, float)) / 2
    spb = len(x) // len(fr)
    rms = []
    for i, (b, v, n) in enumerate(ons):
        e = ons[i + 1][0] if i + 1 < len(ons) else min(len(fr), b + 100)
        rms.append(float(np.sqrt(np.mean(x[b * spb:e * spb] ** 2))))
    return ons, recs, rms, (s.dg()['trigs'] if dg else 0)


for case, speed in (('A', 10), ('B', 19)):
    d_on, d_rec, d_rms, ev = run(True, speed)
    s_on, s_rec, s_rms, _ = run(False, speed)
    n = min(len(d_on), len(s_on))
    gap = d_on[1][0] - d_on[0][0] if len(d_on) > 1 else 0
    check(len(d_on) == len(s_on) and len(d_on) >= 8 and [(b, k) for b, v, k in d_on] == [(b, k) for b, v, k in s_on],
          f'{case}: SPEED {speed} (a note every {gap} blocks): the same {len(d_on)} notes at the same blocks as the stock arp '
          f'({[k for b, v, k in d_on][:8]} ... / {[k for b, v, k in s_on][:8]} ...)')
    check(len({k for b, v, k in d_on}) >= 8 and ev == 0, f'{case}: the arp walks all four chords ({len({k for b, v, k in d_on})} different notes), no DigiGlide chord event ({ev})')
    diff = [i for i in range(n) if d_rec[i] != s_rec[i] or d_on[i][1] != s_on[i][1]]
    check(not diff, f'{case}: every note\'s voice and voice record are stock\'s ({len(diff)} of {n} differ: {diff[:8]})')
    db = [20 * np.log10(max(d_rms[i], 1e-9) / max(s_rms[i], 1e-9)) for i in range(n)]
    worst = max(db, key=abs) if db else 99
    check(db and max(abs(x) for x in db) <= 1.0 and min(s_rms[:n]) > 1e-4,
          f'{case}: every note within 1 dB of the stock arp\'s note (worst {worst:+.2f} dB; quietest stock note {min(s_rms[:n]):.4f}, '
          f'mean {np.mean(d_rms[:n]):.4f} / {np.mean(s_rms[:n]):.4f})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
