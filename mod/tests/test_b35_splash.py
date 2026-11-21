"""Image 35: the boot splash. A cold boot in the emulator, every frame the display flushes send written down.
  A  stock's intro plays first, untouched: its frames are the ones a build without the splash sends.
  B  then the splash: its frames in order, each the picture splash_gen.py made (read back with digikit's own panel
     decoder, so the orientation is the display's), for the ticks they were given.
  C  then the start goes on as stock's: the intro's end is reached once, the main screen comes up, and the splash's
     counters do not move again.
    DG_OS=1.12 ~/dn2-workspace/repos/digikit/.venv/bin/python test_b35_splash.py [DIGIGLIDE.syx] [NO_SPLASH.syx]
The second image (built with -D DG_SPLASH=0) is the reference for A; without it A only counts the frames."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgkit import latest, symbols
from osver import A
import osver, fastemu, emucheck, splash_gen
from emu import panel
from emu.longrun import spin

img = sys.argv[1] if len(sys.argv) > 1 else latest()
ref = sys.argv[2] if len(sys.argv) > 2 else None
print('image', os.path.basename(img))
ok = True


def check(c, msg):
    global ok
    ok &= bool(c)
    print(('  ok   ' if c else '  FAIL ') + msg, flush=True)


splash_frames = set()


def boot(image):
    """-> (flushes [(kind, phase, ticks, frame bytes)], reached the main screen, intro ends, symbols, machine)"""
    d = image[:-4]
    sym = symbols(image)
    snap = os.path.join(d, 'emu_splash', 'boot400M.snap')
    os.makedirs(os.path.dirname(snap), exist_ok=True)
    if not os.path.exists(snap) or os.path.getmtime(snap) < os.path.getmtime(image):
        fastemu.cold_boot(open(os.path.join(d, 'section_3.bin'), 'rb').read(), osver.STOCK_SYX, snap, log=lambda *a: None)
    m, ev, st, pc, inq, at, pits, profile = fastemu.setup(snap, osver.STOCK_SYX)
    uc = m.uc
    u32 = lambda a: struct.unpack('>I', bytes(uc.mem_read(a, 4)))[0]
    val = lambda n: u32(sym[n]) if n in sym else 0
    sent, ends = [], []

    def flush(kind):
        def f(uc_, a, s, d_):
            p = u32(A(0x402A0B88))
            sent.append((kind, val('dg_splash_phase'), val('dg_splash_ticks'), bytes(uc.mem_read(p, 1024)) if p else b''))
        return f
    at(A(0x40131C74), flush('full'))
    at(A(0x40131CF2), flush('diff'))
    if profile.intro_done is not None:
        at(profile.intro_done, lambda uc_, a, s, d_: ends.append(len(sent)))
    done, seen = 0, None
    while done < 900_000_000:
        pc, ran, stop = spin(m, pc, 10_000_000, pits=pits, fast=True)
        done += ran
        buf = panel.read(m, profile.fb_front)
        if (seen is None and buf and (ends or profile.intro_done is None) and bytes(buf) not in splash_frames
                and emucheck.frame_on_fraction(buf) >= emucheck.MAIN_SCREEN_ON_FRACTION):   # (after the intro's end only)
            seen = done
        if seen is not None and done - seen >= 20_000_000:
            break
    return sent, seen, ends, {n: val(n) for n in ('dg_splash_phase', 'dg_splash_ticks', 'dg_splash_shown', 'dg_splash_sum')}, done


build = os.path.basename(img)[:-4].rsplit('_', 1)[-1]
frames, ticks, line = splash_gen.make(build)
print(' ', line)
splash_frames.update(frames)
sent, seen, ends, v, done = boot(img)
end = ends[0] if ends else len(sent)
mine = [s for s in sent[:end] if s[1] == 1]
n_intro = len([s for i, s in enumerate(sent) if s[1] == 0 and ends and i < ends[0]])
check(n_intro >= 100, f'A stock\'s intro plays first: {n_intro} frames sent before the splash')
if ref:
    rs, rseen, rends, rv, rdone = boot(ref)
    r_intro = [s[3] for i, s in enumerate(rs) if rends and i < rends[0]]
    m_intro = [s[3] for i, s in enumerate(sent) if s[1] == 0 and ends and i < ends[0]]
    check(r_intro == m_intro and len(r_intro) >= 100,
          f'A its frames are the ones the image without a splash sends ({len(m_intro)} / {len(r_intro)}, '
          f'{sum(a != b for a, b in zip(m_intro, r_intro))} differ)')
    check(rseen is not None and seen is not None,
          f'C both reach the main screen (with the splash after {done / 1e6:.0f}M instructions, without {rdone / 1e6:.0f}M)')
check([s[3] for s in mine] == frames,
      f'B then the splash: {len(mine)} frame(s) sent, {len(frames)} made, in order and the same bytes')
want_at = [sum(ticks[:i]) + 1 for i in range(len(ticks))]      # (the tick is counted before the frame is sent)
check([s[2] for s in mine] == want_at, f'B each frame at its tick: sent at {[s[2] for s in mine]}, wanted {want_at}')
if mine:
    px = splash_gen.unpack(mine[-1][3])
    lit = panel.lit(mine[-1][3])
    same = all(((x, y) in lit) == bool(px[y][x]) for y in range(64) for x in range(128))
    check(same and 20 < len(lit) < 4000, f'B read back with the emulator\'s panel decoder the picture is the one made ({len(lit)} pixels lit)')
    out = os.path.join(img[:-4], 'splash_last.png')
    panel.write_png(mine[-1][3], out)
    print('  info the last splash frame as the display got it:', out)
check(v['dg_splash_ticks'] == sum(ticks) and v['dg_splash_shown'] == len(frames),
      f'C the splash took {v["dg_splash_ticks"]} ticks ({sum(ticks)} given) for {v["dg_splash_shown"]} frame(s)')
check(len(ends) == 1, f'C the intro\'s end is reached once ({len(ends)}), after flush {ends[:1]} of {len(sent)}')
after = sent[ends[0]:] if ends else []
check(seen is not None and len(after) > 0 and all(s[2] == sum(ticks) for s in after),
      f'C the main screen comes up ({"yes" if seen else "no"}); {len(after)} frames sent after the intro, none of them the splash\'s')
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
