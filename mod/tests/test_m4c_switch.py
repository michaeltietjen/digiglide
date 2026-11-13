"""DigiGlide M4 switch (owner's decision, 2026-11-10): VCNT is the switch (OFF, 3, 4, 5, 6; OFF stored as 0 and the
default; only the exact on-codes 0x0100..0x0400 turn DigiGlide on), plus the [FUNC] + push-E shortcut.

  A. VCNT OFF on every track (the demo project as stock left it: its WAVETONE sounds hold 0x4000 in VCNT's slot):
     the frames the OS sends are byte-identical to stock's, and so are the DSP renders.
  B. The shortcut turns DigiGlide on (5 voices when the track had none), off, and back to the last voice count, with
     its messages on screen.
  C. The value survives stock's sound save and load: the converters a project's save and load run for every sound
     (0x400dd6a6 live -> stored, 0x400dd1ea stored -> live). ([FUNC] + [YES] / [FUNC] + [NO] did not reload any sound
     value in the emulator, stock's own amp volume included: experiments/m4_reload.py.)
  D. Without the combo the keys are stock's: [FUNC] alone, push E alone, [FUNC] + push D change nothing of
     DigiGlide's and leave the same screen and state as on stock.
  E. Toggling while a pattern plays: switching OFF mid-chord releases every DigiGlide voice (note-offs, no stuck note,
     no pitch jump); the next trig plays stock; switching on applies from the next trig.
  F. A p-lock to OFF on a step plays that trig as a stock note; the chord releases.
    ~/dn2-workspace/repos/digikit/.venv/bin/python test_m4c_switch.py [DIGIGLIDE.syx]
"""
import os, sys, struct, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, latest, G, U16, word, edges, SLOT_VCNT, panelin
from osver import A
import dn2paths as P

img = sys.argv[1] if len(sys.argv) > 1 else latest()
OUT = os.path.expanduser('~/glide/renders/M4')
print('image', os.path.basename(img))
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg)


def msg_until(s):
    b = bytes(s.k.h.r(s.sym['DG'], 96))
    return struct.unpack_from('>I', b, 72)[0]       # DG.msg_until (after ctl, stock_trigs, combo_was, combo_req)


# ---------------------------------------------------------------- A: OFF everywhere = stock
runs = {}
for name, im in (('stock', None), ('digiglide', img)):
    s = Session(im, tag='m4c_A', solo=False)       # the demo project as it loads, every track playing
    runs[name] = s.play(3000, bpm=120)
    if im:
        vc = [s.vcnt(t) for t in range(16) if s.k.mach(t) == 1]
        dgt = s.dg()['trigs']
a, b = runs['stock'], runs['digiglide']
same = len(a) == len(b) and all(x == y for x, y in zip(a, b))
first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
check(same, f'A: VCNT OFF everywhere (WAVETONE tracks store {sorted(set(hex(v) for v in vc))} in VCNT\'s slot): '
            f'{len(a)} frames byte-identical to stock' + ('' if same else f' (first difference at frame {first})'))
check(dgt == 0, f'A: no DigiGlide trig ({dgt})')
import dn2frame as D
sec7, snap = P.snap('stock')
ra = D.render(D.Frame(D.image_from_sec7(sec7), snap), [D.swap16(bytes(f[:2688])) for f in a[:1500]])
rb = D.render(D.Frame(D.image_from_sec7(sec7), snap), [D.swap16(bytes(f[:2688])) for f in b[:1500]])
check(np.array_equal(np.asarray(ra[0]), np.asarray(rb[0])) and np.array_equal(np.asarray(ra[1]), np.asarray(rb[1])),
      f'A: DSP renders of the first 1500 frames bit-identical (rms {float(np.sqrt(np.mean(np.asarray(ra[0], float) ** 2))):.4f})')

# ---------------------------------------------------------------- B, C, D: the shortcut, save / reload, the keys alone
s = Session(img, tag='m4c_B', solo=False)
k, h = s.k, s.k.h
h.out = OUT
check(k.mach(0) == 1 and s.vcnt() == 0x4000, f'B: track 1 is WAVETONE with stock\'s {s.vcnt():#06x} in VCNT\'s slot: OFF')
s.syn_page(3)
s.shortcut()
h.png('switch_on_message.png')
check(s.vcnt() == 0x300 and msg_until(s), f'B: shortcut -> VCNT {s.vcnt():#06x} (5 voices, no count before), message')
h.run(300_000_000); h.frames(2200); h.run(60_000_000)
check(not msg_until(s), 'B: the message clears after about 1.3 s')
s.shortcut()
h.png('switch_off_message.png')
check(s.vcnt() == 0, f'B: shortcut again -> OFF (stored {s.vcnt():#06x})')
k.slot(0, SLOT_VCNT, 0x200)                            # 4 voices, as the knob would set it
s.shortcut(); off = s.vcnt()
s.shortcut(); back = s.vcnt()
check(off == 0 and back == 0x200, f'B: from 4 voices: OFF ({off:#06x}), then back to 4 voices ({back:#06x})')

import cfkit
BUF = cfkit.SPARE + 0x10000
h.w(BUF, bytes(0x400))
k.call(A(0x400DD6A6), [BUF, k.sound(0), 0])               # stock's sound save
s.shortcut(); toggled = s.vcnt()
k.call(A(0x400DD1EA), [k.sound(0), BUF])                  # stock's sound load
on = k.call(s.sym['dg_test_read'], [0, 0]) >> 16
check(toggled == 0 and s.vcnt() == 0x200 and on, f'C: saved at 4 voices, switched OFF ({toggled:#06x}), loaded back: '
                                                f'{s.vcnt():#06x} (4 voices, DigiGlide on again)')
h.run(300_000_000); h.frames(2200); h.run(60_000_000)  # let the shortcut's message clear before D

before = s.vcnt()
for name, (g, mask) in (('FUNC alone', (2, 0x01)), ('push E alone', (5, 0x10))):
    h.pc = panelin.buttons(h.m, h.profile, g, mask); h.run(500_000); h.frames(12)
    h.pc = panelin.buttons(h.m, h.profile, g, 0); h.run(15_000_000); h.frames(12); h.run(40_000_000)
    check(s.vcnt() == before and not msg_until(s), f'D: {name}: VCNT unchanged ({s.vcnt():#06x}), no message')
s._btn(2, 0x01, 500_000); s._btn(5, 0x08, 500_000); s._btn(5, 0, 15_000_000); s._btn(2, 0, 15_000_000)
h.run(40_000_000)
check(s.vcnt() == before and not msg_until(s), 'D: [FUNC] + push D: nothing of DigiGlide\'s')


def keys_alone(im, tag):
    """[FUNC] alone, then push E alone, on the AMP page of the demo: the screen and state after, for stock vs mod."""
    s = Session(im, tag=tag, solo=False)
    k, h = s.k, s.k.h
    k.tap('AMP'); h.frames(10)
    for g, mask in ((2, 0x01), (5, 0x10)):
        h.pc = panelin.buttons(h.m, h.profile, g, mask); h.run(500_000); h.frames(12)
        h.pc = panelin.buttons(h.m, h.profile, g, 0); h.run(15_000_000); h.frames(12)
    h.run(100_000_000)
    app = h.u32(A(0x446478D0)); snd = h.u32(A(0x800052A0)); pat = h.u32(A(0x42C5A9A0)); scr = h.u32(A(0x402A0B8C))
    return [bytes(h.r(a_, n)) for a_, n in ((app, 451596), (snd, 52 + 1163 * 16), (pat, 131072), (scr, 1024))]


st, md = keys_alone(None, 'm4c_D'), keys_alone(img, 'm4c_D')
check(all(x == y for x, y in zip(st, md)), 'D: [FUNC] alone and push E alone on the AMP page: app, sounds, pattern '
                                          'and screen identical to stock')

# ---------------------------------------------------------------- E, F: while playing
BAR, STEP = 3000, 187.5


def dg_session(tag, locks=None):
    s = Session(img, tag=tag)
    s.set_sound(G.Params(key=0, scl=1, chrd=1, glid=5, vcnt=5))
    for st in (0, 16, 32, 48):
        s.trig(st, length=78)                          # 16 steps: one chord per bar, released at the bar's end
    for st, f in (locks or {}).items():
        s.lock(st, **f)
    return s


def gated_after(fr, upto):
    """voices whose last edge up to frame `upto` is a note-on (still gated)."""
    state = {}
    for i, f in enumerate(fr[:upto]):
        for v in range(6):
            if (U16(f, 0x22) >> v) & 1:
                state[v] = True
            if (U16(f, 0x24) >> v) & 1:
                state[v] = False
    return sorted(v for v, g in state.items() if g)


s = dg_session('m4c_E')
h = s.k.h
plan = {}
A_OFF, A_ON = 1500, int(1.5 * BAR)                      # OFF mid chord 1; ON between bar 2's and bar 3's trigs
for base, tag in ((A_OFF, 'off'), (A_ON, 'on')):
    plan.update({base: (2, 0x01), base + 3: (5, 0x10), base + 40: (5, 0), base + 45: (2, 0)})


def each(i):
    if i in plan:
        g, mask = plan[i]
        h.pc = panelin.buttons(h.m, h.profile, g, mask)


fr = s.play(4 * BAR + 600, bpm=120, each=each)
ons, offs = edges(fr)
d = s.dg()
off_blocks = [i for i in offs if A_OFF <= i < A_OFF + 400]
check(off_blocks and not gated_after(fr, off_blocks[-1] + 1),
      f'E: switched OFF mid-chord at ~{A_OFF}: note-offs at {off_blocks[:2]}, no DigiGlide voice left gated')
jump = max(abs(word(fr[i], v) - word(fr[i - 1], v)) / 256 for i in range(A_OFF, A_OFF + 600) for v in range(5))
check(jump < 0.2, f'E: no pitch jump while the chord releases (largest per-block change {jump:.3f} semitone)')
bar2 = [(i, [v for v in range(16) if (U16(fr[i], 0x22) >> v) & 1]) for i in range(BAR - 5, BAR + 300)
        if U16(fr[i], 0x22)]
check(bar2 and len(bar2[0][1]) == 1 and word(fr[bar2[0][0]], bar2[0][1][0]) == 60 << 8,
      f'E: the bar-2 trig plays stock: one note-on {bar2[:1]}, MIDI {word(fr[bar2[0][0]], bar2[0][1][0]) / 256 if bar2 else "-"}')
bar3 = [i for i in ons if 2 * BAR - 5 <= i < 2 * BAR + 300]
att3 = [v for v in range(6) if bar3 and (U16(fr[bar3[0]], 0x22) >> v) & 1]
check(len(att3) == 5, f'E: switched on before bar 3: its trig attacks a DigiGlide chord ({len(att3)} voices)')
check(not gated_after(fr, len(fr)), f'E: after STOP no voice is left gated (stuck): {gated_after(fr, len(fr))}')

s = dg_session('m4c_F', locks={16: dict(vcnt=0)})
fr = s.play(3 * BAR, bpm=120)
on2 = [(i, [v for v in range(16) if (U16(fr[i], 0x22) >> v) & 1]) for i in range(BAR - 5, BAR + 300) if U16(fr[i], 0x22)]
offs2 = [i for i in range(BAR - 5, BAR + 300) if U16(fr[i], 0x24) & 0x3F]
check(on2 and len(on2[0][1]) == 1 and word(fr[on2[0][0]], on2[0][1][0]) == 60 << 8 and offs2,
      f'F: VCNT p-locked OFF on step 17: one stock note-on {on2[:1]} at MIDI 60, the chord releases at {offs2[:1]}')
on3 = [i for i in range(2 * BAR - 5, 2 * BAR + 300) if U16(fr[i], 0x22) & 0x3F]
check(on3 and bin(U16(fr[on3[0]], 0x22) & 0x3F).count('1') == 5, 'F: step 33 (VCNT from the sound) is DigiGlide again')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
