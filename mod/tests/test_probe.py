"""DigiGlide's read-only USB probe (probe.S, dnfw's usbprobe protocol): requests are handed to the firmware's own SysEx
router, as its MIDI input task does, and the reply is read from the probe's send buffer.
  A  HELLO answers with protocol 3 and the build's tag ("DG <build>").
  B  PEEK returns the bytes of DigiGlide's state, the same as the emulator reads there.
  C  PEEK outside RAM (a peripheral register) is refused; an unknown command (STATS, a write) answers "unknown".
  D  the same request from DIN MIDI, or with another device byte, gets no answer, and neither does a message
     with no body (all three fall through to the stock router code).
  E  switching the status box on ([FUNC] + push encoder G) shows "DIGIGLIDE BUILD <n>".
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_probe.py [DIGIGLIDE.syx]"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


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


s = Session(img, tag='probe', solo=True, reserve=0)
k, h = s.k, s.k.h
TX, BUF = s.sym['dg_probe_tx'], 0x46900000 - 0x1000        # a scratch message buffer in free RAM
ROUTER = A(0x4012166E)


def ask(body, dev=0x7D, source=2, raw=None):
    msg = raw or (bytes([0xF0, 0x00, 0x20, 0x3C, dev, 0x00]) + pack7(body) + b'\xF7')
    h.w(TX, bytes(0x4C0))
    h.w(BUF, msg)
    k.call(ROUTER, [BUF, len(msg), source])
    t = bytes(h.r(TX, 0x4C0))
    if t[0] != 0xF0:
        return None
    return unpack7(t[6:t.index(0xF7)])


r = ask(struct.pack('>HB', 0x1234, 1))
check(r and r[:4] == bytes([0x12, 0x34, 0x81, 0]) and r[4:6] == b'\0\x03' and r[10:].split(b'\0')[0].startswith(b'DG '),
      f'A: HELLO: seq echoed, status ok, protocol 3, tag {r[10:].split(bytes(1))[0] if r else None}')
dg = s.sym['DG']
want = bytes(h.r(dg, 64))
r = ask(struct.pack('>HBIH', 7, 3, dg, 64))
check(r and r[3] == 0 and struct.unpack('>I', r[4:8])[0] == dg and r[8:72] == want, 'B: PEEK of DigiGlide state (64 bytes at DG): the bytes the emulator reads there')
r = ask(struct.pack('>HBIH', 8, 3, 0x80005E60, 1024))
check(r and r[3] == 0 and r[8:8 + 1024] == bytes(h.r(0x80005E60, 1024)), 'B: PEEK of the frame in SRAM, 1024 bytes')
r = ask(struct.pack('>HBIH', 9, 3, 0xFC045640, 4))
check(r and r[3] == 1 and len(r.rstrip(b'\0')) <= 4, f'C: PEEK of a peripheral register is refused (status {r[3] if r else None})')
r = ask(struct.pack('>HBIH', 10, 3, 0x47FFFFF0, 64))
check(r and r[3] == 1, 'C: PEEK running past the end of RAM is refused')
r = ask(struct.pack('>HBIH', 11, 3, dg, 2000))
check(r and r[3] == 1, 'C: PEEK longer than 1024 bytes is refused')
for cmd in (2, 4, 0x7F):
    r = ask(struct.pack('>HBIH', 12, cmd, dg, 4))
    check(r and r[3] == 2, f'C: command {cmd} (no such command: nothing writes) answers "unknown"')
check(ask(struct.pack('>HB', 1, 1), source=8) is None, 'D: the same HELLO from DIN MIDI: no answer')
check(ask(struct.pack('>HB', 1, 1), dev=0x15) is None, 'D: another device byte: no answer')
check(ask(None, raw=bytes([0xF0, 0x00, 0x20, 0x3C, 0x7D, 0x00, 0xF7])) is None, 'D: a message with no body: no answer')
# E: the status box's toggle ([FUNC] + push encoder G) names the build
s._btn(2, 0x01, 500_000); s._btn(5, 0x40, 500_000); s._btn(5, 0x00, 15_000_000); s._btn(2, 0x00, 15_000_000)
msg = bytes(h.r(s.sym['dg_msg'], 28)).split(b'\0')[0].decode()
build = os.path.basename(img)[:-4].rsplit('_', 1)[-1]
check(msg == 'DIGIGLIDE BUILD ' + build and h.u32(s.sym['DG'] + 0) is not None, f'E: status box on: the message reads "{msg}"')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
