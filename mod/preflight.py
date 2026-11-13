"""Preflight for a built DigiGlide image: the rules of dnfw v0.50's safety check, taken against the stock file of the
OS being built (dnfw's own `check` knows 1.11 only). build_dg.py runs this on every image; an image that fails is
renamed <name>.syx.FAILED so it cannot be picked up for flashing.
    python preflight.py IMAGE.syx [...]"""
import hashlib, os, sys
from dnfw.firmware.load import load
from dnfw.firmware.verify import verify
import osver

USB_BUFFER = 0x200000        # the unit's USB upgrade buffer
DSP_MAX = 1 << 20            # the DSP upload
OURS = (3, 7)                # sections a mod may change (ColdFire image, DSP image); DigiGlide changes 3 only


def usb_bytes(syx):
    n = i = 0
    while True:
        i = syx.find(b'\xf0', i)
        if i < 0:
            return n * 101
        if i + 6 < len(syx) and syx[i + 6] == 0x7E:
            n += 1
        i += 1


def check(path, quiet=False):
    sb = open(osver.STOCK_SYX, 'rb').read()
    res = [('stock file is ' + osver.OS, hashlib.sha256(sb).hexdigest() == osver.STOCK_SHA256, '')]
    s = load(sb).container
    bb = open(path, 'rb').read()
    fw = load(bb)
    b = fw.container
    res.append(('product, version, build as stock', (b.product, b.version, b.build) == (s.product, s.version, s.build), f'{b.product} {b.version} {b.build}'))
    ids = tuple(x.id for x in b.sections)
    res.append(('sections and their order as stock', ids == tuple(x.id for x in s.sections), str(ids)))
    n = usb_bytes(bb)
    res.append(('fits the 2 MiB USB upgrade buffer', 0 < n <= USB_BUFFER, f'{n:,} bytes, {USB_BUFFER - n:,} spare'))
    sid = {x.id: x for x in s.sections}
    for x in b.sections:
        same = x.id in sid and x.raw_payload == sid[x.id].raw_payload
        if x.id in OURS:
            res.append((f'section {x.id}', True, 'identical to stock' if same else 'changed (expected)'))
        else:
            res.append((f'section {x.id} untouched', same, ''))
    d = b.find(7)
    n7 = len(d.unpack())
    res.append(('DSP image fits its 1 MiB upload', n7 < DSP_MAX and len(d.raw_payload) <= DSP_MAX, f'{n7:,} bytes'))
    r = verify(fw)
    bad = [c.name for c in r.checks if not c.ok]
    res.append(('integrity checks', not bad, f'{len(r.checks) - len(bad)}/{len(r.checks)} {bad or ""}'))
    res.append(('signed', fw.key is not None, ''))
    ok = all(o for _, o, _ in res)
    if not quiet or not ok:
        print('preflight', os.path.basename(path), 'PASS' if ok else 'FAIL')
        for nm, o, dt in res:
            print('   [ok ]' if o else '   [BAD]', nm, dt)
    return ok


if __name__ == '__main__':
    sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
    sys.exit(0 if all([check(p) for p in sys.argv[1:]]) else 1)
