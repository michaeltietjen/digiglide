"""DigiGlide build 18: the stock arpeggiator plays DigiGlide's chord. A DigiGlide track (TYPE MIN, EXT 7), trigs C3
on step 1 and D3 on step 9, each 60 long.
  A  arp MODE UP: the arp is given the chord of each trig and plays it note by note (C Eb G Bb, then D F A C) as
     single stock notes on the track; DigiGlide makes no chord event.
  B  MODE DOWN: the same notes downwards.
  C  POS locked up on step 9 (two inversions): the arp gets A C D F.
  D  MODE CHRD: as before build 18, every arp step is a DigiGlide chord event; the arp is given the key only.
  E  MODE OFF: two chord events, the arp is given nothing.
  F  a track without DigiGlide, MODE UP: the arp gets the key only (stock), every note is the trig's.
  G  keyboard: a key held on the DigiGlide track with MODE UP plays its chord; the key's "note out"
     takes the whole chord out. (Two keys at once and the panel's own release are not reachable in the emulator.)
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b18_arp.py [DIGIGLIDE.syx]"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, Ui, U16
import cfkit
from emu import panelin

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
OFF, TRUE, UP, DOWN, CHRD = 0, 1, 2, 3, 7
ARP_SET = 0x40599728                                     # OS 1.12: the arp's held notes, 16 bytes a track


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def session(tag, t, dg=True):
    s = Session(img, tag=tag, solo=True, reserve=0)
    if dg:
        s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, pos=64, voic=64), t=t, mach=None, atk=None)
    s.trig(0, note=48, length=60, t=t)
    s.trig(8, note=50, length=60, t=t)
    return s


def run(s, t, mode, blocks=2600):
    k, h = s.k, s.k.h
    snd = k.sound(t)
    h.uc.mem_write(snd + 351, bytes([mode])); h.uc.mem_write(snd + 374, bytes([mode]))
    u32 = lambda n: struct.unpack('>I', bytes(h.r(s.sym[n], 4)))[0]
    i0, e0 = u32('dg_arp_ins'), s.dg()['trigs']
    fr = s.play(blocks, bpm=120)
    notes = [U16(f, 2 + 2 * v) >> 8 for f in fr for v in range(16) if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) == t]
    return notes, u32('dg_arp_ins') - i0, s.dg()['trigs'] - e0, list(bytes(h.r(s.sym['dg_arp_last'], 8)))


T = 0
s = session('b18a', T)
notes, ins, ev, last = run(s, T, UP)
check(ins == 2 and last[:5] == [4, 50, 53, 57, 60], f'A: the arp was given each trig\'s chord ({ins} chords, the last {last[1:5]})')
check(notes[:4] == [48, 51, 55, 58] and set(notes[8:12]) == {50, 53, 57, 60} and notes[8:12] == sorted(notes[8:12]),
      f'A: UP plays the chord note by note: {notes}')
check(ev == 0, f'A: no DigiGlide chord event ({ev})')

s = session('b18b', T)
notes, ins, ev, last = run(s, T, DOWN)
check(notes[:4] == [58, 55, 51, 48], f'B: DOWN plays it downwards: {notes[:8]}')

s = session('b18c', T)
s.k.call(s.sym['dg_lock_put'], [T, 8, 4, 80])
notes, ins, ev, last = run(s, T, UP)
check(last[:5] == [4, 57, 60, 62, 65] and notes[:4] == [48, 51, 55, 58], f'C: POS locked to 80 on step 9: the arp gets {last[1:5]} (two inversions up); step 1 as before {notes[:4]}')

s = session('b18d', T)
notes, ins, ev, last = run(s, T, CHRD)
check(ins == 0 and ev >= 4, f'D: CHRD: {ev} DigiGlide chord events (one per arp step), the arp given the key only')

s = session('b18e', T)
notes, ins, ev, last = run(s, T, OFF)
check(ins == 0 and ev == 2, f'E: arp OFF: {ev} chord events, nothing given to the arp')

T2 = 1
s = session('b18f', T2, dg=False)
notes, ins, ev, last = run(s, T2, UP)
check(ins == 0 and len(notes) >= 8 and set(notes) == {48, 50}, f'F: a track without DigiGlide: stock arp, the trig\'s own note every step ({sorted(set(notes))}, {len(notes)} notes)')

s = Session(img, tag='b18g', solo=True, reserve=0)
k, h = s.k, s.k.h
s.set_sound(Ui(vcnt=5, type=1, ext=2, glid=3, pos=64, voic=64), t=T, mach=None, atk=None)
snd = k.sound(T)
h.uc.mem_write(snd + 351, bytes([UP])); h.uc.mem_write(snd + 374, bytes([UP]))
u32 = lambda n: struct.unpack('>I', bytes(h.r(s.sym[n], 4)))[0]


def btn(g, m, n=3_000_000, fr=30):
    h.pc = panelin.buttons(h.m, h.profile, g, m); h.run(n); h.frames(fr)


def set_notes():
    b = bytes(h.r(ARP_SET + 16 * T, 16))
    return [32 * w + i for w in range(4) for i in range(32) if struct.unpack_from('>I', b, 4 * w)[0] >> i & 1]


def played(st):
    return [U16(f, 2 + 2 * v) >> 8 for f, _ in h.sent[st:] for v in range(16) if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) == T]


k.tap('KEYB')
st = len(h.sent)
btn(3, 0x01, fr=1500)
one = set_notes()
last = list(bytes(h.r(s.sym['dg_arp_last'], 8)))
notes = played(st)
check(u32('dg_arp_ins') == 1 and one == last[1:5] and len(one) == 4, f'G: a held key gives the arp its chord ({one})')
check(len(notes) >= 4 and notes[:4] == one, f'G: and it is played note by note: {notes[:8]}')
# The emulated panel takes no key change after the first key (a stock track behaves the same: the key stays in the
# arp's set and the arp runs on), so the release is made by calling the hooked "note out" as stock's handler does.
r0 = k.call(s.sym['dg_arp_out'], [T, 99])                # a note that is no held key: stock's own call, nothing leaves
check(set_notes() == one and u32('dg_arp_outs') == 0, f'G: "note out" for a note that is no held key changes nothing ({set_notes()})')
k.call(s.sym['dg_arp_out'], [T, one[0]])
check(u32('dg_arp_outs') == 1 and not set_notes(), f'G: "note out" for the key takes its whole chord out of the arp (set {set_notes()})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
