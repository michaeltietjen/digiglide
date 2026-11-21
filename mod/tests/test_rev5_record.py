"""DigiGlide rev 5: recording. DigiGlide takes the track's notes in the audio interrupt, right before the frame goes
to the DSP; the sequencer and its live recorder are upstream and must still capture what is played.

Each case: live recording ([RECORD] + [PLAY]) of three keys in keyboard mode, [STOP]; the recorded pattern is then
copied into a fresh session and played (the emulator will not PLAY again in a session that made a recording gesture).
  A  stock OS: how many trigs three keys record, and the notes they play back (the reference).
  B  DigiGlide, HOLD off: as many trigs as stock records; playback goes through DigiGlide: each recorded trig is a
     chord on the note stock would play, nothing stock underneath, and each chord ends with its recorded length.
  C  DigiGlide, HOLD on: while recording the chord holds after the key is released; playback matches: no release
     between the chords; every trig strikes the held chord again (pad or fast attack) and it
     glides to the trig's chord; the strike does not restart the amp envelope (AMP RSET off in DigiGlide's voices); [STOP] releases it.
  D  grid recording ([RECORD] tapped, three trig keys): DigiGlide stores exactly the bytes stock stores, placing
     trigs sounds nothing, and the trigs play back as chords.
Step 1's trig does not play in the emulator's first bar, on stock either (PLAY starts just after it): the checks use
the trigs after it.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_rev5_record.py [DIGIGLIDE.syx]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import Session, latest, G, U16, Ui
from osver import A
from emu import panelin
import cfkit

img = sys.argv[1] if len(sys.argv) > 1 else latest()
print('image', os.path.basename(img))
ok = True
KEYS = (0x01, 0x04, 0x10)
MACH = int(os.environ.get('DG_MACH', '1'))             # the track's machine: 1 WAVETONE (default), 0 FM TONE


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


def setup(image, tag, hold, atk=64):
    s = Session(image, tag=tag, solo=True, reserve=0)
    if image:
        s.set_sound(Ui(voic=64, glid=3, drft=0, vib=0, hold=int(hold)), atk=atk, mach=MACH)
        for _ in range(3):
            s.k.tap('SYN')
    else:
        s.k.select(MACH, track=0)
    return s


def record_and_play(image, hold=False, atk=64):
    name = ('dg' if image else 'stock') + ('_hold' if hold else '') + ('' if atk == 64 else '_fast')
    s = setup(image, 'rr_' + name, hold, atk)
    k, h = s.k, s.k.h
    for st in range(128):
        k.call(A(0x40054690), [s.ctx0, st, 1, 0])
    pat = h.u32(A(0x42C5A9A0))
    k.tap('KEYB')

    def btn(g, m, fr=20):
        h.pc = panelin.buttons(h.m, h.profile, g, m); h.run(3_000_000); h.frames(fr)
    h.w(A(0x402A0DEC), cfkit.BE(120 * 120))
    btn(2, 0x04); btn(2, 0x0C); btn(2, 0x00)             # [RECORD] held, [PLAY]: live recording
    rec_offs = []
    for mask in KEYS:
        st = len(h.sent)
        btn(3, mask, fr=375); btn(3, 0x00, fr=375)
        rec_offs += [1 for f, _ in h.sent[st:] if U16(f, 0x24)]
    h.frames(300)
    btn(2, 0x10); btn(2, 0x00)                           # [STOP]
    trigs = [st for st in range(64) if h.r(pat + 2 * st + 1, 1)[0] & 1]
    data = bytes(h.r(pat, 131072))
    p = setup(image, 'rp_' + name, hold, atk)
    h2 = p.k.h
    h2.w(h2.u32(A(0x42C5A9A0)), data)
    names = []
    fr = p.play(3000, bpm=120, each=(lambda i: names.append(bytes(h2.r(p.sym['dg_name'], 16)).split(b'\0')[0].decode()))
                if image else None)
    st0 = len(h2.sent)
    h2.frames(1500)                                      # after [STOP]: the emulated UI acts on the key late; the release came
                                                         # 896 blocks after it on image 25, 907 on images 26 and 27 (900 was too few)
    after = [x for x, _ in h2.sent[st0:]]
    return dict(trigs=trigs, rec_offs=len(rec_offs), fr=fr, names=names, sess=p, after=after)


def onsets(fr):
    return [(i, [(v, U16(f, 2 + 2 * v) >> 8) for v in range(16) if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) == 0])
            for i, f in enumerate(fr) if U16(f, 0x22)]


st = record_and_play(None)
s_on = onsets(st['fr'][:2998])
s_notes = [vs[0][1] for _, vs in s_on]
check(len(st['trigs']) == 3 and len(s_notes) >= 2, f'A: stock records 3 keys as trigs on steps {[x + 1 for x in st["trigs"]]}; playback notes {s_notes}')

dg = record_and_play(img)
fr = dg['fr'][:2998]
d_on = onsets(fr)
roots = [min(n for _, n in vs[:4]) for _, vs in d_on]
seq = [n for n in ([dg['names'][0]] + [b for a, b in zip(dg['names'], dg['names'][1:]) if a != b]) if n]
check(len(dg['trigs']) == 3, f'B: DigiGlide on, HOLD off: 3 keys record 3 trigs (steps {[x + 1 for x in dg["trigs"]]}), as stock')
want = [G.NOTE_NAMES[n % 12].upper() + ' MAJ' for n in s_notes]
check(seq == want, f'B: playback goes through DigiGlide: chords {seq} on the notes stock plays back {s_notes}')
check(all(len(vs) == 5 and all(v < 5 for v, _ in vs) for _, vs in d_on),
      f'B: each recorded trig attacks DigiGlide\'s 5 voices and nothing else ({[len(vs) for _, vs in d_on]} voices)')
offs = [i for i, f in enumerate(fr) if U16(f, 0x24) & 0x1F]
check(len(offs) == len(d_on), f'B: each chord ends with its recorded length (note-offs at {offs}, attacks at {[i for i, _ in d_on]})')

dh = record_and_play(img, hold=True)
fr = dh['fr'][:2998]
h_on = onsets(fr)
offs = [i for i, f in enumerate(fr) if U16(f, 0x24) & 0x1F]
check(dh['rec_offs'] == 0, f'C: HOLD on, while recording: the chord holds after each key is released ({dh["rec_offs"]} note-off blocks)')
hseq = [n for n in ([dh['names'][0]] + [y for x, y in zip(dh['names'], dh['names'][1:]) if x != y]) if n]
check(len(dh['trigs']) == 3 and len(h_on) >= 2 and len(hseq) >= 2 and not offs,
      f'C: playback matches what was heard: no release between the chords; every trig strikes the held chord and it glides through {hseq} ({len(h_on)} attacks, note-offs {offs})')
w = [[U16(f, 2 + 2 * j) * 100 / 256 for j in range(5)] for f in fr]
i0 = h_on[0][0] if h_on else 0
jump = max(max(abs(a - b) for a, b in zip(w[i], w[i - 1])) for i in range(i0 + 2, len(w)))
rs = [U16(f, 0xDA + 146 * j + 134) for f in fr[i0 + 2:] for j in range(5)]
check(not any(rs), 'C: the amp envelope does not restart on a strike: AMP RSET is off in the record of every voice DigiGlide plays')
check(jump < 50, f'C: the recorded chords glide from one to the next (largest step {jump:.1f} cent a block)')
end = dh['fr'][2998:] + dh['after']
rel = [i for i, f in enumerate(end) if U16(f, 0x24) & 0x1F]
check(rel, f'C: [STOP] releases the held chord ({rel[0] if rel else "never"} blocks after the key)')
df = record_and_play(img, hold=True, atk=0)
f_on = onsets(df['fr'][:2998])
f_off = [i for i, f in enumerate(df['fr'][:2998]) if U16(f, 0x24) & 0x1F]
check(len(df['trigs']) == 3 and len(f_on) >= 2 and not f_off,
      f'C: HOLD on, a fast attack (AMP ATK 0): every recorded trig strikes the held chord again ({len(f_on)} attacks, no release)')


def grid(image):
    s = setup(image, 'rg_' + ('dg' if image else 'stock'), False)
    h = s.k.h
    pat = h.u32(A(0x42C5A9A0))
    before = bytes(h.r(pat, 131072))

    def btn(g, m, fr=20):
        h.pc = panelin.buttons(h.m, h.profile, g, m); h.run(3_000_000); h.frames(fr)
    btn(2, 0x04); btn(2, 0x00, fr=200)                   # [RECORD]: grid recording
    st0 = len(h.sent)
    for mask in KEYS:
        btn(3, mask, fr=120); btn(3, 0x00, fr=200)
    h.frames(700)
    ons = [i for i, (f, _) in enumerate(h.sent[st0:]) if U16(f, 0x22)]
    after = bytes(h.r(pat, 131072))
    return {i: after[i] for i in range(len(after)) if after[i] != before[i]}, ons, after


g_st, _, _ = grid(None)
g_dg, g_ons, g_data = grid(img)
check(len(g_st) > 6 and g_dg == g_st, f'D: grid recording stores the same {len(g_st)} pattern bytes with DigiGlide on as stock does')
check(not g_ons, f'D: placing trigs sounds nothing (note-on blocks {g_ons[:4]})')
p = setup(img, 'rgp_dg', False)
p.k.h.w(p.k.h.u32(A(0x42C5A9A0)), g_data)
g_on = onsets(p.play(1200, bpm=120))
check(len(g_on) >= 2 and all(len(vs) == 5 for _, vs in g_on), f'D: the placed trigs play back as chords ({[len(vs) for _, vs in g_on]} voices)')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
