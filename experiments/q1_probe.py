import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import dn2paths as P; os.chdir(P.DIGIKIT); import cfkit
k = cfkit.Kit(str(P.SEC3_STOCK), str(P.STOCK), None, str(P.BUILD / 'stock_emu'))
app = k.call(0x4018A97A); ctx = k.call(0x4003EFDE, [app])
b = bytes(k.h.uc.mem_read(ctx + 0x478, 24)) if hasattr(k.h, 'uc') else None
print('ctx', hex(ctx), 'bytes ctx+0x478..:', b.hex(' ') if b else 'n/a')
print([a for a in dir(k.h) if not a.startswith('_')][:60])
