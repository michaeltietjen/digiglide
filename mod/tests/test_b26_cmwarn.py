"""Build 26: "CHORD MODE ON?" shows once a track until power off (owner: "keeps popping up").
  A  three keys at once on track 1: the message shows, and track 1's bit in dg_cmwarn is set.
  B  the message gone (2600 blocks, longer than its 2000), three keys again: it does not show again,
     and DigiGlide still plays the chord (note-ons on its voices).
  C  one key alone never shows it (a fresh session).
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b26_cmwarn.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, U16, Ui
from emu import panelin

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
TEXT = b'CHORD MODE ON?'


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def live(tag):
    s = Session(img, tag=tag, solo=True, reserve=0)
    s.set_sound(Ui(voic=64, glid=0, drft=0, vib=0, hold=0))
    for _ in range(3):
        s.k.tap('SYN')
    s.k.tap('KEYB')
    s.k.h.w(s.sym['dg_cmwarn'], bytes(2)) if 'dg_cmwarn' in s.sym else None
    s.k.h.frames(2200)                                   # set-up's own message (2000 blocks) has gone
    s.k.h.w(s.sym['dg_msg'], bytes(28))
    return s


def press(s, mask, frames=400):
    h = s.k.h
    st = len(h.sent)
    h.pc = panelin.buttons(h.m, h.profile, 3, mask); h.run(3_000_000)
    h.frames(frames)
    return [x for x, _ in h.sent[st:]]


msg = lambda s: bytes(s.k.h.r(s.sym['dg_msg'], 28)).split(b'\0')[0]
warn = lambda s: (int.from_bytes(bytes(s.k.h.r(s.sym['dg_cmwarn'], 2)), 'big') if 'dg_cmwarn' in s.sym else None)
ons = lambda fr: [i for i, f in enumerate(fr) if U16(f, 0x22)]

# ---------------------------------------------------------------- A, B
s = live('b26_ab')
a = press(s, 0x15, 1200)
check(msg(s) == TEXT and warn(s) == 1, f'A: three keys at once: the message shows ({msg(s)!r}), dg_cmwarn {warn(s)}')
press(s, 0x00, 2600)
s.k.h.w(s.sym['dg_msg'], bytes(28))
b = press(s, 0x15, 1200)
check(msg(s) != TEXT, f'B: three keys again after it went: it does not show again ({msg(s)!r})')
check(ons(a) and ons(b), f'B: both times DigiGlide plays the chord (note-ons at {ons(a)[:1]} and {ons(b)[:1]})')
press(s, 0x00)

# ---------------------------------------------------------------- C
s = live('b26_c')
press(s, 0x01); press(s, 0x00)
check(msg(s) != TEXT and not warn(s), f'C: one key alone: no message ({msg(s)!r}), dg_cmwarn {warn(s)}')

print('OK' if ok else 'FAIL')
