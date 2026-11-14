"""Image 18 on the unit: "the arp is very quiet on quicker progressions". The OS's own frames into the SHARC
emulator; the level of every arp note, DigiGlide's arp against a stock arp that plays the same notes.
  WHO    dg     the DigiGlide image, track 1 a DigiGlide track (TYPE MIN, EXT 7): the arp is given the chord
         stock  the stock OS, the same trigs; the chord's notes are put into the arp's note set from outside
                (0x40599728) as soon as the trig's own note is in it
  PROG   bar    one trig a bar (C3)            step  a trig every step, the root moving (C D F G ...)
         beat   a trig every 4 steps
  SPEED  the arp's SPEED byte (sound +SPEED_OFF), ATK the sound's AMP ATK, NLEN the arp's N.LEN byte
Writes OUT.npz (audio, note-ons with their voice records) and prints the RMS of every note.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python arp_level.py IMAGE.syx WHO PROG SPEED ATK NLEN OUT"""
import os, struct, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, U16, Ui
import dn2paths as P, dn2frame as D

img, who, prog, speed, atk, nlen, out = sys.argv[1:8]
SPEED_OFF, NLEN_OFF = int(os.environ.get('SPEED_OFF', 0)), int(os.environ.get('NLEN_OFF', 0))
BLOCKS = int(os.environ.get('BLOCKS', 3000))
RESERVE = int(os.environ.get('RESERVE', 4))
ARP_SET, UP, T = 0x40599728, 2, 0
CH = (0, 3, 7, 10)
s = Session(img if who == 'dg' else None, tag='al_' + who, solo=True, reserve=RESERVE)
if who == 'dg':
    s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, pos=64, voic=64), t=T, mach=None, atk=None)
if atk != '-':
    s.k.sound_slot(T, 81, int(atk) << 8)
R4 = (48, 50, 61, 66)
trigs = {'bar': [(0, 48, 127)], 'beat': [(4 * i, R4[i], 30) for i in range(4)],
         'step': [(i, R4[i % 4], 6) for i in range(16)]}[prog]
for st, n, ln in trigs:
    s.trig(st, note=n, length=ln, t=T)
h = s.k.h
snd = s.k.sound(T)
h.uc.mem_write(snd + 351, bytes([UP])); h.uc.mem_write(snd + 374, bytes([UP]))
if speed != '-' and SPEED_OFF:
    h.uc.mem_write(snd + SPEED_OFF, bytes([int(speed)]))
if nlen != '-' and NLEN_OFF:
    h.uc.mem_write(snd + NLEN_OFF, bytes([int(nlen)]))
roots = {n for _, n, _ in trigs}


def inject(i):                                           # stock: the chord of the trig's note into the arp's set
    w = list(struct.unpack('>4I', bytes(h.r(ARP_SET + 16 * T, 16))))
    have = {32 * a + b for a in range(4) for b in range(32) if w[a] >> b & 1}
    want = {r + c for r in have & roots for c in CH}     # (no root is in another root's chord: the rest is ours)
    if want != have:
        w = [0, 0, 0, 0]
        for n in want:
            w[n // 32] |= 1 << (n % 32)
        h.w(ARP_SET + 16 * T, struct.pack('>4I', *w))


fr = s.play(BLOCKS, bpm=120, each=inject if who == 'stock' else None)[:BLOCKS]
ons, offs = [], []
for b, f in enumerate(fr):
    on, off = U16(f, 0x22), U16(f, 0x24)
    for v in range(16):
        if U16(f, 0xA5A + 2 * v) != T:
            continue
        if on >> v & 1:
            ons.append((b, v, U16(f, 2 + 2 * v) >> 8))
        if off >> v & 1:
            offs.append((b, v))
# (a sound slot written from here does not reach the frame: AMP ATK / AMP RSET go straight into every voice record)
for sl, env in ((81, 'ATKF'), (92, 'RSETF')):
    if os.environ.get(env):
        o = [0xDA + 146 * v + 2 * (sl - 25) for v in range(16)]
        fr2 = []
        for f in fr:
            f = bytearray(f)
            for a in o:
                f[a:a + 2] = (int(os.environ[env]) << 8).to_bytes(2, 'big')
            fr2.append(bytes(f))
        fr = fr2
sec7, snap = P.snap('stock')
L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), [D.swap16(bytes(f)) for f in fr])
x = (np.asarray(L, float) + np.asarray(R, float)) / 2
spb = len(x) // len(fr)
rms = []
for i, (b, v, n) in enumerate(ons):
    e = ons[i + 1][0] if i + 1 < len(ons) else min(len(fr), b + 200)
    seg = x[b * spb:e * spb]
    rms.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
recs = np.array([list(fr[b][0xDA + 146 * v:0xDA + 146 * (v + 1)]) for b, v, n in ons], dtype=np.uint8)
np.savez(out, x=x.astype(np.float32), ons=np.array(ons), offs=np.array(offs), rms=np.array(rms), recs=recs,
         hdr=np.array([list(fr[b][:0xDA]) for b, v, n in ons], dtype=np.uint8))
tag = f'RES {who} {prog} speed {speed} ATKF {os.environ.get("ATKF")} RSETF {os.environ.get("RSETF")}'
gaps = [ons[i + 1][0] - ons[i][0] for i in range(len(ons) - 1)]
lens = []
for b, v, n in ons:
    o = [ob for ob, ov in offs if ov == v and ob > b]
    lens.append(o[0] - b if o else -1)
print(tag, 'sound slots 81 (ATK) 92 (RSET):', s.k.sound_slot(T, 81), s.k.sound_slot(T, 92), 'record RSET words at the note-ons:', sorted({int(r[134]) << 8 | int(r[135]) for r in recs}))
print(tag, 'note-ons', len(ons), 'gap', gaps[:6], 'len', lens[:6])
print(tag, 'notes ', [n for b, v, n in ons][:24])
print(tag, 'voices', [v for b, v, n in ons][:24])
print(tag, 'rms   ', ' '.join(f'{r:.4f}' for r in rms[:32]))
print(tag, 'rms all %.4f  mean note %.4f  dB %.1f' % (float(np.sqrt(np.mean(x ** 2))), float(np.mean(rms)) if rms else 0,
      20 * np.log10(max(float(np.mean(rms)) if rms else 0, 1e-9))))
if who == 'dg':
    print(tag, 'dg', s.dg())
