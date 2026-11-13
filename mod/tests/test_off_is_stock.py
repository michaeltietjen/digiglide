"""DigiGlide off is stock: with no DigiGlide sound switched on, every byte the ColdFire sends the DSP is stock's.
  A  the demo project plays on all 16 tracks, nothing touched: 3000 frames, all 2688 bytes each, identical to stock.
  B  track 1 is a WAVETONE sound carrying DigiGlide's parameters with VCNT OFF (a DigiGlide sound switched off), with
     trigs, the demo playing on the others: all frames identical to stock given the same sound.
  C  keys played by hand on that switched-off track (keyboard mode): the same notes on the same voices as stock, and
     no DigiGlide chord event.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_off_is_stock.py [DIGIGLIDE.syx]"""
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


def same(a, b):
    bad = [(i, [o for o in range(len(x)) if x[o] != y[o]][:6]) for i, (x, y) in enumerate(zip(a, b)) if bytes(x) != bytes(y)]
    return len(a) == len(b) and not bad, bad[:3]


def demo(image, tag, off_sound):
    s = Session(image, tag='os_' + tag + ('_dg' if image else '_st'), solo=False, reserve=0)
    if off_sound:
        s.set_sound(Ui(hold=1, glid=3), on=False)
        for st, n in ((0, 60), (4, 64), (8, 67), (12, 72)):
            s.trig(st, note=n, length=20)
    fr = s.play(3000, bpm=120)
    return s, fr


_, a_st = demo(None, 'a', False)
sa, a_dg = demo(img, 'a', False)
r, bad = same(a_st, a_dg)
check(r, f'A: the demo project, nothing touched: {len(a_dg)} frames byte-identical to stock (first differences {bad})')
check(sa.k.h.u32(sa.sym['DG'] + 4) == 0, 'A: no DigiGlide chord event')
_, b_st = demo(None, 'b', True)
sb, b_dg = demo(img, 'b', True)
r, bad = same(b_st, b_dg)
check(r, f'B: a DigiGlide sound with VCNT OFF on track 1, with trigs: {len(b_dg)} frames byte-identical to stock (first differences {bad})')
check(sb.k.h.u32(sb.sym['DG'] + 4) == 0, 'B: no DigiGlide chord event')


def keys(image):
    s = Session(image, tag='os_c' + ('_dg' if image else '_st'), solo=True, reserve=0)
    s.set_sound(Ui(hold=1, glid=3), on=False)
    s.k.tap('KEYB')
    h = s.k.h
    ev = []
    for mask in (0x01, 0x04, 0x10, 0x05, 0x00):
        st = len(h.sent)
        h.pc = panelin.buttons(h.m, h.profile, 3, mask); h.run(3_000_000); h.frames(400)
        seg = [f for f, _ in h.sent[st:]]
        ev.append(([(U16(f, 0x22), [U16(f, 2 + 2 * v) >> 8 for v in range(16) if U16(f, 0x22) >> v & 1]) for f in seg if U16(f, 0x22)],
                   [U16(f, 0x24) for f in seg if U16(f, 0x24)]))
    return s, ev


_, c_st = keys(None)
sc, c_dg = keys(img)
check(c_st == c_dg and any(e[0] for e in c_st), f'C: keys by hand on the switched-off track: the same note-ons and note-offs as stock ({c_dg})')
check(sc.k.h.u32(sc.sym['DG'] + 4) == 0, 'C: no DigiGlide chord event')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
