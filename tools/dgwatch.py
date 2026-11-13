#!/usr/bin/env python3
"""Sample a DigiGlide unit over the read-only probe for N seconds and save every sample (tools/dgprobe.py's transport).
Per sample: DG (208 bytes), the frame's head (notes, masks, velocity, level, machine: 0xda bytes), the sound records of
voices 0 and 1 as the frame carries them, the voice -> track map, the play flag, the playheads and the keys held.
An existing OUT is never overwritten: the next free OUT-2, OUT-3 ... is used. The last line says what was seen.
    python3 dgwatch.py SECONDS OUT.jsonl"""
import json, os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dgprobe

FRAME, PLAY, HEADS, KEYS = 0x80005E60, 0x42C5B994, 0x446493D0, 0x445A2E30         # OS 1.12
out, k = sys.argv[2], 1
while os.path.exists(out):
    k += 1
    out = '%s-%d%s' % (os.path.splitext(sys.argv[2])[0], k, os.path.splitext(sys.argv[2])[1])
seen = dict(trigs=set(), play=set(), names=set(), keys=0)
pr = dgprobe.Probe('Digitone II')
h = pr.hello()
s = dgprobe.symbols(os.path.expanduser('~/dn2-workspace/build'), h['tag'], '1.12')
t0, n = time.time(), 0
with open(out, 'w') as f:
    while time.time() - t0 < float(sys.argv[1]):
        rec = {'t': round(time.time() - t0, 3), 'dg': pr.peek(s['DG'], 208).hex(), 'head': pr.peek(FRAME, 0xda).hex(),
               'v0': pr.peek(FRAME + 0xda, 292).hex(), 'vt': pr.peek(FRAME + 0xa5a, 32).hex(),
               'name': pr.peek(s['dg_name'], 16).split(b'\0')[0].decode('ascii', 'replace')}
        rec['play'] = pr.peek(PLAY, 4).hex()
        rec['heads'] = pr.peek(HEADS, 16).hex()
        rec['keys'] = pr.peek(KEYS, 8).hex()
        seen['trigs'].add(rec['dg'][8:16]); seen['play'].add(rec['play']); seen['names'].add(rec['name'])
        seen['keys'] += any(bytes.fromhex(rec['keys']))
        f.write(json.dumps(rec) + '\n')
        n += 1
print(n, 'samples in', round(time.time() - t0, 1), 's ->', out)
print('seen: %d chord events, sequencer %s, keys held in %d samples, chords %s' % (
    len(seen['trigs']) - 1, 'played' if '00000001' in seen['play'] else 'never played', seen['keys'], sorted(seen['names'])))
