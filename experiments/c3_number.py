"""M0 wrap-up: which MIDI number does the Digitone II call C3?

Sets the TRIG page NOTE default through the stock setter 0x4004ec38(ctx, value), screenshots the TRIG page,
then plays one trig on track 1 and reads the note word the OS sends to the DSP (frame +0x02+2v, note << 8).
Earlier (q2_note_word.py) the DSP played note word 60 at 261.6 Hz, so the frame value is the MIDI note number.
    $DIGIKIT/.venv/bin/python c3_number.py
"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import dn2paths as P
OUT = os.path.expanduser('~/glide/experiments/out/c3')
os.chdir(P.DIGIKIT)
import cfkit

for value in (48, 60):
    k = cfkit.Kit(str(P.SEC3_STOCK), str(P.STOCK), None, str(P.BUILD / 'stock_emu'))
    k.h.out = OUT
    app = k.call(0x4018A97A)
    ctx = k.call(0x4003EFDE, [app])
    k.call(0x4004EC38, [ctx, value])
    vt = k.h.u32(ctx); words = k.call(k.h.u32(vt + 40), [ctx])
    stored = k.h.r(words + 0x485, 1)[0]
    k.tap('TRIG')
    k.h.png(f'trig_page_note{value}.png')
    print(f'set {value}: default byte {stored}, screenshot {OUT}/trig_page_note{value}.png')
