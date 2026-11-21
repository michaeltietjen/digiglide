"""Build 28: DigiGlide must not make other tracks drop notes (owner, image 25, video).
The hook runs before the frame is sent, so its time on a frame that carries note-ons is what loses them. The owner's
layout: DigiGlide on track 13 (6 voices, HOLD on), kick / snare / 16th hats / bass on tracks 1..4, chord trigs on the
same steps as kick and bass. Mod code bytes run inside the audio ISR per frame (about 3.3 bytes an instruction).
  A  CHRD: on frames with note-ons at most NOTE_MAX; quiet frames' median at most QUIET_MED; no regular spike (the 99th
     percentile of all frames at most P99_MAX); no chord event worked out on a note frame; the wait at most 2 frames.
  B  STRM, STRU, HARP with BASS and a bass pattern: the same limits on note frames.
  C  every case: the other tracks' note-ons are the pattern's (8 / 4 / 32 / 16) and none lands on DigiGlide's reserved
     voices 0..5; every DigiGlide note-on is on voices 0..5.
  D  the status box ([FUNC] + push G) with its third line (the hook's time from DTIM3) on: the pattern plays on.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b28_load.py [IMAGE.syx]
Image 26: A fails (66,160 on a note frame, median 24,186, p99 41,568)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from unicorn import UC_HOOK_BLOCK
from dgkit import Session, Ui, U16, latest
from osver import A

NOTE_MAX, QUIET_MED, P99_MAX = 30000, 20000, 30000
DGT = 12
ok_all = True


def check(ok, text):
    global ok_all
    ok_all &= bool(ok)
    print(('  ok   ' if ok else '  FAIL ') + text, flush=True)


def session(img, tag, **kw):
    s = Session(img, tag=tag, solo=True, reserve=0)
    bpat = kw.pop('bpat', None)
    u = dict(vcnt=6, type=1, ext=0, glid=3, hold=1, bass=0, voic=64, drft=8, vib=4); u.update(kw)
    s.set_sound(Ui(**u), t=DGT, mach=None, atk=None)
    if bpat is not None:
        s.k.call(s.sym['dg_par_set'], [DGT, 19, bpat << 8])     # K_BPAT
    for st, note in ((0, 48), (8, 53), (16, 55), (24, 50)):
        s.trig(st, note=note, length=127, t=DGT)
    for st in range(0, 32, 4):  s.trig(st, note=36, length=2, t=0)
    for st in range(4, 32, 8):  s.trig(st, note=38, length=2, t=1)
    for st in range(0, 32, 1):  s.trig(st, note=42, length=1, t=2)
    for st in range(0, 32, 2):  s.trig(st, note=36 + st % 12, length=6, t=3)
    return s


def measure(img, tag, blocks=6000, **kw):
    s = session(img, tag, **kw)
    addrs = sorted(a for a in s.sym.values() if 0x40000000 <= a < 0x48000000)
    per, cur, inisr = [], [0], [False]

    def blk(uc, addr, size, _):
        if inisr[0]:
            cur[0] += size
    h = s.k.h
    h.m.uc.hook_add(UC_HOOK_BLOCK, blk, begin=addrs[0], end=addrs[-1] + 0x4000)
    fe = h.fastemu
    orig = fe.run_isr

    def wrap(*a, **k2):
        inisr[0] = True; cur[0] = 0
        r = orig(*a, **k2)
        inisr[0] = False; per.append(cur[0])
        return r
    fe.run_isr = wrap
    fr = s.play(blocks, bpm=120)
    fe.run_isr = orig
    per = np.array(per[-len(fr):])
    note = np.array([U16(f, 0x22) != 0 for f in fr])
    ons, where = [0] * 16, {}
    for f in fr:
        for v in range(16):
            if U16(f, 0x22) >> v & 1:
                t = min(U16(f, 0xA5A + 2 * v), 15)
                ons[t] += 1
                where.setdefault(t, set()).add(v)
    ex = {nm: h.u32(s.sym[nm]) for nm in ('dg_forced', 'dg_defer_max') if nm in s.sym}
    offs = np.array([U16(f, 0x24) != 0 for f in fr])       # build 30: frames that carry a note-off
    ex['off_max'] = int(per[offs].max()) if offs.any() else 0
    ex['off_n'] = int(offs.sum())
    return per, note, ons, where, ex


def voices(name, ons, where):
    others = set().union(*(where.get(t, set()) for t in range(4)))
    check(ons[:4] == [8, 4, 32, 16], f'C {name}: the other tracks play every note (kick {ons[0]} snare {ons[1]} hats {ons[2]} bass {ons[3]}; 8 4 32 16)')
    check(not (others & set(range(6))), f'C {name}: none of their notes on the reserved voices 0..5 (they use {sorted(others)})')
    check(ons[DGT] > 0 and where.get(DGT, set()) <= set(range(6)), f'C {name}: every DigiGlide note-on on voices 0..5 ({ons[DGT]} on {sorted(where.get(DGT, []))})')


img = sys.argv[1] if len(sys.argv) > 1 else latest()
per, note, ons, where, ex = measure(img, 'b28a')
check(per[note].max() <= NOTE_MAX, f'A CHRD: on frames with note-ons the hook runs at most {NOTE_MAX} bytes of code ({per[note].max()} on {int(note.sum())} frames)')
check(np.median(per[~note]) <= QUIET_MED, f'A CHRD: quiet frames, median at most {QUIET_MED} ({np.median(per[~note]):.0f})')
check(np.percentile(per, 99) <= P99_MAX, f'A CHRD: no regular spike, the 99th percentile at most {P99_MAX} ({np.percentile(per, 99):.0f}; max {per.max()})')
check(ex.get('dg_forced', -1) == 0, f'A CHRD: no chord event worked out on a note frame ({ex.get("dg_forced")})')
check(ex.get('dg_defer_max', 99) <= 2, f'A CHRD: an event waits at most 2 frames for a quiet one ({ex.get("dg_defer_max")})')
check(ex['off_n'] > 0 and ex['off_max'] <= NOTE_MAX, f'A CHRD: on frames with note-offs at most {NOTE_MAX} too, so no chord event there ({ex["off_max"]} on {ex["off_n"]} frames)')
voices('CHRD', ons, where)
for mode, name in ((1, 'STRM'), (2, 'STRU'), (3, 'HARP')):
    per, note, ons, where, ex = measure(img, f'b28b{mode}', play=mode, bass=2, bpat=3)
    check(per[note].max() <= NOTE_MAX, f'B {name} + bass pattern: on frames with note-ons at most {NOTE_MAX} ({per[note].max()} on {int(note.sum())} frames; quiet median {np.median(per[~note]):.0f}, max {per.max()})')
    check(ex.get('dg_forced', -1) == 0, f'B {name}: no chord event worked out on a note frame ({ex.get("dg_forced")}, longest wait {ex.get("dg_defer_max")})')
    check(ex['off_n'] > 0 and ex['off_max'] <= NOTE_MAX, f'B {name}: on frames with note-offs at most {NOTE_MAX} ({ex["off_max"]} on {ex["off_n"]} frames)')
    voices(name, ons, where)

s = session(img, 'b28d')
s.k.h.frames(300)
s.func_with(5, 6)                                       # [FUNC] + push encoder G
line = s.k.call(s.sym['dg_dbg_line'], [2, 0])
text = bytes(s.k.h.r(line, 24)).split(b'\0')[0].decode() if line else None
check(bool(line) and text.startswith('H'), f'D the status box is on and has its third line ("{text}")')
fr = s.play(3200, bpm=120)
ons = [0] * 16
for f in fr:
    for v in range(16):
        if U16(f, 0x22) >> v & 1:
            ons[min(U16(f, 0xA5A + 2 * v), 15)] += 1
line = s.k.call(s.sym['dg_dbg_line'], [2, 0])
text = bytes(s.k.h.r(line, 24)).split(b'\0')[0].decode() if line else None
check(ons[0] >= 4 and ons[2] >= 16 and ons[DGT] >= 6, f'D with the box on the pattern plays (kick {ons[0]} hats {ons[2]} DigiGlide {ons[DGT]}; line "{text}")')
print('OK' if ok_all else 'FAIL')
