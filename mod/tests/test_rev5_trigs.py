"""DigiGlide rev 5: stock trig features upstream of the note takeover. Trigs on steps 3 (C) and 7 (E) of track 1, each
case in its own session (a long emulator session drops events).
  A  retrig on step 3 (the step word's retrig flag; stock plays the note twice, ending the first note at the retrig
     and again at its own length): HOLD off, fast attack: the chord is struck twice and ends once, with the second
     note, on all its voices; HOLD on, pad: every hit strikes the chord and no note-off reaches any voice.
  B  probability (the track's trig default): 0 % plays nothing, 100 % plays both trigs.
  C  track mute ([FUNC] + [TRIG 1]): muted before PLAY nothing plays; muted under a chord HOLD keeps, the chord is
     released (stock sends a muted track no more notes, so nothing else would end it).
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_rev5_trigs.py [DIGIGLIDE.syx]"""
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


def run(tag, hold=0, atk=64, retrig=False, prob=None, mute=None):
    s = Session(img, tag='rt_' + tag, solo=True, reserve=0)
    s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=hold), atk=atk)
    for _ in range(3):
        s.k.tap('SYN')
    h = s.k.h
    s.trig(2, note=60, length=14)
    s.trig(6, note=64, length=14)
    if retrig:
        h.w(h.u32(A(0x42C5A9A0)) + 4, (0x8383).to_bytes(2, 'big'))
    if prob is not None:
        h.w(s.trig_defaults(0) + 16, bytes([prob]))
    if mute == 'pre':
        s.func_with(3, 0)
    fr = s.play(1500 if mute != 'mid' else 700, bpm=120)
    if mute == 'mid':
        st = len(h.sent)
        s.func_with(3, 0)
        h.frames(600)
        return ([(i, U16(f, 0x22)) for i, f in enumerate(fr) if U16(f, 0x22)],
                [(i, U16(f, 0x24)) for i, (f, _) in enumerate(h.sent[st:]) if U16(f, 0x24)])
    return ([(i, U16(f, 0x22)) for i, f in enumerate(fr) if U16(f, 0x22)],
            [(i, U16(f, 0x24)) for i, f in enumerate(fr) if U16(f, 0x24)])


on, off = run('retrig_fast', atk=0, retrig=True)
first = [x for x in off if x[0] < 1000]
check(len([x for x in on if x[0] < 1000]) == 2 and len(first) == 1 and first[0][1] == 0x1F and first[0][0] > on[1][0],
      f'A: retrig, HOLD off, fast attack: struck twice, released once on all 5 voices (attacks {on}, note-offs {[(i, hex(m)) for i, m in off]})')
on, off = run('retrig_hold', hold=1, retrig=True)
check(len(on) == 3 and all(m == 0x1F for _, m in on) and not off, f'A: retrig, HOLD on, pad: every hit strikes all 5 voices ({len(on)} attacks), no note-off reaches a voice (note-offs {[(i, hex(m)) for i, m in off]})')
on, off = run('prob0', prob=0)
check(not on and not off, f'B: probability 0 %: nothing plays ({len(on)} attacks)')
on, off = run('prob100', prob=100)
check(len(on) == 2 and all(m == 0x1F for _, m in on), f'B: probability 100 %: both trigs play as chords ({len(on)} attacks)')
on, off = run('mute_pre', mute='pre')
check(not on, f'C: the track muted before PLAY: nothing plays ({len(on)} attacks)')
on, off = run('mute_mid', hold=1, mute='mid')
check(len(on) >= 1 and off and off[0][1] == 0x1F, f'C: muted under a held chord (HOLD on): the chord is released (note-offs {[(i, hex(m)) for i, m in off[:3]]})')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
