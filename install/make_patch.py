"""Make install/DigiGlide_<N>.dgpatch from a built image (the developer's side; a tester never runs this).

    python3 install/make_patch.py STOCK.syx BUILD_DIR/DN2_1.12_DIGIGLIDE_<N>.syx

The patch says how to make the built MAIN OS section from the stock one, as a list of two kinds of steps:
    copy   offset, length     bytes taken from the tester's own stock section
    data   bytes              bytes that are DigiGlide's (its compiled code, dnfw's loader, the changed hook sites)
The built section holds a copy of Elektron's parameter table (the build relocates it so it can grow). That copy,
like every other stretch of 16 bytes or more that the stock section also holds, becomes a copy step: the patch
carries its offset and length, never its bytes. The checks at the end fail the run if that is not so.
Needs the build's directory beside the .syx (section_3.bin, symbols.txt), as build_dg.py leaves it."""
import hashlib, json, os, struct, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'vendor'))
import pathlib
from dnfw.cli.files import read_image
from dnfw.firmware.load import load

MIN_COPY = 16                                # a stretch this long that stock also holds is copied, not carried
CODE_VA = 0x46800000
CHAIN = 192                                  # the build's aPLib match chain depth (zcache.py)


def sha(b):
    return hashlib.sha256(bytes(b)).hexdigest()


def find_copies(stock, index, new, lo, hi):
    """[lo, hi) of new -> steps; a stretch of MIN_COPY or more found in stock becomes a copy."""
    steps, i, lit = [], lo, lo
    while i < hi:
        best = (0, 0)
        if i + MIN_COPY <= hi:
            for at in index.get(new[i:i + 8], ()):
                n = 0
                while i + n < hi and at + n < len(stock) and stock[at + n] == new[i + n]:
                    n += 1
                if n > best[0]:
                    best = (n, at)
        if best[0] >= MIN_COPY:
            while i > lit and best[1] > 0 and stock[best[1] - 1] == new[i - 1]:     # (and backwards: the bytes before)
                i, best = i - 1, (best[0] + 1, best[1] - 1)
            if i > lit:
                steps.append(('data', new[lit:i]))
            steps.append(('copy', best[1], best[0]))
            i += best[0]
            lit = i
        else:
            i += 1
    if hi > lit:
        steps.append(('data', new[lit:hi]))
    return steps


def main(stock_path, built_path):
    raw = open(stock_path, 'rb').read()
    stock = bytes(load(read_image(pathlib.Path(stock_path))).container.find(3).unpack())
    d = built_path[:-4]
    new = open(os.path.join(d, 'section_3.bin'), 'rb').read()
    built = open(built_path, 'rb').read()
    build = os.path.basename(d).rsplit('_', 1)[-1]
    sym = {l.split()[1]: int(l.split()[0], 16) for l in open(os.path.join(d, 'symbols.txt'))}
    n = len(stock)
    assert len(new) > n
    steps, i, same = [], 0, 0
    while i < n:                             # the stock part: the same bytes are copied, changed ones are data
        j = i
        if stock[i] == new[i]:
            while j < n and stock[j] == new[j]:
                j += 1
            steps.append(('copy', i, j - i))
        else:
            while j < n and stock[j] != new[j]:
                j += 1
            steps.append(('data', new[i:j]))
            same += 1
        i = j
    changed = sum(len(s[1]) for s in steps if s[0] == 'data')
    want = {new[k:k + 8] for k in range(n, len(new) - 7)}         # the appended part: DigiGlide's code, with stock's
    index = {}                                                    # table inside it
    for at in range(0, n - 7):
        w = stock[at:at + 8]
        if w in want and w != w[:1] * 8:
            index.setdefault(w, []).append(at)
    tail = find_copies(stock, index, new, n, len(new))
    steps += tail
    # rebuild from the steps, as the patcher will
    out = bytearray()
    for s in steps:
        out += stock[s[1]:s[1] + s[2]] if s[0] == 'copy' else s[1]
    assert bytes(out) == new, 'the steps do not rebuild the section'
    # checks: what is carried as data is DigiGlide's
    pos, data_at = 0, []
    for s in steps:
        ln = s[2] if s[0] == 'copy' else len(s[1])
        if s[0] == 'data':
            data_at.append((pos, pos + ln))
        pos += ln
    code0 = new.index(open(os.path.join(d, 'code.bin'), 'rb').read(), n)   # where the linked code is in the section
    t0, t1 = code0 + sym['dg_ptable'] - CODE_VA, code0 + sym['dg_records'] - CODE_VA
    in_table = sum(max(0, min(b, t1) - max(a, t0)) for a, b in data_at)
    assert in_table == 0, f'{in_table} bytes of the relocated stock table would be carried as data'
    long_shared = 0
    for a, b in data_at:
        if a >= n:
            for k in range(a, b - MIN_COPY + 1):
                if new[k:k + 8] in index and stock.find(new[k:k + MIN_COPY]) >= 0:
                    long_shared += 1
    assert long_shared == 0, f'{long_shared} stretches of {MIN_COPY} bytes in the data are also in stock'
    body = bytearray()
    for s in steps:
        if s[0] == 'copy':
            body += b'C' + struct.pack('>II', s[1], s[2])
        else:
            body += b'D' + struct.pack('>I', len(s[1])) + s[1]
    head = {'format': 1, 'name': 'DigiGlide', 'build': build, 'os': '1.12', 'section': 3, 'chain': CHAIN,
            'stock_sha256': sha(raw), 'stock_section_sha256': sha(stock), 'section_sha256': sha(new),
            'out_sha256': sha(built), 'out_name': os.path.basename(built_path), 'out_bytes': len(built)}
    hj = json.dumps(head, sort_keys=True).encode()
    z = zlib.compress(bytes(body), 9)
    path = os.path.join(HERE, f'DigiGlide_{build}.dgpatch')
    open(path, 'wb').write(b'DGPATCH1' + struct.pack('>I', len(hj)) + hj + z)
    copied_tail = sum(s[2] for s in tail if s[0] == 'copy')
    carried = sum(len(s[1]) for s in steps if s[0] == 'data')
    print(f'{path}: {os.path.getsize(path):,} bytes')
    print(f'  stock part: {same} changed places, {changed} bytes carried; the rest copied from the stock file')
    print(f'  appended part: {len(new) - n:,} bytes, {copied_tail:,} of them copied from the stock file '
          f'(the relocated table: {t1 - t0:,} bytes, all copied)')
    print(f'  carried as data in all: {carried:,} bytes; none of it a stretch of {MIN_COPY} bytes that stock holds')
    print(f'  makes {head["out_name"]} sha256 {head["out_sha256"]}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
