"""Build 29: five FM TONE sounds for DigiGlide tracks (coupled drone networks on four operators), rendered in the SHARC
emulator. Every value is a row of the stock parameter table (dn2synth). How a render is made:
  1. b29_capture.py: the OS (image 29) in the ColdFire emulator plays a DigiGlide track, two chords of four bars each,
     twice round. From its frames come the note words (the glides, DRFT, VIB), the gates and the velocities.
  2. Here every voice's sound record is the sound below. A sound's LFO is not the stock LFO (it runs in the ColdFire
     and has not been made to run in the emulator, notes/build_log.md "DRONE PULSE"): the destination's word is
     written into the voice records block by block, a triangle of the stated depth and period. So the LFO settings
     in the sheet are what the render plays, not a check of the stock LFO's own scaling.
  3. The SHARC emulator (stock DSP image) renders the frames. Reverb is the kit's default with the send below.
    ~/dn2-workspace/repos/digikit/.venv/bin/python b29_patches.py NAME [...]    (still chain ring bells beat pure)
Writes ~/glide/renders/b29/NAME.wav and ~/glide/sounds/b29/NAME.json."""
import json, math, os, sys, wave
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
import dn2paths as P, dn2frame as D, dn2synth as S

OUT = os.path.expanduser('~/glide/renders/b29')
SND = os.path.expanduser('~/glide/sounds/b29')
OUT_WAV = OUT                                           # where render() writes (b33_patches.py: renders/b33)
BAR = 3000                                              # blocks a bar at 120 BPM
R = lambda v: ('raw', v)                                # a stored word, where a knob step is too coarse
OFS = lambda thousandths: R(0x4000 + round(thousandths * 16.384))   # a ratio offset, in 1/1000 of the ratio

# name: (title, what it is, knobs, couple, lfo, DigiGlide settings, capture)
# lfo: (destination row, centre raw, depth raw, period in bars) or None
SOUNDS = {}


def sound(name):
    title, text, knobs, couple, lfo, dg, cap = SOUNDS[name]
    snd = S.Sound('FMTONE')
    for k, v in knobs.items():
        if isinstance(v, tuple):
            snd.slots[snd.names[k.upper()]] = v[1]
        else:
            snd.set(k, v)
    return snd


def frames(name):
    title, text, knobs, couple, lfo, dg, cap = SOUNDS[name]
    raw = open(f'{OUT}/cap_{cap}.bin', 'rb').read()
    osf = [raw[i:i + 2688] for i in range(0, len(raw), 2688)]
    snd = sound(name)
    song = S.Song(bpm=120)
    for v in range(16):
        song.assign(v, snd)
    out, gate = [], 0
    tail = [None] * 9000                                # 6 s after the last frame: gates off, the release rings
    for b, f in enumerate(osf + tail):
        fb = bytearray(song.base)
        if f is not None:
            for o, n in ((0x02, 32), (0x22, 8), (0x34, 32), (0xA5A, 32)):
                fb[o:o + n] = f[o:o + n]
            on, off = int.from_bytes(f[0x22:0x24], 'big'), int.from_bytes(f[0x24:0x26], 'big')
            gate = (gate | on) & ~off
            last = f
        else:
            for o, n in ((0x02, 32), (0x34, 32), (0xA5A, 32)):
                fb[o:o + n] = last[o:o + n]
            if gate:
                fb[0x24:0x26] = fb[0x28:0x2a] = gate.to_bytes(2, 'big')
                gate = 0
        if lfo:
            row, centre, depth, bars = lfo
            ph = (b / (bars * BAR)) % 1.0
            tri = 1 - 4 * abs(ph - 0.5)                 # starts at the bottom, top after half a period
            val = int(max(0, min(0x7f00, centre + depth * tri)))
            o = S.slot_off(snd.names[row.upper()])
            for v in range(6):
                fb[0xda + 146 * v + o:0xda + 146 * v + o + 2] = val.to_bytes(2, 'big')
        out.append(D.swap16(bytes(fb)))
    return out


def render(name):
    sec7, snap = P.snap('stock')
    L, Rr, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), frames(name))
    x = np.stack([np.asarray(L, float), np.asarray(Rr, float)], 1)
    peak = np.abs(x).max()
    rms = np.sqrt(np.mean(x ** 2))
    y = x / peak * 10 ** (-3 / 20) if peak > 0 else x     # normalised to -3 dBFS peak for listening
    os.makedirs(OUT_WAV, exist_ok=True)
    with wave.open(f'{OUT_WAV}/{name}.wav', 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes((y * 32767).astype('<i2').tobytes())
    print(f'{name}: {len(x) / 48000:.1f} s, peak {20 * np.log10(peak + 1e-12):.1f} dBFS, rms {20 * np.log10(rms + 1e-12):.1f} dBFS before normalising', flush=True)
    return x


def sheet(name):
    title, text, knobs, couple, lfo, dg, cap = SOUNDS[name]
    snd = sound(name)
    rows = {}
    for r in S.PARAM_ROWS:
        if (r['grp'] == 0 or r['grp'] in S.SOUND_GROUPS) and S.slot_off(r['id']) is not None:
            v = snd.slots[r['id']]
            if v != r['dflt']:
                rows[f"{r['page']} {r['short']} ({r['name']}, slot {r['id']})"] = dict(
                    knob=v >> 8, fine=v & 0xFF, stored=f'{v:#06x}', default=f"{r['dflt']:#06x}")
    os.makedirs(SND, exist_ok=True)
    json.dump(dict(name=title, machine='FM TONE', character=text, changed_from_init=rows, couple=couple,
                   lfo=None if not lfo else dict(destination=lfo[0], centre=f'{lfo[1]:#06x}', depth=f'{lfo[2]:#06x}',
                                                 period_bars=lfo[3]),
                   digiglide=dg), open(f'{SND}/{name}.json', 'w'), indent=1)
