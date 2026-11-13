"""Build GLIDE: python3 build.py [-o OUT.syx] [-D NAME=VALUE ...]
Default output: $DN2_WORKSPACE/build/DN2_1.11_GLIDE_<N>.syx (next free N: never overwrites an older build)."""
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import cfmod, dn2paths as P

ap = argparse.ArgumentParser()
ap.add_argument('-o')
ap.add_argument('-D', action='append', default=[])
a = ap.parse_args()
out = a.o
if not out:
    n = 1
    while (P.BUILD / f'DN2_1.11_GLIDE_{n}.syx').exists():
        n += 1
    out = str(P.BUILD / f'DN2_1.11_GLIDE_{n}.syx')
defs = dict(d.split('=', 1) for d in a.D)
m = cfmod.Mod([os.path.join(HERE, f) for f in ('glide.c', 'voicelead.c', 'hooks.S')],
              entries=['glide_stub', 'glide_tx', 'G', 'glide_seq', 'glide_seq_n'], init='glide_init', include=[HERE], defines=defs)
m.context(0x40025E88, '6620', 'bnes right after the hooked move: reads its flags (the stub replays the move last)')
m.context(0x40025E94, '487980005e60', 'the frame the driver sends right after: 0x80005e60')
m.jsr(0x40025E82, 'glide_stub', stock='2039402876f8', why='audio ISR: before the frame goes to the DSP -> glide_tx')
m.write(out)
print(out)
