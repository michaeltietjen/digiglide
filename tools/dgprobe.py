#!/usr/bin/env python3
"""Read live state from a Digitone II running DigiGlide (build 13 or later), over USB MIDI, on the Mac.
Every command only reads: the probe in the firmware has no command that writes (mod/probe.S).

    python3 dgprobe.py ports              the MIDI ports this Mac sees
    python3 dgprobe.py hello              is DigiGlide answering, and which build
    python3 dgprobe.py peek ADDR [LEN]    hex dump (RAM 0x40000000..0x48000000, SRAM 0x80000000..0x80010000)
    python3 dgprobe.py sym NAME [LEN]     peek at a symbol of the build that answers (DG, dg_name, dg_msg, T, ...)
    python3 dgprobe.py selftest           the codec, with no device

    options: --port "Digitone II" (a substring of the port name), --build-dir ~/dn2-workspace/build, --os 1.12

Stock firmware ignores these messages (device byte 0x7D is no Elektron machine), so a unit that does not answer is
running stock or a build before 13. Close Elektron Transfer and Overbridge first if the port is busy.
Needs mido and python-rtmidi (pip3 install mido python-rtmidi).

Protocol and codec derived from dnfw's tools/dn2probe.py (AGPL-3.0-or-later), itself derived from irpina/digihealth
(tools/digiusb.py, GPL-2.0-or-later).
    request  F0 00 20 3C 7D 00 <pack7: u16 seq, u8 cmd, payload> F7
    reply    F0 00 20 3C 7D 00 <pack7: u16 seq, u8 cmd | 0x80, u8 status, payload> F7
Integers big-endian. Status 0 ok, 1 refused argument, 2 unknown command."""
import argparse, os, struct, sys, time

HEADER = [0x00, 0x20, 0x3C, 0x7D, 0x00]
HELLO, PEEK = 1, 3
STATUS = {0: 'ok', 1: 'refused (address or length outside the readable ranges)', 2: 'unknown command'}


def pack7(b):
    out = bytearray()
    for i in range(0, len(b), 7):
        g = b[i:i + 7]
        out.append(sum(0x40 >> k for k, x in enumerate(g) if x & 0x80))
        out += bytes(x & 0x7F for x in g)
    return bytes(out)


def unpack7(b):
    out, i = bytearray(), 0
    while i < len(b):
        top, g = b[i], b[i + 1:i + 8]
        out += bytes(x | (0x80 if top & (0x40 >> k) else 0) for k, x in enumerate(g))
        i += 8
    return bytes(out)


class Probe:
    def __init__(self, port):
        import mido
        self.mido = mido
        ins = [n for n in mido.get_input_names() if port.lower() in n.lower()]
        outs = [n for n in mido.get_output_names() if port.lower() in n.lower()]
        if not ins or not outs:
            sys.exit(f'no MIDI port matching "{port}" (run: dgprobe.py ports). Is the unit on USB and switched on?')
        self.i, self.o, self.seq = mido.open_input(ins[0]), mido.open_output(outs[0]), int(time.time()) & 0x7FFF

    def ask(self, cmd, payload=b'', timeout=1.0):
        self.seq = (self.seq + 1) & 0xFFFF
        for _ in self.i.iter_pending():
            pass
        self.o.send(self.mido.Message('sysex', data=HEADER + list(pack7(struct.pack('>HB', self.seq, cmd) + payload))))
        end = time.time() + timeout
        while time.time() < end:
            for m in self.i.iter_pending():
                if m.type == 'sysex' and list(m.data[:5]) == HEADER:
                    r = unpack7(bytes(m.data[5:]))
                    if len(r) >= 4 and struct.unpack('>H', r[:2])[0] == self.seq and r[2] == cmd | 0x80:
                        return r[3], r[4:]
            time.sleep(0.002)
        return None, b''

    def hello(self):
        st, p = self.ask(HELLO)
        if st is None:
            sys.exit('no answer: the unit is running stock or a DigiGlide build before 13 (or another program holds the port)')
        return {'proto': struct.unpack('>H', p[:2])[0], 'frames': struct.unpack('>I', p[2:6])[0],
                'tag': p[6:].split(b'\0')[0].decode('ascii', 'replace')}

    def peek(self, addr, n):
        out = b''
        while n > 0:
            k = min(n, 1024)
            st, p = self.ask(PEEK, struct.pack('>IH', addr, k))
            if st is None:
                sys.exit('no answer')
            if st:
                sys.exit(f'peek {addr:#010x} {k}: {STATUS.get(st, st)}')
            out += p[4:4 + k]
            addr += k
            n -= k
        return out


def dump(addr, b):
    for i in range(0, len(b), 16):
        g = b[i:i + 16]
        print(f'{addr + i:08x}  {g.hex(" "):<47}  {"".join(chr(x) if 32 <= x < 127 else "." for x in g)}')


def symbols(build_dir, tag, osv):
    """The symbols of the build that answered: the tag is "DG <n>", the build's folder ends _<n>."""
    n = tag.split()[-1]
    for d in sorted(os.listdir(build_dir)):
        p = os.path.join(build_dir, d, 'symbols.txt')
        if d == f'DN2_{osv}_DIGIGLIDE_{n}' and os.path.exists(p):
            return {l.split()[-1]: int(l.split()[0], 16) for l in open(p) if len(l.split()) >= 2}
    sys.exit(f'no symbols.txt for DN2_{osv}_DIGIGLIDE_{n} under {build_dir}')


def selftest():
    import random
    for n in list(range(0, 40)) + [1024]:
        b = bytes(random.randrange(256) for _ in range(n))
        p = pack7(b)
        assert all(x < 0x80 for x in p) and unpack7(p)[:n] == b, n
    print('codec ok')


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('command', choices=['ports', 'hello', 'peek', 'sym', 'selftest'])
    a.add_argument('rest', nargs='*')
    a.add_argument('--port', default='Digitone II')
    a.add_argument('--build-dir', default=os.path.expanduser('~/dn2-workspace/build'))
    a.add_argument('--os', default='1.12', help='the OS the unit runs (picks the build folder for sym)')
    a = a.parse_args()
    if a.command == 'selftest':
        selftest()
    elif a.command == 'ports':
        import mido
        print('in: ', mido.get_input_names())
        print('out:', mido.get_output_names())
    else:
        pr = Probe(a.port)
        h = pr.hello()
        if a.command == 'hello':
            print(f'{h["tag"]}: DigiGlide build {h["tag"].split()[-1]}, protocol {h["proto"]}, {h["frames"]} audio frames since power on')
        elif a.command == 'peek':
            addr = int(a.rest[0], 0)
            dump(addr, pr.peek(addr, int(a.rest[1], 0) if len(a.rest) > 1 else 64))
        else:
            s = symbols(a.build_dir, h['tag'], a.os)
            if a.rest[0] not in s:
                sys.exit(f'no symbol {a.rest[0]} in build {h["tag"]}')
            dump(s[a.rest[0]], pr.peek(s[a.rest[0]], int(a.rest[1], 0) if len(a.rest) > 1 else 64))
