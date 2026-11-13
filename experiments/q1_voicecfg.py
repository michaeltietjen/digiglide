import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import dn2paths as P; os.chdir(P.DIGIKIT); import cfkit
k = cfkit.Kit(str(P.SEC3_STOCK), str(P.STOCK), None, str(P.BUILD / 'stock_emu'))
app = k.call(0x4018A97A); kit = k.call(0x4003E41A, [app]); cfg = k.call(0x40030AF8, [kit])
s = lambda v: v - (1 << 32) if v >= 1 << 31 else v
print('global 0x40028ffc:', s(k.call(0x40028FFC, [cfg])))
for t in range(16):
    print(f'track {t+1:2d}: 9054={s(k.call(0x40029054,[cfg,t]))} 920e={s(k.call(0x4002920E,[cfg,t]))} '
          f'938c={s(k.call(0x4002938C,[cfg,t]))} 944a={s(k.call(0x4002944A,[cfg,t]))}')
