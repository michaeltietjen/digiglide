#!/usr/bin/env python3
"""Sample the whole DSP frame buffer (0xC00 bytes) with DG, the play flag and the playheads for N seconds, over the
read-only probe (OS 1.12). Slower than dgwatch.py (a few samples a second): for values that stay, not for pulses.
An existing OUT is never overwritten.
    python3 dgframe.py SECONDS OUT.jsonl"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dgprobe

FRAME, PLAY, HEADS, SIZE = 0x80005E60, 0x42C5B994, 0x446493D0, 0xC00              # OS 1.12
out, k = sys.argv[2], 1
while os.path.exists(out):
    k += 1
    out = '%s-%d%s' % (os.path.splitext(sys.argv[2])[0], k, os.path.splitext(sys.argv[2])[1])
pr = dgprobe.Probe('Digitone II')
h = pr.hello()
s = dgprobe.symbols(os.path.expanduser('~/dn2-workspace/build'), h['tag'], '1.12')
t0, n = time.time(), 0
with open(out, 'w') as f:
    while time.time() - t0 < float(sys.argv[1]):
        rec = {'t': round(time.time() - t0, 3), 'play': pr.peek(PLAY, 4).hex(), 'heads': pr.peek(HEADS, 16).hex(),
               'dg': pr.peek(s['DG'], 208).hex(),
               'frame': b''.join(pr.peek(FRAME + o, 256) for o in range(0, SIZE, 256)).hex()}
        f.write(json.dumps(rec) + '\n')
        n += 1
print(n, 'samples in', round(time.time() - t0, 1), 's ->', out)
