"""DigiGlide and the 16-voice pool (found on the unit, build 7: reservations piled up until other tracks were silent).
  A  tracks 2, 5, 6 hold 12 voices; VCNT 4 on track 12 takes the last 4: the message says other tracks have none.
  B  a sound that was a DigiGlide sound (HOLD marker), VCNT off, VOICES 4 left by an earlier session: on the first
     look the voices go back to the default, and a track with no reserved voices sounds again.
  C  a WAVETONE sound that was never a DigiGlide sound keeps its VOICES 4.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_voices_pool.py [DIGIGLIDE.syx]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, U16, Ui
from osver import A

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def session(tag, reserves):
    s = Session(img, tag=tag, solo=True, reserve=0)
    assert s.k.mach(11) == 1                             # the demo's track 12 is a WAVETONE track
    k = s.k
    cfg = k.call(A(0x40030AF8), [k.call(A(0x4003E41A), [s.app])])
    for t, n in reserves:
        k.call(A(0x40029094), [cfg, t, n])
    return s, cfg


def voices(s, cfg):
    k = s.k
    d = k.call(k.h.u32(k.h.u32(cfg) + 40), [cfg])
    return [k.h.r(d + 5 * t + 1, 1)[0] for t in range(16)]


def msg(s):
    return bytes(s.k.h.r(s.sym['dg_msg'], 28)).split(b'\0')[0].decode()


def sounding(s, tracks):
    for t in tracks:
        for i in range(4):
            s.trig(4 * i + 2, note=60 + i, length=2, t=t)
    used = {}
    for f in s.play(2400, bpm=120):
        on = U16(f, 0x22)
        for v in range(16):
            if on >> v & 1:
                used.setdefault(U16(f, 0xA5A + 2 * v), set()).add(v)
    return used


s, cfg = session('vp_a', ((1, 4), (4, 4), (5, 4)))
s.set_sound(Ui(vcnt=4, glid=3, drft=0, vib=0), t=11)
s.k.tap('SYN'); s.k.h.frames(400)
v = voices(s, cfg)
check(v[11] == 4 and sum(v) == 16, f'A: VCNT 4 on track 12 reserves the last 4 voices (VOICES {v})')
check(msg(s) == 'OTHER TRACKS: NO VOICES', f'A: the message says so ("{msg(s)}")')

s, cfg = session('vp_b', ((1, 4), (4, 4), (5, 4), (11, 4)))
s.set_sound(Ui(vcnt=4, glid=3, drft=0, vib=0), t=11)
s.k.tap('SYN'); s.k.h.frames(400)
v = voices(s, cfg)
check(v[11] == 4 and sum(v) == 16, f'B: VCNT on, VOICES 4 already there from an earlier session (VOICES {v})')
s.k.slot(11, 54, 0)                                      # VCNT OFF
s.k.tap('SYN'); s.k.h.frames(400)
v = voices(s, cfg)
check(v[11] == 0 and sum(v) == 12, f'B: VCNT switched off: the 4 voices are handed back (VOICES {v})')
check(msg(s) == 'VOICES FREED: TRACK 12', f'B: the message says so ("{msg(s)}")')
u = sounding(s, (6, 13))
check(u.get(6) and u.get(13), f'B: tracks with no reserved voices sound again (track 7 on {sorted(u.get(6, []))}, track 14 on {sorted(u.get(13, []))})')

s, cfg = session('vp_b2', ((1, 4), (11, 4)))
s.set_sound(Ui(vcnt=4, glid=3, drft=0, vib=0), t=11, on=False)
s.k.tap('SYN'); s.k.h.frames(400)
v = voices(s, cfg)
check(v[11] == 4, f'B: VOICES set by hand on a former DigiGlide sound with VCNT off stays (VOICES {v})')
s.k.h.w(s.sym['dg_vchk'], bytes(16))                     # as after power-on: no track looked at yet
s.k.tap('SYN'); s.k.h.frames(400)
v = voices(s, cfg)
check(v[11] == 4, f'B: after power-on nothing is touched in the first 2 s, while the kit loads (VOICES {v})')
s.k.h.frames(3000); s.k.tap('SYN'); s.k.h.frames(200)
v = voices(s, cfg)
check(v[11] == 0 and v[1] == 4, f'B: then the first look hands back a former DigiGlide sound\'s voices (VOICES {v})')

s, cfg = session('vp_c', ((1, 4), (9, 4)))
assert s.k.mach(9) == 1 and s.k.mach(11) == 1
s.k.slot(9, 94, 0)
s.k.tap('SYN'); s.k.h.frames(400)
v = voices(s, cfg)
check(v[9] == 4 and v[1] == 4, f'C: a sound that was never a DigiGlide sound keeps its VOICES (VOICES {v})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
