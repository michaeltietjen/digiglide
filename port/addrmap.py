"""Port addresses from Digitone II OS 1.11 to 1.12 (DigiGlide, spec rev 3: the user runs 1.12).

Only section 3 (the ColdFire MAIN OS) differs between the two images; sections 2, 7 (SHARC) and 8 are byte-identical.

  code / image data (0x40000400.. in the image): the 1.11 bytes around the address, with every longword that looks
      like an absolute address masked (they move too), are searched for in 1.12 near the address plus the local shift.
      The match must be unique and cover at least 40 unmasked bytes.
  RAM (0x42.., 0x44.., 0x46.., 0x80..): the 1.11 code that holds the literal (or literal + small offsets) is mapped
      to 1.12 as above and the literal read back there; every reference must agree.

    ~/dn2-workspace/repos/digikit/.venv/bin/python addrmap.py 0x40025E82 0x80005E60 ...   prints 1.11 -> 1.12
Reads ~/dn2-workspace/extracted/section_3.bin (1.11) and ~/dn2-workspace/v112/extracted/section_3.bin (1.12)."""
import os, struct, sys
from collections import Counter, defaultdict

WS = os.path.expanduser('~/dn2-workspace')
BASE = 0x40000400
A = open(os.path.join(WS, 'extracted/section_3.bin'), 'rb').read()
B = open(os.path.join(WS, 'v112/extracted/section_3.bin'), 'rb').read()
END_A, END_B = BASE + len(A), BASE + len(B)
CODE_END = 0x401D0000                    # ColdFire code ends below the tables


def looks_abs(v):
    return (0x40000000 <= v < 0x48000000) or (0x80000000 <= v < 0x80100000) or (0x20000000 <= v < 0x20100000)


def masked(buf, off, n):
    """bytes buf[off:off+n] with absolute-looking longwords (at any even offset) replaced by None."""
    seg = list(buf[off:off + n])
    for k in range(0, n - 3, 2):
        v = struct.unpack_from('>I', buf, off + k)[0]
        if looks_abs(v):
            for j in range(4):
                seg[k + j] = None
    return seg


_shift = None


def shifts():
    """coarse (1.11 offset, delta) anchors from unique 16-byte chunks."""
    global _shift
    if _shift is None:
        idx = defaultdict(list)
        for k in range(0, len(B) - 16, 2):
            idx[B[k:k + 16]].append(k)
        _shift = []
        for k in range(0, len(A) - 16, 32):
            c = idx.get(A[k:k + 16], [])
            if len(c) == 1:
                _shift.append((k, c[0] - k))
    return _shift


def local_delta(off):
    s = shifts()
    lo, hi = 0, len(s)
    while lo < hi:
        m = (lo + hi) // 2
        if s[m][0] <= off:
            lo = m + 1
        else:
            hi = m
    near = [d for k, d in s[max(0, lo - 8):lo + 8]]
    return Counter(near).most_common(3)


def map_image(va, before=48, after=48, radius=0x3000):
    off = va - BASE
    lo = max(0, off - before)
    pat = masked(A, lo, before + after)
    fixed = [(i, b) for i, b in enumerate(pat) if b is not None]
    if len(fixed) < 40:
        raise ValueError(f'{va:#x}: only {len(fixed)} fixed bytes around it')
    cands = set()
    for d, _ in local_delta(off):
        for x in range(lo + d - radius, lo + d + radius, 2):
            if 0 <= x and x + before + after <= len(B) and all(B[x + i] == b for i, b in fixed):
                cands.add(x)
        if cands:
            break
    if len(cands) != 1:
        raise ValueError(f'{va:#x}: {len(cands)} matches')
    return BASE + cands.pop() + (off - lo)


def refs(lit, slack=0x400):
    """1.11 code offsets holding a longword in [lit - slack, lit + slack] -> {offset: value}."""
    out = {}
    for k in range(0, CODE_END - BASE - 3, 2):
        v = struct.unpack_from('>I', A, k)[0]
        if lit - slack <= v <= lit + slack:
            out[k] = v
    return out


def map_ram(lit, slack=0x400, need=3):
    votes = Counter()
    seen = 0
    for k, v in refs(lit, slack).items():
        try:
            nb = map_image(BASE + k, 40, 40) - BASE
        except ValueError:
            continue
        w = struct.unpack_from('>I', B, nb)[0]
        votes[w - v] += 1
        seen += 1
    if not votes:
        raise ValueError(f'{lit:#x}: no mappable references')
    (d, n), = votes.most_common(1)
    if n < min(need, seen) or n < 0.8 * seen:
        raise ValueError(f'{lit:#x}: references disagree {votes.most_common(4)}')
    return lit + d, n, seen


def port(va):
    if BASE <= va < END_A:
        return map_image(va), 'image'
    r, n, seen = map_ram(va)
    return r, f'ram ({n}/{seen} references agree)'


if __name__ == '__main__':
    for a in sys.argv[1:]:
        va = int(a, 16)
        try:
            r, how = port(va)
            print(f'{va:#010x} -> {r:#010x}  {r - va:+#x}  {how}')
        except ValueError as e:
            print(f'{va:#010x} -> ?  {e}')
