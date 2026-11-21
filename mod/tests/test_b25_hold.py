"""Build 25: turning HOLD off lets a held chord go (owner: "stuck on hold").
  A  HOLD on, a key played and released: the chord keeps sounding; HOLD turned off in the store: it releases.
  B  HOLD turned off while the key is still down: the chord sounds on, and releases when the key comes up.
  C  [FUNC] + push H turns HOLD off with a chord held: it releases.
  D  HOLD on again: the next key's chord is held again after the key comes up.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b25_hold.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, U16, Ui
from emu import panelin

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def voices_of(s, t):
    k = s.k
    cfg = s.app + 244 + 17092
    data = k.call(k.h.u32(k.h.u32(cfg) + 40), [cfg])
    return k.h.r(data + 5 * t + 1, 1)[0], sum(k.h.r(data + 5 * j + 1, 1)[0] for j in range(t))


def live(tag):
    s = Session(img, tag=tag, solo=True, reserve=0)
    s.set_sound(Ui(voic=64, glid=0, drft=0, vib=0, hold=1))
    for _ in range(3):
        s.k.tap('SYN')
    s.k.tap('KEYB')
    return s


def press(s, mask, frames=400):
    h = s.k.h
    st = len(h.sent)
    h.pc = panelin.buttons(h.m, h.profile, 3, mask); h.run(3_000_000)
    h.frames(frames)
    return [x for x, _ in h.sent[st:]]


def run(s, frames=400):
    h = s.k.h
    st = len(h.sent)
    h.frames(frames)
    return [x for x, _ in h.sent[st:]]


def offs(s, fr):
    have, base = voices_of(s, 0)
    m = ((1 << have) - 1) << base
    return [i for i, f in enumerate(fr) if U16(f, 0x24) & m]


def ons(s, fr):
    have, base = voices_of(s, 0)
    m = ((1 << have) - 1) << base
    return [i for i, f in enumerate(fr) if U16(f, 0x22) & m]


HOLD = 94
# ---------------------------------------------------------------- A
s = live('b25_a')
a = press(s, 0x01); b = press(s, 0x00)
check(ons(s, a) and not offs(s, a) and not offs(s, b), 'A: HOLD on: the key comes up, the chord keeps sounding')
s.k.slot(0, HOLD, 0x200)
c = run(s)
check(offs(s, c), f'A: HOLD turned off: the held chord releases (note-off at frame {offs(s, c)[:1]})')

# ---------------------------------------------------------------- B
s = live('b25_b')
a = press(s, 0x01)
s.k.slot(0, HOLD, 0x200)
b = run(s)
c = press(s, 0x00)
check(ons(s, a) and not offs(s, b), 'B: HOLD off with the key still down: the chord sounds on')
check(offs(s, c), 'B: the key comes up: the chord releases')

# ---------------------------------------------------------------- C
s = live('b25_c')
a = press(s, 0x01); b = press(s, 0x00)
k, h = s.k, s.k.h
st = len(h.sent)
s._btn(2, 0x01, 500_000); s._btn(5, 0x80, 500_000); s._btn(5, 0x00, 15_000_000); s._btn(2, 0x00, 15_000_000)
h.frames(400)
c = [x for x, _ in h.sent[st:]]
check(not offs(s, b) and k.slot(0, HOLD) == 0x200 and offs(s, c), f'C: [FUNC] + push H turns HOLD off ({k.slot(0, HOLD):#06x}) with a chord held: it releases')

# ---------------------------------------------------------------- D
k.slot(0, HOLD, 0x300)
d = press(s, 0x04); e = press(s, 0x00); f = run(s, 800)
check(ons(s, d) and not offs(s, e) and not offs(s, f), 'D: HOLD on again: the next chord is held after the key comes up')

print('OK' if ok else 'FAIL')
