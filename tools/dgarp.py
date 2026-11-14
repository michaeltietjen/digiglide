#!/usr/bin/env python3
"""Watch the stock arp on DigiGlide's track over the read-only probe (OS 1.12) for N seconds: the playhead, the arp's
note set and state, the keys DigiGlide gave it (arp_key), the in / out counters and the track's note-ons in the
frame. Prints a line whenever something changes. An existing OUT is never overwritten.
    python3 dgarp.py SECONDS OUT.jsonl [TRACK 1..16]"""
import json, os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dgprobe

FRAME, PLAY, HEADS, ARP_SET, ARP_ST, SOUNDS = 0x80005E60, 0x42C5B994, 0x446493D0, 0x40599728, 0x405994A8, 0x800052A0
out, k = sys.argv[2], 1
while os.path.exists(out):
    k += 1
    out = '%s-%d%s' % (os.path.splitext(sys.argv[2])[0], k, os.path.splitext(sys.argv[2])[1])
pr = dgprobe.Probe('Digitone II')
h = pr.hello()
s = dgprobe.symbols(os.path.expanduser('~/dn2-workspace/build'), h['tag'], '1.12')
dg = pr.peek(s['DG'], 56)
t = int(sys.argv[3]) - 1 if len(sys.argv) > 3 else struct.unpack('>i', dg[48:52])[0]
snd = struct.unpack('>I', pr.peek(SOUNDS, 4))[0]
modes = [pr.peek(snd + 52 + 1163 * i + 351, 1)[0] for i in range(16)]
print('arp MODE per track:', modes)
if len(sys.argv) <= 3 and any(modes):
    t = [i for i, m in enumerate(modes) if m][0]
print('unit', h, 'track (from 0)', t)
if snd:
    print('sound +348..+360:', pr.peek(snd + 52 + 1163 * t + 348, 13).hex(' '), ' +374:', pr.peek(snd + 52 + 1163 * t + 374, 1).hex())
bits = lambda b: [32 * w + i for w in range(4) for i in range(32) if struct.unpack_from('>I', b, 4 * w)[0] >> i & 1]
t0, last, n = time.time(), None, 0
with open(out, 'w') as f:
    while time.time() - t0 < float(sys.argv[1]):
        a = pr.peek(s['dg_arp_outs'], 8) + pr.peek(s['arp_key'] + 36 * t, 36)
        st = pr.peek(ARP_ST + 40 * t, 40)
        aset = bits(pr.peek(ARP_SET + 16 * t, 16))
        head = pr.peek(HEADS + t, 1)[0]
        fr = pr.peek(FRAME, 0x30)
        outs, ins = struct.unpack('>II', a[:8])
        keys = [(a[8 + 9 * i], list(a[10 + 9 * i:10 + 9 * i + a[9 + 9 * i]])) for i in range(4) if a[9 + 9 * i]]
        rec = dict(t=round(time.time() - t0, 3), step=head, ins=ins, outs=outs, set=aset, keys=keys, last=st[12:16].hex(),
                   arpstep=st[:4].hex(), play=pr.peek(PLAY, 4)[3], dgtrigs=struct.unpack('>I', pr.peek(s['DG'] + 4, 4))[0])
        f.write(json.dumps(rec) + '\n')
        n += 1
        key = (ins, outs, tuple(aset), str(keys))
        if key != last:
            print('%6.2f step %3d ins %d outs %d set %s keys %s last note %s dg events %d' % (rec['t'], head + 1, ins, outs, aset, keys, rec['last'], rec['dgtrigs']))
            last = key
print(n, 'samples ->', out)
