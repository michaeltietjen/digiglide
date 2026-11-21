"""Image 31, DigiDrone: [FUNC] + push encoder A picks one of the ten drone sounds, [FUNC] + push encoder B loads it
into the active track (stock's sound loader) with its DigiGlide settings.
    ~/dn2-workspace/repos/digikit/.venv/bin/python test_b31_drones.py DIGIGLIDE.syx
"""
import os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser('~/glide/experiments'))
from dgkit import Session, latest, U16
import b29_sounds, b29_patches, b30_patches
import b33_patches                                   # image 33: the deep set replaces the first ten's values
import make_drones_tab as TAB

img = sys.argv[1] if len(sys.argv) > 1 else latest()
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


s = Session(img, tag='b31')
k, h = s.k, s.k.h


def push(bit):                                  # [FUNC] (2, 0) held, push encoder (5, bit), release both
    s._btn(2, 0x01, 500_000); s._btn(5, 1 << bit, 500_000)
    s._btn(5, 0x00, 15_000_000); s._btn(2, 0x00, 15_000_000)
    h.run(40_000_000)


msg = lambda: bytes(h.r(s.sym['dg_msg'], 28)).split(b'\0')[0].decode()
sel = lambda: h.u32(s.sym['dg_drone_sel']) - (1 << 32 if h.u32(s.sym['dg_drone_sel']) >> 31 else 0)
loads = lambda: h.u32(s.sym['dg_drone_loads'])
snd_hash = lambda t: hashlib.sha1(bytes(h.r(k.sound(t), 1163))).hexdigest()
par = lambda kk: k.call(s.sym['dg_par'], [0, kk]) & 0xFFFF

s.select_track(0)
before0, before1 = snd_hash(0), snd_hash(1)
push(1)
check(loads() == 0 and snd_hash(0) == before0 and 'PICKS' in msg(), f'A [FUNC] + push B with nothing picked loads nothing ("{msg()}")')
for _ in range(3):
    push(0)
check(sel() == 2 and msg() == 'DRONE 3 DARK RING' and snd_hash(0) == before0, f'B [FUNC] + push A three times: drone 3 ("{msg()}"), the sound untouched')
push(1)
name = bytes(h.r(k.sound(0) + 4, 16)).split(b'\0')[0].decode()
want = dict(b29_sounds.sound('ring').slots)
bad = {sid: (hex(v), hex(k.sound_slot(0, sid))) for sid, v in want.items() if k.sound_slot(0, sid) != v}
check(loads() == 1 and msg() == 'LOADED DARK RING' and k.mach(0) == 0 and name == 'DARK RING' and not bad,
      f'C [FUNC] + push B: "{msg()}", track 1 is FM TONE "{name}", {len(want)} sound slots as designed {bad or ""}')
dgs = dict(TAB.ORDER)['ring']
got = {kk: par(kk) >> 8 for kk, _ in dgs}
check(all(got[kk] == v for kk, v in dgs), f'C its DigiGlide settings are set (K: value {got})')
check(snd_hash(1) == before1, 'C track 2\'s sound is untouched')
h.frames(400)
s.trig(4, note=48, length=127, t=0)
fr = s.play(1500, bpm=120)
if not any(U16(f, 0x22) for f in fr):
    fr = s.play(1500, bpm=120)
on = [f for f in fr if U16(f, 0x22)]
vs = [v for v in range(16) if on and U16(on[0], 0x22) >> v & 1]
rec_bad = {}
if vs:
    f = fr[min(len(fr) - 1, next(i for i, x in enumerate(fr) if U16(x, 0x22)) + 60)]   # 40 ms into the chord
    for sid, v in want.items():
        o = b29_sounds.S.slot_off(sid)
        got = U16(f, 0xda + 146 * vs[0] + o) if o is not None else v
        # 65 89 92: DigiGlide's own (lock lane, pan, envelope reset). 43 68 81 98: stock moves these a little on
        # every sound made from the demo kit (before the load too): within 3 knob steps
        if sid == 67:                                   # DARK RING's LFO1 destination: checked below
            continue
        if sid in (65, 89, 92) or (sid in (43, 68, 81, 98) and abs(got - v) <= 0x300):
            continue
        if got != v:
            rec_bad[sid] = (hex(v), hex(got))
check(len(vs) == 4, f'D a trig plays a chord on 4 voices ({vs})')
check(vs and U16(f, 0x94 + 2 * vs[0]) == 0 and U16(f, 0x94 + 2 * vs[-1]) == 0 and not rec_bad,
      f'D the DSP is sent the designed sound: voice record of voice {vs[0] if vs else "-"} equals the patch {rec_bad or ""}')
if vs:                                           # LFO1 on the filter frequency: does the stock LFO move it?
    i0 = next(i for i, x in enumerate(fr) if U16(x, 0x22))
    o67 = 0xda + 146 * vs[0] + b29_sounds.S.slot_off(67)
    tr = [U16(fr[i], o67) for i in range(i0 + 20, len(fr), 100)]
    print(f'  info LFO1 -> filter FREQ (base 0x3000): word every 100 blocks {[hex(x) for x in tr]}', flush=True)
    check(max(tr) != min(tr), 'D the stock LFO moves the filter frequency (LFO1 DEST reads as the filter)')
names = []
for i in range(10):
    push(0); push(1)
    names.append(bytes(h.r(k.sound(0) + 4, 16)).split(b'\0')[0].decode())
want_names = [b29_sounds.SOUNDS[n][0] for n, _ in TAB.ORDER]
check(names == want_names[3:] + want_names[:3] and loads() == 11 and k.mach(0) == 0,
      f'E all ten load in turn, wrapping after the tenth ({names})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
