"""Open question 1: how many voices can one track hold, and how does stock allocate / steal them for a 4-note trig?

Stock trigs carry NOTE + NOT2..NOT4 (sound slots 9..11, offsets centred on 64). This places a trig on step 1 of the
first N tracks, sets each track's chord to +4 / +7 / +11 (maj7 = 4 notes), plays, and decodes the SPI frames the OS
sends: per note-on, which voice, which note, which track.
    ~/dn2-workspace/repos/digikit/.venv-fast/bin/python q1_voices.py
"""
import os, struct, sys
SK = os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts')
sys.path.insert(0, SK)
import dn2paths as P
os.chdir(P.DIGIKIT)
import cfkit

APP = 0x4018A97A
U16 = lambda f, o: struct.unpack_from('>H', f, o)[0]


def decode(frames):
    ev = []
    for i, f in enumerate(frames):
        on = U16(f, 0x22)
        for v in range(16):
            if on >> v & 1:
                ev.append((i, v, U16(f, 0x02 + 2 * v) / 256, U16(f, 0xA5A + 2 * v)))
    return ev


def run(ntracks, chord=(4, 7, 11)):
    k = cfkit.Kit(str(P.SEC3_STOCK), str(P.STOCK), None, str(P.BUILD / 'stock_emu'))
    app = k.call(APP)
    slots = [k.call(0x400DBCC4, [e]) for e in (28, 29, 30, 31)]   # entries of Note 1..4 (record index + 1)
    print('  entry->slot NOTE..NOT4:', slots, ' ctx0 track word:', k.h.u32(k.call(0x4003EFDE, [app]) + 60))
    for t in range(ntracks):
        # select track t as the active one via the edit context of that track
        ctx = k.call(0x4003EFDE, [app]) + 132 * t       # P + 70 + 132 t (track 0 active at boot)
        assert k.h.u32(ctx + 60) == t, (t, k.h.u32(ctx + 60))
        for s, off in zip(slots[1:], chord):          # chord first: a new trig copies the TRIG page values
            k.slot(t, s, (64 + off) << 8)
        k.call(0x40054690, [ctx, 0, 1, 1])            # trig on step 1
    frames = k.play(120, bpm=120)
    return decode(frames)


for n in (1, 4, 5):
    ev = run(n)
    first = [e for e in ev if e[0] == ev[0][0]] if ev else []
    print(f'--- {n} track(s) with a 4-note trig on step 1: {len(ev)} note-ons in 120 blocks')
    for i, v, note, t in ev[:24]:
        print(f'  block {i:3d}  voice {v:2d}  note {note:6.2f}  track {t}')
