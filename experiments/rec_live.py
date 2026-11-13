"""Live recording on a DigiGlide track, against stock: [RECORD] + [PLAY], three keys played in keyboard mode about a
beat apart, [STOP]; then the pattern's step words of track 1 and what plays back.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python rec_live.py [stock|IMAGE.syx] [hold]"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
from dgkit import Session, latest, Ui, U16
from osver import A
from emu import panelin
import cfkit

arg = sys.argv[1] if len(sys.argv) > 1 else 'stock'
img = None if arg == 'stock' else arg
hold = len(sys.argv) > 2
s = Session(img, tag='rec_' + ('stock' if not img else 'dg') + ('_h' if hold else ''), solo=True, reserve=0)
k, h = s.k, s.k.h
if img:
    s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=int(hold)))
    for _ in range(3):
        k.tap('SYN')
else:
    k.select(1, track=0)
for st in range(128):
    k.call(A(0x40054690), [s.ctx0, st, 1, 0])
pat = h.u32(A(0x42C5A9A0))
steps = lambda: [st for st in range(64) if h.r(pat + 2 * st + 1, 1)[0] & 1]
k.tap('KEYB')


def btn(g, m, n=3_000_000, fr=20):
    h.pc = panelin.buttons(h.m, h.profile, g, m); h.run(n); h.frames(fr)


h.w(A(0x402A0DEC), cfkit.BE(120 * 120))
btn(2, 0x04); btn(2, 0x0C); btn(2, 0x00)                 # [RECORD] held, [PLAY]: live recording
print('playing', h.u32(A(0x42C5A994)), 'steps with trigs before', steps())
log = []
for mask in (0x01, 0x04, 0x10):                          # three keys, each held ~250 ms, ~1 beat apart
    st = len(h.sent)
    btn(3, mask, fr=375); btn(3, 0x00, fr=375)
    log += [(st + i - 0, [(v, U16(f, 2 + 2 * v) >> 8) for v in range(16) if U16(f, 0x22) >> v & 1]) for i, (f, _) in enumerate(h.sent[st:]) if U16(f, 0x22)]
h.frames(400)
btn(2, 0x10); btn(2, 0x00)                               # [STOP]
print('note-ons while recording:', [(b, v) for b, v in log][:8])
rec = steps()
print('steps with trigs after recording:', rec, [hex(U16(bytes(h.r(pat + 2 * st, 2)), 0)) for st in rec])
if img:
    print('DigiGlide events', h.u32(s.sym['DG'] + 4), 'name', s.chord_name(0))
# playback in a fresh session: the recorded pattern copied over (the emulator will not PLAY again after a recording
# gesture in the same session)
data = bytes(h.r(pat, 131072))
s2 = Session(img, tag='rec_play_' + ('stock' if not img else 'dg') + ('_h' if hold else ''), solo=True, reserve=0)
if img:
    s2.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=int(hold)))
    for _ in range(3):
        s2.k.tap('SYN')
else:
    s2.k.select(1, track=0)
h2 = s2.k.h
h2.w(h2.u32(A(0x42C5A9A0)), data)
names = []
fr = s2.play(3200, bpm=120, each=(lambda i: names.append(bytes(h2.r(s2.sym['dg_name'], 16)).split(b'\0')[0].decode())) if img else None)
pb = [(i, [(v, U16(f, 2 + 2 * v) >> 8) for v in range(16) if U16(f, 0x22) >> v & 1]) for i, f in enumerate(fr) if U16(f, 0x22)]
print('playback note-ons:', pb[:8])
offs = [(i, hex(U16(f, 0x24))) for i, f in enumerate(fr) if U16(f, 0x24)]
print('playback note-offs:', offs[:8])
if img:
    seq = [names[0]] + [b for a, b in zip(names, names[1:]) if a != b]
    print('chord names during playback:', seq, 'events', h2.u32(s2.sym['DG'] + 4))
