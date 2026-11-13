"""DigiGlide M5 (spec rev 3): DSP renders, A/B against stock, the M5 checks, and the listening WAVs.

Every render is the real OS (ColdFire emulator: DIGIGLIDE_<N>, or stock 1.11) deciding note words, note-on / note-off
masks, velocities, voice -> track and DigiGlide's per-voice pan, rendered by the SHARC emulator (stock section 7:
DigiGlide has no DSP code) with an explicit sound record: the emulated OS's parameter smoothers never converge (as M3).
The sound is BRICKGLIDE PAD (sounds/BRICKGLIDE_PAD.json): WAVETONE saws a few cents apart, slow attack, long release,
reverb / delay / chorus sends; its kit FX for the renders: a longer reverb and the delay on a dotted 1/4.

Track 1 = a DigiGlide sound with BRICKGLIDE PAD's values (KEY C, SCL minor, CHRD Seventh, VCNT 5, BASS root, SPRD 77,
DRFT 8, VIB 4, GLID 1 bar, PATH Smooth), VOICES 6, 90 BPM. Patterns (DEG p-locked per trig):
  progression  I VI IV V (i VI iv v in C minor), a chord every 2 bars (steps 1 33 65 97), LEN INF, last 16 steps
  move_<m>     the same, the MOVE p-locked on the second chord (step 33: step 9 has no trig in this layout)
  path_<p>     one change, i -> VI on step 17 (GLID 1 bar), each PATH
  midglide     GLID 4 bars, a trig every bar (steps 1 17 33 49): each chord arrives while the last is still gliding
  stock        the progression's pattern on stock OS (the trig note alone: what the track plays without DigiGlide)
Checks (spec M5, owner's list):
  - the progression's DSP pitch follows the M1 model within 1 cent per voice and block: the note words sent vs the
    model (exact), plus the DSP's pitch vs those words (each voice rendered alone as a sine 3 octaves up, its
    fundamental demodulated; the DSP takes a note word a block later, Q2);
  - no pitch step over 5 cents between consecutive blocks sent to the DSP, in every DigiGlide render except the
    Semitones and Scale steps paths;
  - two renders of the same frames are bit-identical;
  - VCNT OFF: the same progression with the sound's VCNT OFF gives frames and a render identical to stock.
    ~/dn2-workspace/repos/digikit/.venv/bin/python render_m5.py [DIGIGLIDE.syx] [--only name,name]
"""
import argparse, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dgkit import Session, latest, G, U16, word, edges, model
import osver
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import dn2paths as P, dn2frame as D, dn2synth as S

ap = argparse.ArgumentParser()
ap.add_argument('img', nargs='?')
ap.add_argument('--only')
ap.add_argument('--wavs', action='store_true', help='write every WAV from the saved renders, one gain for all')
a = ap.parse_args()
img = a.img or latest()
OUT = os.path.expanduser('~/glide/renders/M5')
CACHE = os.path.join(OUT, '.cache')
os.makedirs(CACHE, exist_ok=True)
BPM = 90
BAR = int(round(240 / BPM * 1500))                       # 4000 blocks
STEP = BAR // 16
LOOP = 8 * BAR - 50          # the pattern is 128 steps (8 bars): stop before it plays step 1 again
PAD = json.load(open(os.path.expanduser('~/glide/sounds/BRICKGLIDE_PAD.json')))
BASE = G.Params(**PAD['digiglide'])
NV = 5
ok = True
log_lines = []


def check(c, msg):
    global ok
    ok &= bool(c)
    line = ('  ok   ' if c else '  FAIL ') + msg
    print(line, flush=True)
    log_lines.append(line)


# ---------------------------------------------------------------- patterns
def pattern(name):
    """-> (trigs [(step, length, locks)], blocks, base params)"""
    if name in ('progression', 'stock', 'vcnt_off') or name.startswith('move_'):
        mv = [m.lower() for m in G.MOVES].index(name[5:].replace('_', ' ')) if name.startswith('move_') else 0
        tr = [(st, 78 if st == 96 else 127, dict(deg=d, **({'move': mv} if mv and st == 32 else {})))
              for st, d in zip((0, 32, 64, 96), (0, 5, 3, 4))]
        return tr, LOOP, BASE
    if name.startswith('path_'):
        pa = [x.lower() for x in G.PATHS].index(name[5:].replace('_', ' '))
        return [(0, 127, dict(deg=0)), (16, 78, dict(deg=5))], 5 * BAR, BASE.copy(path=pa)
    if name == 'midglide':
        return ([(st, 78 if st == 48 else 127, dict(deg=d)) for st, d in zip((0, 16, 32, 48), (0, 5, 3, 4))],
                LOOP, BASE.copy(glid=7))
    raise KeyError(name)


def capture(name, log_trigs=False):
    """the OS's frames for a pattern (cached by image)."""
    im = None if name == 'stock' else img
    stamp = os.path.basename(im)[:-4] if im else 'stock' + ('' if osver.OS == '1.11' else '_' + osver.OS)
    cache = os.path.join(CACHE, f'{name}_{stamp}.bin')
    meta = cache[:-4] + '.json'
    if os.path.exists(cache) and (not log_trigs or os.path.exists(meta)):
        raw = open(cache, 'rb').read()
        return [raw[i:i + 2688] for i in range(0, len(raw), 2688)], None, json.load(open(meta)) if log_trigs else None
    tr, nb, base = pattern(name)
    s = Session(im, tag='m5_' + name)
    if im:
        s.set_sound(base, on=name != 'vcnt_off')
    else:
        s.k.select(1, track=0)
    for st, ln, lk in tr:
        s.trig(st, note=60, length=ln)
        if im and name != 'vcnt_off':
            s.lock(st, **lk)
    log = s.trig_log() if log_trigs else None
    fr = [bytes(f[:2688]) for f in s.play(nb, bpm=BPM, each=log)]
    open(cache, 'wb').write(b''.join(fr))
    if log_trigs:
        ons, _ = edges(fr)
        isr = log.isr_blocks()
        meta_d = dict(trig_blocks=[b + ons[0] - isr[0] for b in isr], tempo=s.dg()['last_tempo'])
        json.dump(meta_d, open(meta, 'w'))
        return fr, s, meta_d
    return fr, s, None


# ---------------------------------------------------------------- sounds and renders
def sound(kind):
    snd = S.Sound('WAVETONE')
    if kind == 'pad':
        for _, v in PAD['sound_slots'].items():
            pass
        for label, v in PAD['sound_slots'].items():
            slot = int(label.split('(')[1].rstrip(')'))
            snd.set(slot, int(v, 16))
        snd.set('FILTER.FREQ', 84)
    else:                                                 # a plain sine: one oscillator at the PRIM table's sine end
        for n, v in (('SYN.WAV1', 120), ('SYN.LEV1', 100), ('SYN.LEV2', 0), ('SYN.NLEV', 0), ('SYN.DRIF', 0),
                     ('FILTER.FREQ', 127), ('FILTER.RESO', 0), ('AMP.ATK', 0), ('AMP.HOLD', 127), ('AMP.SUS', 127),
                     ('AMP.REL', 60), ('FX.REV', 0), ('FX.DEL', 0), ('FX.CHR', 0)):
            snd.set(n, v)
    return snd


MEAS_UP = 36      # the sine render plays every note word 3 octaves up: the 8-sample sine fit needs w well above 0
                  # (at C2, 65 Hz, neighbouring float32 samples are too alike and the fit reads 0 Hz)


def hybrid(osframes, kind, solo=None):
    song = S.Song(bpm=BPM)
    if kind == 'pad':
        for n, v in (('Reverb.DEC', 0x5800), ('Reverb.PRE', 0x1800), ('Delay.TIME', 0x2000), ('Delay.FDBK', 0x3000),
                     ('Delay.LPF', 0x4800)):
            try:
                song.set_fx(n, v)
            except KeyError:
                print('  (no FX parameter', n, ')')
    snd = sound(kind)
    for v in range(16):
        song.assign(v, snd)
    out = []
    for f in osframes:
        b = bytearray(song.base)
        for o, n in ((0x02, 32), (0x22, 8), (0x34, 32), (0xA5A, 32)):
            b[o:o + n] = f[o:o + n]
        if solo is not None:                              # only this voice sounds
            for o in (0x22, 0x26):
                b[o:o + 2] = (int.from_bytes(b[o:o + 2], 'big') & (1 << solo)).to_bytes(2, 'big')
        if kind == 'sine':
            for v in range(16):
                w = int.from_bytes(f[2 + 2 * v:4 + 2 * v], 'big')
                if w:
                    b[2 + 2 * v:4 + 2 * v] = min(0x7F00, w + (MEAS_UP << 8)).to_bytes(2, 'big')
        if kind == 'pad':
            for v in range(6):
                o = 0xDA + 146 * v + 128
                b[o:o + 2] = f[o:o + 2]
        out.append(D.swap16(bytes(b)))
    return out


def render(packets, trace=()):
    sec7, snap = P.snap('stock')
    fr = D.Frame(D.image_from_sec7(sec7), snap)
    bufs = {v: [] for v in trace}

    def on_block(k, frame):
        m = frame.s.mem
        for v in trace:
            bufs[v].extend(m.rf(D.VOICEBUF + 256 * v + 4 * i) for i in range(32))
    L, R, _ = D.render(fr, packets, on_block=on_block if trace else None)
    return np.array(L), np.array(R), {v: np.array(b, float) for v, b in bufs.items()}


def sine_midi(x, fs=48000, win=8):
    num = x[1:-1] * (x[:-2] + x[2:])
    den = 2 * x[1:-1] ** 2
    k = np.ones(win)
    c = np.clip(np.convolve(num, k, 'same') / np.maximum(np.convolve(den, k, 'same'), 1e-30), -1, 1)
    m = 69 + 12 * np.log2(np.maximum(np.arccos(c) * fs / (2 * math.pi), 1e-3) / 440)
    return np.concatenate([[np.nan], m, [np.nan]])


def dsp_vs_words(x, fr, v, W=1920, H=256, delay=44):
    """{frame: the DSP's pitch minus voice v's sent note word, in cents} from a solo render x (see the progression
    check). delay: a word reaches the DSP a block later, 11 to 12 samples in."""
    n = len(x)
    w = np.array([word(f, v) for f in fr], float) / 256 + MEAS_UP
    fb = 440 * 2 ** ((w - 69) / 12)
    f = fb[np.clip((np.arange(n) - delay) // 32, 0, len(fr) - 1)]
    z = x * np.exp(-2j * np.pi * np.cumsum(f) / 48000)
    ang = np.unwrap(np.angle(np.convolve(z, np.ones(W) / W, 'same')))
    out = {}
    for b in range(len(fr)):
        s_ = b * 32 + 16 + delay
        if s_ - H >= W and s_ + H + W < n and fb[b] > 0:
            d = (ang[s_ + H] - ang[s_ - H]) / (2 * H) * 48000 / (2 * math.pi)
            out[b] = 1200 * math.log2((fb[b] + d) / fb[b])
    return out


def max_step(fr):
    """largest change between consecutive frames of any DigiGlide voice's note word, in cents (while it sounds)."""
    w = np.array([[word(f, v) for v in range(6)] for f in fr], float) * 100 / 256
    gate = np.zeros_like(w, bool)
    on = np.zeros(6, bool)
    for i, f in enumerate(fr):
        for v in range(6):
            if (U16(f, 0x22) >> v) & 1:
                on[v] = True
            if (U16(f, 0x24) >> v) & 1:
                on[v] = False
        gate[i] = on
    d = np.abs(np.diff(w, axis=0))
    both = gate[1:] & gate[:-1]
    return float(d[both].max()) if both.any() else 0.0


renders = {}


def wav(name, fr):
    L, R, _ = render(hybrid(fr, 'pad'))
    renders[name] = (L, R)
    np.savez(os.path.join(CACHE, name + '.npz'), L=L, R=R)
    return L, R


wanted = set(a.only.split(',')) if a.only else None
want = lambda n: wanted is None or n in wanted

# ---------------------------------------------------------------- 1, A/B, the checks on the progression
if want('progression'):
    dg, s, meta = capture('progression', log_trigs=True)
    st, _, _ = capture('stock')
    ons, offs = edges(dg)
    trig_blocks = meta['trig_blocks']
    check(len(trig_blocks) == 4, f'progression: 4 DigiGlide trigs at blocks {trig_blocks} (90 BPM, a bar = {BAR})')
    b0 = trig_blocks[0]
    ev = {}
    for k_, b in enumerate(trig_blocks):
        tr, _, _ = pattern('progression')
        ev.setdefault(b - b0, []).append(('trig', tr[k_][0], BASE.copy(**tr[k_][2]), 60))
    for b in offs:
        if b > b0:
            ev.setdefault(b - b0, []).append(('off',))
    n = len(dg) - b0 - 4
    mp, mg, _ = model(ev, n, meta['tempo'])
    mp = np.array(mp)[:, :NV] / 100.0
    L1, R1 = wav('progression', dg)
    L2, R2, _ = render(hybrid(dg, 'pad'))
    check(np.array_equal(L1, L2) and np.array_equal(R1, R2), f'two renders of the same frames are bit-identical '
                                                             f'({len(L1) / 48000:.1f} s)')
    wav('stock', st)
    # DSP pitch vs the M1 model = (note words the OS sent vs the model, exact) + (the DSP's pitch vs those words,
    # measured). The test sine is WAVETONE's sine end, which still carries 3rd and 5th harmonics, so the DSP's pitch
    # is read by demodulating the fundamental: each voice rendered alone (3 octaves up), multiplied by the phase
    # the sent words predict, smoothed over 40 ms; the residual phase slope is the DSP's deviation in cents.
    # Windows that touch the voice's own note-on / note-off are left out (the restart is not a pitch).
    words = np.array([[word(f, v) for v in range(NV)] for f in dg], float) / 256.0
    worst_w, worst_d, total = 0.0, 0.0, 0
    for v in range(NV):
        dw = [abs(words[b0 + b, v] - mp[b, v]) * 100 for b in range(n - 2) if mg[b][v] and b >= 64]
        worst_w = max(worst_w, max(dw))
        Ls, Rs, _ = render(hybrid(dg, 'sine', solo=v))
        r = dsp_vs_words((Ls.astype(float) + Rs.astype(float)) / 2, dg, v)
        edges_v = [i for i, f in enumerate(dg) if (U16(f, 0x22) | U16(f, 0x24)) >> v & 1]
        near = np.zeros(len(dg), bool)
        for e in edges_v:
            near[max(0, e - 80):e + 80] = True
        d = np.array([abs(r[b0 + b]) for b in range(64, n - 2)
                      if mg[b][v] and (b0 + b) in r and not near[b0 + b]])
        worst_d = max(worst_d, float(d.max()))
        total += len(d)
        print(f'      voice {v + 1}: words vs model largest {max(dw):.3f} cent; DSP vs words {len(d)} blocks, '
              f'median {np.median(d):.3f}, largest {d.max():.3f} cent')
    worst = worst_w + worst_d
    check(worst <= 1.0, f'progression: each voice\'s DSP pitch within 1 cent of the M1 model ({total} voice-blocks: '
                        f'words vs model {worst_w:.3f} + DSP vs words {worst_d:.3f} = {worst:.3f} cent at most)')
    check(max_step(dg) <= 5.0, f'progression: largest step sent to the DSP {max_step(dg):.3f} cent (limit 5)')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 5))
    t = np.arange(n) / 1500.0
    for v in range(NV):
        ax.plot(t, np.where(np.array(mg)[:, v], mp[:, v], np.nan), lw=3, alpha=0.35, label=f'voice {v + 1}: M1 model')
        bl = np.arange(0, n - 2, 25)
        ax.plot(t[bl], np.where(np.array(mg)[bl, v], words[b0 + bl, v], np.nan), '.', ms=2, color='k')
    ax.set_xlabel('seconds'); ax.set_ylabel('MIDI note (C4 = 60)')
    ax.set_title('M5: note words sent to the DSP (dots) over the M1 model (lines): i VI iv v, C minor, 90 BPM, GLID 1 bar')
    ax.legend(fontsize=7, loc='lower right'); fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'pitch_dsp_vs_model.png'), dpi=110)

if want('vcnt_off'):
    off_fr, _, _ = capture('vcnt_off')
    st, _, _ = capture('stock')
    # after STOP (the last 4 frames) the OS puts back the demo project's own tempo (81 BPM) over the 90 the harness
    # set; when that lands within those frames is UI timing, on stock as on DigiGlide: that word is left out there
    strip = lambda f, i: f if i < len(f_) - 4 else f[:0xD8] + f[0xDA:]
    f_ = off_fr
    same = len(off_fr) == len(st) and all(strip(x, i) == strip(y, i) for i, (x, y) in enumerate(zip(off_fr, st)))
    La, Ra, _ = render(hybrid(off_fr, 'pad'))
    Lb, Rb = renders['stock'] if 'stock' in renders else render(hybrid(st, 'pad'))[:2]
    check(same and np.array_equal(La, Lb) and np.array_equal(Ra, Rb),
          f'VCNT OFF: frames ({len(off_fr)}) and render identical to stock OS')

# ---------------------------------------------------------------- 2, 3, 4
for mv in range(1, 10):
    name = 'move_' + G.MOVES[mv].lower().replace(' ', '_')
    if not want(name) and not want('moves'):
        continue
    fr, _, _ = capture(name)
    wav(name, fr)
    check(max_step(fr) <= 5.0, f'{name}: largest step {max_step(fr):.3f} cent')
for pa in range(10):
    name = 'path_' + G.PATHS[pa].lower().replace(' ', '_')
    if not want(name) and not want('paths'):
        continue
    fr, _, _ = capture(name)
    wav(name, fr)
    ms = max_step(fr)
    if pa in (G.SEMITONES, G.SCALE_STEPS):
        print(f'  --   {name}: largest step {ms:.1f} cent (steps by design)')
    else:
        check(ms <= 5.0, f'{name}: largest step {ms:.3f} cent')
if want('midglide'):
    fr, _, _ = capture('midglide')
    wav('midglide', fr)
    check(max_step(fr) <= 5.0, f'midglide: largest step {max_step(fr):.3f} cent')

# ---------------------------------------------------------------- files (one gain for all: loudness compares)
if log_lines:
    open(os.path.join(OUT, 'checks.txt'), 'a').write('\n'.join(log_lines) + '\n')
if a.wavs:
    import glob
    for f in sorted(glob.glob(os.path.join(CACHE, '*.npz'))):
        z = np.load(f)
        renders[os.path.basename(f)[:-4]] = (z['L'], z['R'])
    peak = max(np.max(np.abs(np.r_[L, R])) for L, R in renders.values())
    gain = 10 ** (-1 / 20) / peak
    for name, (L, R) in renders.items():
        D.write_wav(os.path.join(OUT, f'{name}.wav'), L * gain, R * gain)
    order = sorted(n for n in renders if n.startswith('path_'))
    if order:
        gap = np.zeros(24000)
        cat = [np.concatenate([np.r_[renders[n][c], gap] for n in order]) for c in (0, 1)]
        D.write_wav(os.path.join(OUT, 'paths_all.wav'), cat[0] * gain, cat[1] * gain)
    print(f'{len(renders)} WAVs, shared gain {gain:.3f}')
print('files:', OUT)
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
