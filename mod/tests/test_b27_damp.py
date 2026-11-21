"""Build 27: a strum over a chord that still sounds damps the strings (owner, image 25: "strum down still doesn't work
with chord hold on", "a ring holding over"). Trigs C3 F3 G3 D3 on steps 1, 5, 9, 13, 6 voices, BASS off.
  A  HOLD on, STRU: on trigs 2..4 every string waiting for its turn is silent (level 0) from 6 blocks after the strum
     starts until its own note-on, and at its note-on it is back at its level (the level word moves a little in normal
     play, so "at its level" is within 80 % of the highest).
  B  the same, STRM.
  C  HOLD off, trigs 127 long (legato), STRU: the same.
  D  CHRD, HOLD on: no voice's level ever drops.
  E  the first strum (nothing sounds yet) and the time between strums: every voice at the full level.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b27_damp.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
STEPS = [(0, 48), (4, 53), (8, 55), (12, 50)]
NV, TRIG = 6, 187 * 4
RAMP = 120                                              # the level word rises from 0 over the first ~52 blocks after [PLAY]
                                                        # (image 21 and stock sounds too), and the first strum takes 100


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def run(tag, play, length, hold):
    s = Session(img, tag=tag, solo=True)
    s.set_sound(Ui(vcnt=NV, type=1, ext=2, glid=3, pos=64, voic=64, play=play, hold=hold, bass=0, drft=0, vib=0), t=0, mach=None, atk=None)
    for st, n in STEPS:
        s.trig(st, note=n, length=length, t=0)
    return s.play(3000, bpm=120)


def strums(fr):
    """per trig: (start block, {voice: note-on block})"""
    out = []
    for i in range(4):
        ons = {}
        for b in range(TRIG * i, TRIG * (i + 1)):
            for v in range(NV):
                if U16(fr[b], 0x22) >> v & 1:
                    ons.setdefault(v, b)
        out.append((min(ons.values()) if ons else None, ons))
    return out


lv = lambda f, v: U16(f, 0x74 + 2 * v)
for name, play, length, hold in (('A HOLD on STRU', 2, 30, 1), ('B HOLD on STRM', 1, 30, 1), ('C legato STRU', 2, 127, 0)):
    fr = run('b27' + name[0], play, length, hold)
    st = strums(fr)
    full = max(lv(f, 0) for f in fr[st[0][0]:])
    damped = restored = True
    waits = []
    for t0, ons in st[1:]:
        for v, b in ons.items():
            if b - t0 > 8:                              # a string that waits longer than the fade
                waits.append(b - t0)
                damped &= all(lv(fr[x], v) == 0 for x in range(t0 + 6, b))
            restored &= lv(fr[b], v) >= full * 4 // 5
    check(len(st[1][1]) == NV and waits and damped, f'{name}: every waiting string is silent from 6 blocks after the strum starts until its turn (waits {sorted(set(waits))} blocks)')
    check(restored, f'{name}: at its note-on every string is back at its level (full {full:#06x})')
    first = all(lv(fr[x], v) >= full * 4 // 5 for v, b in st[0][1].items() for x in range(max(b, RAMP), st[1][0] - 1))   # (image 34: the next strum is worked out, and damps, a block before its first note-on)
    check(first, f'{name[0]} (E): the first strum and the time up to the next: every sounding voice at its level (within 80 % of full)')

fr = run('b27D', 0, 30, 1)
st = strums(fr)
full = max(lv(f, 0) for f in fr[st[0][0]:])
low = min(lv(f, v) for f in fr[RAMP:] for v in range(NV))
check(low >= full * 4 // 5, f'D CHRD HOLD on: no voice\'s level ever drops (lowest {low:#06x} of {full:#06x})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
