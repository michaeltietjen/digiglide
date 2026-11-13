"""DigiGlide: the [FUNC] + push-E shortcut on the demo's track 1 (WAVETONE, stock values: 0x4000 in slot 54)."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest
OUT = os.path.expanduser('~/glide/experiments/out/m4')
s = Session(latest(), tag='shortcut', solo=False)
k = s.k; h = k.h; h.out = OUT
print('machine', k.mach(0), 'VCNT stored', hex(s.vcnt()), '-> on?', s.k.call(s.sym['dg_test_read'], [0, 0]) >> 16)
s.syn_page(3); h.png('sc_0_harmony_off.png')
s.shortcut(); h.png('sc_1_on_message.png'); print('after shortcut: VCNT', hex(s.vcnt()))
h.run(400_000_000); h.frames(2200); h.run(100_000_000); h.png('sc_2_after_message.png')
s.shortcut(); h.png('sc_3_off_message.png'); print('after shortcut: VCNT', hex(s.vcnt()))
