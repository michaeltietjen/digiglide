"""Q1: with track 1 reserving 4 voices, which voices does it use over several trigs, and do other tracks avoid them?"""
import os, struct, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import dn2paths as P; os.chdir(P.DIGIKIT); import cfkit
U16 = lambda f, o: struct.unpack_from('>H', f, o)[0]
for reserve in (0, 4):
    k = cfkit.Kit(str(P.SEC3_STOCK), str(P.STOCK), None, str(P.BUILD / 'stock_emu'))
    app = k.call(0x4018A97A); cfg = k.call(0x40030AF8, [k.call(0x4003E41A, [app])])
    data = k.call(k.h.u32(k.h.u32(cfg) + 40), [cfg])            # vtable[40](cfg) -> per-track 5-byte records
    k.call(0x40029094, [cfg, 0, reserve])                       # stock setter: clamp, write, notify
    ctx0 = k.call(0x4003EFDE, [app])
    for st in range(0, 16, 2):                                  # track 1: a trig every other step
        k.call(0x40054690, [ctx0, st, 1, 1])
    for t in (1, 2, 3):                                         # tracks 2-4: trigs on every step
        for st in range(16):
            k.call(0x40054690, [ctx0 + 132 * t, st, 1, 1])
    print(f'reserve={reserve}: free pool now', k.call(0x40028FFC, [cfg]), ' track1 reserve', k.call(0x40029054, [cfg, 0]))
    fr = k.play(700, bpm=240)
    use = {}
    for f in fr:
        on = U16(f, 0x22)
        for v in range(16):
            if on >> v & 1:
                use.setdefault(U16(f, 0xA5A + 2 * v), []).append(v)
    for t in sorted(use):
        print(f'   track {t+1}: voices {sorted(set(use[t]))}  ({len(use[t])} note-ons)')
