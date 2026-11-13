import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import dn2paths as P; os.chdir(P.DIGIKIT); import cfkit
k = cfkit.Kit(str(P.SEC3_STOCK), str(P.STOCK), None, str(P.BUILD / 'stock_emu'))
pat = k.h.u32(0x42C5A9A0); D = pat + 0x1DD40
print('pattern', hex(pat), 'D+16..+28:', bytes(k.h.uc.mem_read(D + 16, 12)).hex(' '))
app = k.call(0x4018A97A); print('0x4003efa8(app) =', hex(k.call(0x4003EFA8, [app])))
