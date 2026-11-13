"""Stock 1.11: does [FUNC] + <button> change any state? FUNC held, the button (group, bit) pressed and released,
FUNC released; diffed against a control run with the same emulated time and no keys. Regions: the app object, the 16
live sounds, the arp state, the playing pattern, and the screen."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session
from emu import panelin


def regions(h):
    app = h.u32(0x446478D0); snd = h.u32(0x800052A0); pat = h.u32(0x42C5A9A0); scr = h.u32(0x402A0B8C)
    return {'app': (app, 451596), 'sounds': (snd, 52 + 1163 * 16), 'arp': (0x405984A8, 640), 'pattern': (pat, 131072),
            'screen': (scr, 1024)}


PAGE = os.environ.get('PAGEKEY', 'SYN')


def run(tag, button):
    s = Session(None, tag='funcany_' + PAGE + tag, solo=False)
    k = s.k; h = k.h
    k.tap(PAGE); h.frames(10)
    if button:
        g, b = button
        h.pc = panelin.press(h.m, h.profile, 2, 0); h.run(500_000); h.frames(20)
        h.pc = panelin.press(h.m, h.profile, g, b, 1 if g == 2 else 0); h.run(500_000); h.frames(20)
        h.pc = panelin.release(h.m, h.profile, g, b, 1 if g == 2 else 0); h.run(15_000_000); h.frames(20)
        h.pc = panelin.release(h.m, h.profile, 2, 0); h.run(15_000_000); h.frames(20)
    else:
        h.run(500_000); h.frames(20); h.run(500_000); h.frames(20); h.run(15_000_000); h.frames(20)
        h.run(15_000_000); h.frames(20)
    h.run(100_000_000)
    return {n: bytes(h.r(a, ln)) for n, (a, ln) in regions(h).items()}


ctl = run('control', None)
for spec in sys.argv[1:]:
    g, b = map(int, spec.split(','))
    got = run(f'{g}_{b}', (g, b))
    diffs = {n: sum(1 for x, y in zip(ctl[n], got[n]) if x != y) for n in ctl}
    print(f'{PAGE} page: FUNC + ({g},{b}):', ', '.join(f'{n} {c}' for n, c in diffs.items()), '-> UNUSED' if not any(diffs.values()) else '')
