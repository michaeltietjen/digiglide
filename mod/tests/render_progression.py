"""Render the 4-chord progression (C maj, A min, F maj, G maj; one chord per bar, 120 BPM) on GLIDE and on stock OS,
check the milestone's slide criteria, and write WAVs + pitch-trace plots.

    ~/dn2-workspace/repos/digikit/.venv/bin/python render_progression.py M3 [--glid 1bar] [--curv ease_out] [--drft 0]
        [--img GLIDE.syx]

How the audio is made (both runs identical except the OS):
  1. The real OS runs in the ColdFire emulator (stock 1.11, or the GLIDE image) with a 4-bar pattern on track 1 and every
     other track empty. GLIDE: one trig per bar (LEN INF, last bar 16 steps), the progression from GLIDE's test table.
     Stock: the same chords played by tracks 1-3, one chord tone each (root position, LEN 16 steps), same steps.
  2. From every frame the OS sends we take what the sequencer / GLIDE decides: note words, note-on / note-off masks,
     velocities, voice -> track. The emulated OS's parameter smoothers never converge (they ramp from 0 after load), so
     the sound record of every voice is the same explicit FM TONE pad patch from the stock parameter table (dn2synth).
  3. The SHARC emulator (stock section 7 -- GLIDE has no DSP code) renders those frames; per-voice buffers give a
     DSP-side pitch trace of the GLIDE voices.
"""
import argparse, json, math, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import glidekit as GK
from glidekit import Session, params, U16
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import dn2paths as P, dn2frame as D, dn2synth as S

ap = argparse.ArgumentParser()
ap.add_argument('milestone')
ap.add_argument('--img')
ap.add_argument('--glid', default='1bar')
ap.add_argument('--curv', default='ease_out')
ap.add_argument('--drft', type=int, default=0)
ap.add_argument('--voic', type=int, default=0)
ap.add_argument('--bpm', type=int, default=120)
ap.add_argument('--only', choices=('glide', 'stock'))
ap.add_argument('--sound', choices=('fmpad', 'wavepad'), default='fmpad')
a = ap.parse_args()

OUT = os.path.expanduser(f'~/glide/renders/{a.milestone}')
os.makedirs(OUT, exist_ok=True)
CHORDS = [('C3', 'maj', (0, 4, 7)), ('A2', 'min', (0, 3, 7)), ('F2', 'maj', (0, 4, 7)), ('G2', 'maj', (0, 4, 7))]
BAR = int(round(4 * 60 / a.bpm * 48000 / 32))              # blocks per bar
TAIL = BAR * 3 // 2
STEPS = (0, 16, 32, 48)
NAME = 'Cmaj-Amin-Fmaj-Gmaj'


def capture(img):
    s = Session(img, tag=a.milestone.lower() + ('_glide' if img else ''), reserve=4 if img else 0)
    if img:
        for st, ln in zip(STEPS, (127, 127, 127, 78)):
            s.trig(st, note=60, length=ln)
        s.progression([params(r, c, voic=a.voic, glid=a.glid, curv=a.curv, drft=a.drft) for r, c, _ in CHORDS])
    else:
        # stock chords: tracks 1-3 each play one chord tone per bar (root position), LEN 16 steps -> hard changes
        for st, (r, c, iv) in zip(STEPS, CHORDS):
            for t, i in enumerate(iv):
                s.trig(st, note=GK.midi(r) + i, length=78, t=t)
    k = s.k
    k.h.w(0x402A0DEC, GK.BE(a.bpm * 120))
    start = len(k.h.sent)
    k.h.tap(GK.cfkit.PLAY)
    k.h.frames(4 * BAR + TAIL)
    k.h.tap(GK.cfkit.STOP); k.h.frames(4)
    fr = [x[:2688] for x, _ in k.h.sent[start:]]
    return fr, s


PATCHES = {
    'fmpad': ('FMTONE', (('AMP.ATK', 34), ('AMP.HOLD', 127), ('AMP.DEC', 100), ('AMP.SUS', 112), ('AMP.REL', 72),
                         ('A LEVEL', 44), ('B LEVEL', 26), ('A ENV DECAY', 110), ('B ENV DECAY', 110), ('A ENV END', 70),
                         ('B ENV END', 60), ('FILTER.FREQ', 100), ('REVERB SEND', 52), ('CHORUS SEND', 30))),
    # WAVETONE pad: two oscillators on different waves, a little phase distortion and drift, low-pass with a touch of
    # resonance, slow attack / long release, chorus + reverb.
    'wavepad': ('WAVETONE', (('SYN.WAV1', 30), ('SYN.WAV2', 70), ('SYN.PD1', 40), ('SYN.PD2', 60), ('SYN.LEV1', 96),
                             ('SYN.LEV2', 72), ('SYN.DRIF', 18), ('FILTER.FREQ', 78), ('FILTER.RESO', 18),
                             ('AMP.ATK', 40), ('AMP.HOLD', 127), ('AMP.DEC', 100), ('AMP.SUS', 116), ('AMP.REL', 76),
                             ('FX.REV', 64), ('FX.CHR', 44))),
}


def pad():
    machine, knobs = PATCHES[a.sound]
    snd = S.Sound(machine)
    for n, v in knobs:
        try:
            snd.set(n, v)
        except KeyError:
            print('  (no parameter', n, ')')
    return snd


def hybrid(osframes):
    song = S.Song(bpm=a.bpm)
    snd = pad()
    for v in range(16):
        song.assign(v, snd)
    out = []
    for f in osframes:
        b = bytearray(song.base)
        for o, n in ((0x02, 32), (0x22, 8), (0x34, 32), (0xA5A, 32)):
            b[o:o + n] = f[o:o + n]
        out.append(D.swap16(bytes(b)))
    return out


def render(packets, trace_voices):
    sec7, snap = P.snap('stock')
    fr = D.Frame(D.image_from_sec7(sec7), snap)
    bufs = {v: [] for v in trace_voices}

    def on_block(k, frame):
        m = frame.s.mem
        for v in trace_voices:
            bufs[v].extend(m.rf(D.VOICEBUF + 256 * v + 4 * i) for i in range(32))
    L, R, _ = D.render(fr, packets, on_block=on_block if trace_voices else None)
    return np.array(L), np.array(R), {v: np.array(b) for v, b in bufs.items()}


def dsp_pitch(x, hop=1024, win=2048, fs=48000):
    t, p = [], []
    for s0 in range(0, len(x) - win, hop):
        seg = x[s0:s0 + win] - np.mean(x[s0:s0 + win])
        if np.sqrt(np.mean(seg ** 2)) < 1e-5:
            t.append((s0 + win / 2) / fs); p.append(np.nan); continue
        c = np.correlate(seg, seg, 'full')[win - 1:]
        lo, hi = int(fs / 1200), int(fs / 50)
        lag = lo + int(np.argmax(c[lo:hi]))
        if 1 <= lag < len(c) - 1:
            y0, y1, y2 = c[lag - 1], c[lag], c[lag + 1]
            den = y0 - 2 * y1 + y2
            lag = lag + (0.5 * (y0 - y2) / den if den else 0)
        t.append((s0 + win / 2) / fs); p.append(69 + 12 * math.log2(fs / lag / 440))
    return np.array(t), np.array(p)


results = {}
img = a.img or GK.latest()
runs = [('glide', img), ('stock', None)]
if a.only:
    runs = [r for r in runs if r[0] == a.only]
for tag, im in runs:
    cache = os.path.join(OUT, f'.{tag}_frames.bin')
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(im[:-4] + '/section_3.bin' if im else cache) - 1:
        raw = open(cache, 'rb').read(); osf = [raw[i:i + 2688] for i in range(0, len(raw), 2688)]
        print(f'{tag}: {len(osf)} OS frames (cached)')
    else:
        osf, _ = capture(im)
        open(cache, 'wb').write(b''.join(osf))
        print(f'{tag}: captured {len(osf)} OS frames')
    tv = (0, 1, 2, 3) if tag == 'glide' else ()
    L, R, vb = render(hybrid(osf), tv)
    results[tag] = dict(osf=osf, L=L, R=R, vb=vb)
    print(f'{tag}: rendered {len(L) / 48000:.1f} s, peak {np.max(np.abs(np.r_[L, R])):.4f}')

# one gain for both files (no per-file normalising: the A/B stays level-honest)
peak = max(np.max(np.abs(np.r_[r['L'], r['R']])) for r in results.values())
gain = 10 ** (-1 / 20) / peak if peak > 0 else 1.0
sfx = '' if a.sound == 'fmpad' else '_' + a.sound
names = {'glide': f'glide_{NAME}_glid{a.glid}{sfx}.wav', 'stock': f'stock_{NAME}{sfx}.wav'}
for tag, r in results.items():
    D.write_wav(os.path.join(OUT, names[tag]), r['L'] * gain, r['R'] * gain)

# ---- checks + traces
ok = True
report = []
def check(c, msg):
    global ok
    ok &= bool(c)
    report.append(('ok   ' if c else 'FAIL ') + msg)
    print(('  ok   ' if c else '  FAIL ') + msg)

if 'glide' in results:
    osf = results['glide']['osf']
    ons = [(i, v, U16(f, 2 + 2 * v) / 256) for i, f in enumerate(osf) for v in range(4) if U16(f, 0x22) >> v & 1]
    first = min(i for i, *_ in ons)
    check(all(i == first for i, *_ in ons), f'GLIDE: one attack only (block {first}), chords 2-4 glide')
    other = [(i, v) for i, f in enumerate(osf) for v in range(4, 16) if U16(f, 0x22) >> v & 1]
    check(not other, f'GLIDE run: no other voice plays {other[:3]}')
    trace = {v: np.array([U16(f, 2 + 2 * v) / 256 for f in osf]) for v in range(4)}
    glid_blocks = GK.glid_blocks(a.glid, a.bpm)
    for c in range(1, 4):
        t0 = first + c * BAR
        for v in (0, 1, 2):
            tr = trace[v][t0 - 5:t0 + glid_blocks - 1]    # this chord's slide only (the next trig follows at once)
            if tr[0] == tr[-1]:
                continue                                   # common tone: holds
            r, _, iv = CHORDS[c]
            tones = [GK.midi(r) + i for i in iv]
            end = tr[-1]
            dist = min(abs((end - t + 6) % 12 - 6) for t in tones)
            mono = np.all(np.diff(tr) >= 0) or np.all(np.diff(tr) <= 0)
            frac = (tr[5 + glid_blocks // 2] - tr[0]) / (end - tr[0])
            check(mono and dist < 0.02 and 0.05 < frac < 0.95,
                  f'chord {c + 1} voice {v}: {tr[0]:.2f} -> {end:.2f} (a chord tone, off by {dist:.3f}), monotonic, '
                  f'{frac:.0%} of the way at half of GLID {a.glid} ({glid_blocks} blocks)')
    # DSP side: what the synth actually played follows the words
    for v in (0, 1, 2):
        t, p = dsp_pitch(results['glide']['vb'][v])
        for c in range(4):
            tb = first + (c + 1) * BAR - BAR // 10                  # late in each bar (slide done for GLID <= 1 bar)
            want = trace[v][tb]
            got = p[np.argmin(np.abs(t - tb * 32 / 48000))]
            check(abs(got - want) < 0.15, f'DSP voice {v} bar {c + 1}: plays {got:.2f}, frame says {want:.2f}')
if 'stock' in results:
    osf = results['stock']['osf']
    ons = [(i, v, U16(f, 2 + 2 * v) / 256) for i, f in enumerate(osf) for v in range(16)
           if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) in (0, 1, 2)]
    want = sorted(GK.midi(r) + i for r, _, iv in CHORDS for i in iv)
    check(sorted(n for *_, n in ons) == want, f'stock: 4 chords x 3 tones = {len(ons)} attacks, notes as written')
    extra = [e for e in ons if e[0] > 4 * BAR + 10]
    check(not extra, f'stock: nothing plays after bar 4 {extra[:3]}')

# plot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)
cols = ['#3b6fb6', '#d1495b', '#2e9e6a', '#8d6cab']
if 'glide' in results:
    osf = results['glide']['osf']
    tt = np.arange(len(osf)) * 32 / 48000
    for v in range(4):
        tr = np.array([U16(f, 2 + 2 * v) / 256 for f in osf]); on = tr > 0
        axes[0].plot(tt[on], tr[on], color=cols[v], lw=1.6, label=f'voice {v + 1} (frame note word)')
        t, p = dsp_pitch(results['glide']['vb'][v])
        axes[0].plot(t, p, '.', color=cols[v], ms=2.5, alpha=.6)
    axes[0].set_title(f'GLIDE ({os.path.basename(img)}): GLID {a.glid}, CURV {a.curv}, DRFT {a.drft} '
                      f'-- lines = note words sent, dots = pitch measured in the DSP voice buffers')
if 'stock' in results:
    osf = results['stock']['osf']
    tt = np.arange(len(osf)) * 32 / 48000
    for i, f in enumerate(osf):
        for v in range(16):
            if U16(f, 0x22) >> v & 1 and U16(f, 0xA5A + 2 * v) in (0, 1, 2):
                axes[1].plot([tt[i], tt[i] + 2], [U16(f, 2 + 2 * v) / 256] * 2, color='#555', lw=1.6)
    axes[1].set_title('Stock OS 1.11: same chords on tracks 1-3, one tone each (hard changes, no glide)')
for ax in axes:
    ax.set_ylabel('MIDI note'); ax.grid(alpha=.3)
    for c in range(5):
        ax.axvline(c * 2 * 120 / a.bpm, color='#bbb', lw=.8)
    ax.set_yticks(range(40, 62, 2))
axes[0].legend(fontsize=7, loc='upper right'); axes[1].set_xlabel('seconds')
fig.tight_layout()
png = os.path.join(OUT, f'pitch_traces_{NAME}{sfx}.png')
fig.savefig(png, dpi=130)
open(os.path.join(OUT, 'checks.txt'), 'w').write('\n'.join(report) + '\n' + ('OK' if ok else 'FAIL') + '\n')
print('files:', OUT)
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
