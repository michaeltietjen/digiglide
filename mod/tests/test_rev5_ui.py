"""DigiGlide rev 5 pages: [SYN] reaches CHORD, MOTION and SETUP after WAVETONE's own three; the pages show the
sounding chord's name; knob A on CHORD turns TYPE; [FUNC] + push encoder E switches DigiGlide, [FUNC] + push encoder H
switches HOLD. Screenshots: ~/glide/renders/rev5/page_chord.png, page_motion.png, page_setup.png, page_chord_name.png.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_rev5_ui.py [DIGIGLIDE.syx]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16
from emu import panelin

img = sys.argv[1] if len(sys.argv) > 1 else latest()
OUT = os.path.expanduser('~/glide/renders/rev5')
os.makedirs(OUT, exist_ok=True)
print('image', os.path.basename(img))
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


s = Session(img, tag='r5_ui', solo=True, reserve=0)
k, h = s.k, s.k.h
h.out = OUT
s.set_sound(Ui(type=1, ext=2, key=0, hold=1, glid=3, drft=0, vib=0))
k.tap('SYN'); h.frames(2200)                             # (let the "VOICES SET TO 5" message time out: 1.3 s of audio)
seen = []
for _ in range(8):
    k.tap('SYN')
    seen.append(s.drawn_page())
check({3, 4, 5} <= set(seen), f'[SYN] reaches the three DigiGlide pages after WAVETONE\'s own (pages drawn {seen})')
for page, name in ((3, 'chord'), (4, 'motion'), (5, 'setup')):
    check(s.syn_page(page), f'{name.upper()} reached')
    h.png(f'page_{name}.png')
s.syn_page(3)
slot = lambda sl: k.slot(0, sl)
for burst in (11, 11, 7):
    if h.turn_to(0, lambda: slot(50) >> 8, 3, burst=burst, tries=80):
        break
check(slot(50) == 3 << 8, f'knob A on CHORD turns TYPE: slot 50 = {slot(50):#06x} (DIM)')
h.frames(300); h.run(400_000_000)                        # (let the emulator's queued knob turns drain first)
k.slot(0, 50, 1 << 8)
k.tap('KEYB')
for _ in range(4):                                       # (the emulator's panel can deliver a key late: wait for it)
    h.pc = panelin.buttons(h.m, h.profile, 3, 0x01); h.run(3_000_000); h.frames(400)
    h.pc = panelin.buttons(h.m, h.profile, 3, 0x00); h.run(3_000_000); h.frames(400)
    if s.chord_name(0):
        break
k.tap('KEYB')
s.syn_page(3)
h.frames(2200); s.syn_page(4); s.syn_page(3)
nm = s.chord_name(0)
print(f'      TYPE slot when the chord was named: {slot(50):#06x}')
h.png('page_chord_name.png')
check(nm.endswith('MIN7'), f'a held chord is named on the page: "{nm}"')
v0 = slot(54)
s.shortcut(); off = slot(54)
s.shortcut(); on = slot(54)
check(v0 == 3 << 8 and off == 0 and on == 3 << 8, f'[FUNC] + push E: VCNT {v0:#06x} -> {off:#06x} -> {on:#06x}')
h0 = slot(94)
s._btn(2, 0x01, 500_000); s._btn(5, 0x80, 500_000); s._btn(5, 0x00, 15_000_000); s._btn(2, 0x00, 15_000_000)
check(h0 == 0x0300 and slot(94) == 0x0200, f'[FUNC] + push H: HOLD on {h0:#06x} -> off {slot(94):#06x}')
print('screenshots:', OUT)
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
