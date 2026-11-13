"""Does the DSP sound a voice that gets a second note-on without a note-off in between (DigiGlide's "strike the held
chord again", build 7)? Frames built with dn2synth, rendered by the SHARC emulator; RMS of 100 ms windows.
  A  note-on at block 100, nothing else                          (reference: a held note)
  B  note-on at 100, a second note-on on the same voice at 1600   (the re-strike, as build 7 sends it)
  C  note-on at 100, note-off at 1599, note-on at 1600            (off and on in consecutive blocks)
  D  note-on at 100, note-off and note-on in the same block 1600  (both bits in one frame)
    ~/dn2-workspace/repos/digikit/.venv/bin/python restrike_audio.py"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import numpy as np
import dn2paths as P, dn2frame as D, dn2synth as S

sec7, snap = P.snap('stock')
N = 4000


def frames(case):
    snd = S.Sound('WAVETONE')
    for n, v in (('AMP.ATK', 20), ('AMP.HOLD', 127), ('AMP.SUS', 127), ('AMP.REL', 40), ('FX.REV', 0), ('FX.DEL', 0), ('FX.CHR', 0)):
        snd.set(n, v)
    song = S.Song(bpm=120)
    song.assign(0, snd).track(0, 0).note(100, 0, 60, 100, length=None)
    out = []
    for i, f in enumerate(song.frames(N)):
        b = bytearray(D.swap16(f))
        on, off = int.from_bytes(b[0x22:0x24], 'big'), int.from_bytes(b[0x24:0x26], 'big')
        if i == 1600 and case in 'BCD':
            on |= 1
        if (i == 1599 and case == 'C') or (i == 1600 and case == 'D'):
            off |= 1
        for o, v in ((0x22, on), (0x26, on), (0x24, off), (0x28, off)):
            b[o:o + 2] = v.to_bytes(2, 'big')
        out.append(D.swap16(bytes(b)))
    return out


for case in 'ABCD':
    L, R, _ = D.render(D.Frame(D.image_from_sec7(sec7), snap), frames(case))
    x = (np.asarray(L, float) + np.asarray(R, float)) / 2
    w = 4800
    rms = [float(np.sqrt(np.mean(x[i:i + w] ** 2))) for i in range(0, len(x) - w, w)]
    print(case, ' '.join(f'{r:.3f}' for r in rms))
