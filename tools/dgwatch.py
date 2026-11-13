#!/usr/bin/env python3
"""Sample a DigiGlide unit over the read-only probe for N seconds and save every sample (tools/dgprobe.py's transport).
Per sample: DG (208 bytes), the frame's head (notes, masks, velocity, level, machine: 0xda bytes), the sound records of
voices 0 and 1 as the frame carries them, the voice -> track map, the play flag.
    python3 dgwatch.py SECONDS OUT.jsonl"""
import json, os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dgprobe

FRAME, PLAY = 0x80005E60, int(sys.argv[3], 0) if len(sys.argv) > 3 else 0
pr = dgprobe.Probe('Digitone II')
h = pr.hello()
s = dgprobe.symbols(os.path.expanduser('~/dn2-workspace/build'), h['tag'], '1.12')
t0, n = time.time(), 0
with open(sys.argv[2], 'w') as f:
    while time.time() - t0 < float(sys.argv[1]):
        rec = {'t': round(time.time() - t0, 3), 'dg': pr.peek(s['DG'], 208).hex(), 'head': pr.peek(FRAME, 0xda).hex(),
               'v0': pr.peek(FRAME + 0xda, 292).hex(), 'vt': pr.peek(FRAME + 0xa5a, 32).hex(),
               'name': pr.peek(s['dg_name'], 16).split(b'\0')[0].decode('ascii', 'replace')}
        if PLAY:
            rec['play'] = pr.peek(PLAY, 4).hex()
        f.write(json.dumps(rec) + '\n')
        n += 1
print(n, 'samples in', round(time.time() - t0, 1), 's')
