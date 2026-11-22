#!/usr/bin/env python3
"""Make the DigiGlide firmware file from your own official Digitone II OS 1.12 file.

    python3 digiglide_patch.py Digitone_II_OS1.12.syx

It checks that the file is Elektron's OS 1.12 (by its SHA-256), applies DigiGlide_35.dgpatch and writes
DN2_1.12_DIGIGLIDE_35.syx beside your file. It refuses any other input, and it writes nothing unless the result is
exactly the image that was built and tested (again by SHA-256). It sends nothing anywhere and does not touch the unit:
you send the result with Elektron Transfer yourself.

Needs Python 3.10 or newer and nothing else. Takes one to three minutes (the firmware is packed in plain Python).

DigiGlide is unofficial: not made, endorsed or supported by Elektron. No warranty; see README.md, "Warning: recovery".
AGPL-3.0-or-later. The container code in vendor/dnfw is dnfw's (angellinares/dn2_firmware_explore, AGPL-3.0-or-later)."""
import glob, hashlib, json, os, struct, sys, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))


def fail(msg):
    print('\nNOT DONE: ' + msg)
    sys.exit(1)


def read_patch(path):
    b = open(path, 'rb').read()
    if b[:8] != b'DGPATCH1':
        fail(f'{os.path.basename(path)} is not a DigiGlide patch file.')
    n = struct.unpack('>I', b[8:12])[0]
    return json.loads(b[12:12 + n]), zlib.decompress(b[12 + n:])


def apply(body, stock):
    out, i = bytearray(), 0
    while i < len(body):
        if body[i:i + 1] == b'C':
            at, n = struct.unpack('>II', body[i + 1:i + 9])
            if at + n > len(stock):
                fail('the patch does not fit this file.')
            out += stock[at:at + n]
            i += 9
        elif body[i:i + 1] == b'D':
            n = struct.unpack('>I', body[i + 1:i + 5])[0]
            out += body[i + 5:i + 5 + n]
            i += 5 + n
        else:
            fail('the patch file is damaged.')
    return bytes(out)


def main(argv):
    if sys.version_info < (3, 10):
        fail(f'this needs Python 3.10 or newer; this is Python {sys.version.split()[0]}. Get it from python.org.')
    args = [a for a in argv if not a.startswith('-')]
    if len(args) != 1 or '-h' in argv or '--help' in argv:
        print(__doc__)
        sys.exit(0 if '-h' in argv or '--help' in argv else 1)
    src = args[0]
    patches = sorted(glob.glob(os.path.join(HERE, 'DigiGlide_*.dgpatch')))
    if len(patches) != 1:
        fail(f'expected one DigiGlide_*.dgpatch file beside this script, found {len(patches)}.')
    head, body = read_patch(patches[0])
    if not os.path.isfile(src):
        fail(f'no such file: {src}')
    raw = open(src, 'rb').read()
    got = hashlib.sha256(raw).hexdigest()
    print(f'DigiGlide build {head["build"]} for Digitone II OS {head["os"]}')
    print(f'your file: {src}\n  sha256 {got}')
    if got == head['out_sha256']:
        fail('this file already is the DigiGlide image. Give the official Elektron OS file.')
    if got != head['stock_sha256']:
        fail(f'this is not the official Digitone II OS {head["os"]} file (expected sha256 {head["stock_sha256"]}).\n'
             f'Download Digitone_II_OS{head["os"]}.syx from Elektron\'s support pages and unzip it. Nothing was written.')
    print('  it is the official OS file')
    sys.path.insert(0, os.path.join(HERE, 'vendor'))
    import pathlib
    from dnfw.cli.files import read_image
    from dnfw.firmware import build as fwbuild
    from dnfw.firmware.load import load
    from dnfw.container.section import compress
    from dnfw.codec import aplib, aplibpack
    firmware = load(read_image(pathlib.Path(src)))
    sec = firmware.container.find(head['section'])
    stock = bytes(sec.unpack())
    if hashlib.sha256(stock).hexdigest() != head['stock_section_sha256']:
        fail('the file\'s MAIN OS section is not the expected one. Nothing was written.')
    new = apply(body, stock)
    if hashlib.sha256(new).hexdigest() != head['section_sha256']:
        fail('the patched section is not the expected one. Nothing was written.')
    print(f'patched: MAIN OS {len(stock):,} -> {len(new):,} bytes')
    print('packing (one to three minutes, no progress shown) ...', flush=True)
    t = time.time()
    pack = aplibpack.pack
    aplibpack.pack = lambda d, **kw: pack(d, chain_depth=head['chain'])
    packed = compress(sec.id, sec.dest, new)
    out = bytes(fwbuild.build(firmware, {head['section']: packed}))
    print(f'  packed in {time.time() - t:.0f} s')
    if hashlib.sha256(out).hexdigest() != head['out_sha256'] or len(out) != head['out_bytes']:
        fail('the result is not the tested image (its SHA-256 differs). Nothing was written.\n'
             'Please report this with your Python version (python3 --version).')
    if '--check' in argv:
        print('\nOK (check only, nothing written): the result is the tested image, sha256 ' + head['out_sha256'])
        return
    dst = os.path.join(os.path.dirname(os.path.abspath(src)), head['out_name'])
    open(dst, 'wb').write(out)
    print(f'\nOK: {dst}\n  sha256 {head["out_sha256"]} (the tested image, byte for byte)')
    print('Read "Warning: recovery" in README.md before you send it to the unit with Elektron Transfer.')


if __name__ == '__main__':
    main(sys.argv[1:])
