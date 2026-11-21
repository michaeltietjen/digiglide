"""DRONE PULSE (spec, "Drone presets"): the DRONE preset plus LFO1 on the amp volume, synced, one cycle an eighth note
(SPD 32 x MULT 32 = 1024). Checked in the emulator: the OS's own LFO evaluator, DigiGlide's frames, the SHARC render.

LFO1 is set through the stock path (sound slot, then the live record 0x4003f1ae, as the value setter does): slots 1..8
are SPD MULT FADE DEST WAVE SPH MODE DEP (entries 75..83; MULT shows 1..2k at indexes 0..11 and again at 12..23).
DEST is a sound slot: 90 = AMP VOL. DEP 0x4000 = 0, (v - 0x4000) / 128 on the screen.

Measured: the level word (+0x74) of DigiGlide's voices, frame by frame (1 frame = 1 block = 2/3 ms), its period and
depth, and the rendered audio's RMS in 10 ms windows.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python b25_drone_pulse.py IMAGE.syx"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/mod/tests'))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
from dgkit import Session, Ui, U16
from osver import A
import dn2paths as P, dn2frame as D

img = sys.argv[1]
sec7, snap = P.snap('stock')
DRONE = Ui(vcnt=5, type=4, ext=0, hold=1, glid=6, time=5, bass=2, voic=64, drft=8, vib=0)
LFO = dict(spd=(1, 75), mult=(2, 76), fade=(3, 77), dest=(4, 78), wave=(5, 79), sph=(6, 80), mode=(7, 82), dep=(8, 83))


def set_lfo(s, t, **kw):
    k = s.k
    root = k.call(A(0x4018A97A))
    for name, v in kw.items():
        sl, e = LFO[name]
        k.sound_slot(t, sl, v)
        k.call(A(0x4003F1AE), [root, t, e, v])


def period(x):
    """dominant period in frames, from the autocorrelation of the mean-removed signal (first peak after a dip)"""
    x = np.asarray(x, float) - np.mean(x)
    if not np.any(x):
        return 0
    ac = np.correlate(x, x, 'full')[len(x) - 1:]
    neg = np.argmax(ac < 0)
    if not neg:
        return 0
    return int(neg + np.argmax(ac[neg:len(x) // 2]))


def audio_env(fr):
    out = [D.swap16(bytes(f)) for f in fr]
    L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), out)
    x = (np.asarray(L, float) + np.asarray(R, float)) / 2
    n = len(x) // len(fr)                                 # samples a frame
    w = max(1, n * 15)                                    # 10 ms
    env = np.sqrt(np.convolve(x ** 2, np.ones(w) / w, 'valid'))[::n]
    return env


def run(tag, bpm, lfo, vcnt=5):
    s = Session(img, tag=tag, solo=True)
    s.set_sound(DRONE.copy(vcnt=vcnt) if vcnt else DRONE.copy(vcnt=0), t=0, mach=None, atk=None)
    if lfo:
        set_lfo(s, 0, **lfo)
    s.trig(0, note=48, length=127, t=0)
    fr = s.play(4500, bpm=bpm)
    on = next((i for i, f in enumerate(fr) if U16(f, 0x22)), 0)
    voices = [v for v in range(16) if any(U16(f, 0x22) >> v & 1 for f in fr[on:on + 40])]
    v0 = voices[0] if voices else 0
    lv = [U16(f, 0x74 + 2 * v0) for f in fr[on + 1500:]]
    env = audio_env(fr)[on + 1500:]
    db = 20 * np.log10(np.maximum(env, 1e-9))
    p_lv, p_au = period(lv), period(db)
    print(f'{tag:14s} {bpm:3d} BPM  voices {voices}  level word {min(lv):#06x}..{max(lv):#06x}  period {p_lv} blocks '
          f'({p_lv * 2 / 3:.0f} ms)  audio {np.percentile(db, 5):6.1f}..{np.percentile(db, 95):6.1f} dB, '
          f'period {p_au} blocks ({p_au * 2 / 3:.0f} ms)', flush=True)
    return p_lv


base = dict(spd=0x6000, fade=0x4000, dest=90 << 8, wave=1 << 8, sph=0, mode=1 << 8)
print('eighth note: 120 BPM 250 ms (375 blocks), 100 BPM 300 ms (450 blocks)')
run('drone, no LFO', 120, None)
for idx in (5, 17):
    for bpm in (120, 100):
        run(f'MULT idx {idx}', bpm, dict(base, mult=idx << 8, dep=0x0000))
run('DEP -64', 120, dict(base, mult=5 << 8, dep=0x2000))
run('DEP +126', 120, dict(base, mult=5 << 8, dep=0x7F00))
run('stock, VCNT 0', 120, dict(base, mult=5 << 8, dep=0x0000), vcnt=0)
