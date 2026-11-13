"""A simple saw pad to hear the DigiGlide model (M1). Not the Digitone's sound: just enough to judge the voicing
and the glides. Per voice: two band-limited saws 7 cents apart, pitch ramped across each block as Brickglide's
engine does, a slow amp envelope (attack 0.8 s, release 2.5 s) on the voice's gate, Brickglide's pan law.
Mix: a gentle static low-pass and a synthetic hall (FFT convolution), numpy only.
"""
import math
import numpy as np

SR = 48000
BLOCK = 32
ATTACK, RELEASE = 0.8, 2.5
DETUNE = 7.0                            # cents between the two saws
CUTOFF = 2400.0
WET = 0.28


def _saw(phase_inc, phase0=0.0):
    """Band-limited saw (polyBLEP) from a per-sample phase increment (cycles/sample)."""
    ph = (phase0 + np.cumsum(phase_inc)) % 1.0
    y = 2.0 * ph - 1.0
    dt = phase_inc
    lo = ph < dt
    t = ph[lo] / dt[lo]
    y[lo] -= t + t - t * t - 1.0
    hi = ph > 1.0 - dt
    t = (ph[hi] - 1.0) / dt[hi]
    y[hi] -= t * t + t + t + 1.0
    return y


def _envelope(gate_blocks):
    """Per-block linear-in-dB-ish envelope: exponential attack to 1, exponential release to 0."""
    a = 1.0 - math.exp(-1.0 / (ATTACK / 4.0 * SR / BLOCK))
    r = 1.0 - math.exp(-1.0 / (RELEASE / 5.0 * SR / BLOCK))
    env = np.zeros(len(gate_blocks) + 1)
    e = 0.0
    for k, g in enumerate(gate_blocks):
        e += ((1.0 - e) * a) if g else (-e * r)
        env[k + 1] = e
    return env


def _per_sample(block_vals):
    """Ramp a per-block value across each block (value at block end), as the engine's r0 -> r1 ramp."""
    v = np.asarray(block_vals, float)
    v0 = np.concatenate([[v[0]], v[:-1]])
    t = (np.arange(BLOCK) + 1) / BLOCK
    return (v0[:, None] + (v - v0)[:, None] * t[None, :]).reshape(-1)


def _lowpass(x, fc):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1.0 / (1.0 + (f / fc) ** 4)           # 2nd-order-ish magnitude, zero phase
    return np.fft.irfft(X, len(x))


def _hall(n_seconds=3.2, seed=7):
    rng = np.random.default_rng(seed)
    n = int(n_seconds * SR)
    t = np.arange(n) / SR
    ir = []
    for ch in range(2):
        noise = rng.standard_normal(n) * np.exp(-t / 0.7)
        noise[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
        ir.append(_lowpass(noise, 3500.0))
    ir = np.array(ir)
    return ir / np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True))


_IR = None


def _convolve(x, ir):
    n = len(x) + len(ir) - 1
    size = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)]


def render(pitch, gate, pan, level):
    """pitch[b][v] in cents (nan = never started), gate/pan/level per block and voice -> (L, R) float arrays."""
    global _IR
    pitch = np.asarray(pitch, float)
    gate = np.asarray(gate, bool)
    pan = np.asarray(pan, float)
    level = np.asarray(level, float)
    nb, nv = pitch.shape
    L = np.zeros(nb * BLOCK)
    R = np.zeros(nb * BLOCK)
    for v in range(nv):
        if np.all(np.isnan(pitch[:, v])):
            continue
        p = pitch[:, v].copy()
        first = int(np.argmax(~np.isnan(p)))
        p[:first] = p[first]
        cents = _per_sample(p)
        f = 440.0 * 2.0 ** ((cents / 100.0 - 69.0) / 12.0)
        inc1 = f * 2 ** (-DETUNE / 2400.0) / SR
        inc2 = f * 2 ** (DETUNE / 2400.0) / SR
        osc = 0.5 * (_saw(inc1, 0.13 * v) + _saw(inc2, 0.61 * v))
        env = _per_sample(_envelope(gate[:, v])[1:])
        g = env * _per_sample(level[:, v])
        pn = _per_sample(pan[:, v])
        lg, rg = np.minimum(1.0, 1.0 - pn), np.minimum(1.0, 1.0 + pn)
        L += osc * g * lg
        R += osc * g * rg
    L, R = _lowpass(L, CUTOFF), _lowpass(R, CUTOFF)
    if _IR is None:
        _IR = _hall()
    wl, wr = _convolve(L, _IR[0]), _convolve(R, _IR[1])
    return (1 - WET) * L + WET * wl * 3.0, (1 - WET) * R + WET * wr * 3.0


def write_wav(path, L, R, gain):
    import wave
    x = np.stack([L, R], 1) * gain
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32767.0).astype('<i2').tobytes()
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)
