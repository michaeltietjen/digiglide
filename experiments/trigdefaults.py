import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import dn2paths as P; os.chdir(P.DIGIKIT); import cfkit
k = cfkit.Kit(str(P.SEC3_STOCK), str(P.STOCK), None, str(P.BUILD / 'stock_emu'))
app = k.call(0x4018A97A); ctx = k.call(0x4003EFDE, [app])
vt = k.h.u32(ctx); words = k.call(k.h.u32(vt + 40), [ctx])
print('ctx', hex(ctx), 'words', hex(words))
print('words+0x478:', bytes(k.h.uc.mem_read(words + 0x478, 24)).hex(' '))
print('first steps:', bytes(k.h.uc.mem_read(words, 32)).hex(' '))
