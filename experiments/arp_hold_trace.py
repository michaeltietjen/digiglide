"""Who empties the arp's note set? A DigiGlide track (HOLD on, arp UP), a short trig on step 1 and one on step 9.
Every entry of stock's "clear this track's set" (0x40029be8) is logged with the block, its caller and the caller's
caller's arguments; the set is printed whenever it changes.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python arp_hold_trace.py IMAGE.syx [HOLD 0/1] [LENGTH]"""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mod', 'tests'))
from dgkit import Session, Ui, U16
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_PC
from unicorn.m68k_const import UC_M68K_REG_A7

img = sys.argv[1]
hold = int(sys.argv[2]) if len(sys.argv) > 2 else 1
ln = int(sys.argv[3]) if len(sys.argv) > 3 else 6
ARP_SET, T = 0x40599728, 0
s = Session(img, tag='ahtrace', solo=True, reserve=0)
s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, pos=64, voic=64, hold=hold), t=T, mach=None, atk=None)
s.trig(0, note=48, length=ln, t=T)
s.trig(8, note=50, length=ln, t=T)
h = s.k.h
snd = s.k.sound(T)
h.uc.mem_write(snd + 351, bytes([2])); h.uc.mem_write(snd + 374, bytes([2]))
log, blk = [], [0]


def at(uc, addr, size, ud):
    sp = uc.reg_read(UC_M68K_REG_A7)
    w = struct.unpack('>12I', bytes(uc.mem_read(sp, 48)))
    log.append((blk[0], hex(addr), [hex(x) for x in w]))


for a in (0x40029BE8, 0x40027C60, 0x40029C72):
    h.uc.hook_add(UC_HOOK_CODE, at, begin=a, end=a)
def wr(uc, access, addr, size, value, ud):
    sp = uc.reg_read(UC_M68K_REG_A7)
    w = struct.unpack('>24I', bytes(uc.mem_read(sp, 96)))
    log.append((blk[0], 'write', hex(addr), hex(value & 0xFFFFFFFF), 'pc', hex(uc.reg_read(UC_M68K_REG_PC)), [hex(x) for x in w if 0x40000400 <= x < 0x40310000]))


h.uc.hook_add(UC_HOOK_MEM_WRITE, wr, begin=ARP_SET + 16 * T, end=ARP_SET + 16 * T + 15)
last = [None]


def each(i):
    blk[0] = i
    b = bytes(h.r(ARP_SET + 16 * T, 16))
    st = [32 * w + j for w in range(4) for j in range(32) if struct.unpack_from('>I', b, 4 * w)[0] >> j & 1]
    if st != last[0]:
        print('block', i, 'set', st, flush=True)
        last[0] = st


fr = s.play(2400, bpm=120, each=each)
ons = [(b, U16(f, 2 + 2 * v) >> 8) for b, f in enumerate(fr) for v in range(16) if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) == T]
print('note-ons', ons)
for l in log:
    print(l)
b = bytes(h.r(ARP_SET + 16 * T, 16))
print('after [STOP]: set', [32 * w + j for w in range(4) for j in range(32) if struct.unpack_from('>I', b, 4 * w)[0] >> j & 1])
h.frames(400)
b = bytes(h.r(ARP_SET + 16 * T, 16))
print('400 blocks later: set', [32 * w + j for w in range(4) for j in range(32) if struct.unpack_from('>I', b, 4 * w)[0] >> j & 1])
import osver
u = lambda a, n=4: int.from_bytes(bytes(h.r(a, n)), 'big')
print('PLAY_FLAG', u(osver.A(0x42C5A994)), 'latches', u(s.sym['dg_arp_latches'], 2), 'keys held', bytes(h.r(osver.A(0x445A1E30), 6)).hex(),
      'mute', u(osver.A(0x8000521A), 2), 'DG', s.dg())
ons2 = [(b, U16(f, 2 + 2 * v) >> 8) for b, (f, _) in enumerate(h.sent[-400:]) for v in range(16) if U16(f, 0x22) >> v & 1]
print('note-ons in the last 400 blocks', ons2)
