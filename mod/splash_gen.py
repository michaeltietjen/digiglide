"""The boot splash's frames -> dg_splash_gen.h (build_dg.py calls write(); dg_splash.c shows them).

Frames: mod/splash/*.png (or .bmp, .pbm, .gif), 128 x 64, taken in name order. A pixel is lit when it is lighter than
mid grey, so white on black is the picture as the OLED shows it. With no frame files a plain "DIGIGLIDE" is made here.

Timing: mod/splash/timing.txt, one whole number a frame: how many ticks the frame stays (a tick is 1/30 s, the stock
intro's own clock). Without the file every frame stays 2 ticks and the last one fills the splash up to 45 ticks.

Build number: "BUILD n" (DG_BUILD) is stamped on every frame, bottom right, in a 5 x 7 font, over a cleared box of
49 x 9 pixels. mod/splash/stamp.txt changes that: "off", or "x y" for the box's top left corner, and "last" as a
third word stamps the last frame only; "centre y", "text WORD" and "from n" as stamp() says.

Limits (the build stops when one is passed): 48 frames, 90 ticks (3 s).

The panel's buffer is 1,024 bytes, a column of 64 pixels in 8 bytes: pixel (x, y), y down from the top, is bit
y % 8 of byte 8 x + 7 - y // 8 (dnfw docs/display-path.md; read back in the emulator by tests/test_b35_splash.py)."""
import glob, os

W, H = 128, 64
MAX_FRAMES, MAX_TICKS, DEFAULT_TICKS = 48, 90, 45
HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.environ.get('DG_SPLASH_DIR') or os.path.join(HERE, 'splash')     # (tests point it at their own frames)
FONT = {                                    # 5 x 7, the lettering of assets/make_assets.py
    'D': '11110 10001 10001 10001 10001 10001 11110', 'I': '11111 00100 00100 00100 00100 00100 11111',
    'G': '01111 10000 10000 10111 10001 10001 01111', 'L': '10000 10000 10000 10000 10000 10000 11111',
    'E': '11111 10000 10000 11110 10000 10000 11111', 'B': '11110 10001 10001 11110 10001 10001 11110',
    'T': '11111 00100 00100 00100 00100 00100 00100', 'A': '01110 10001 10001 11111 10001 10001 10001',
    'U': '10001 10001 10001 10001 10001 10001 01110', ' ': '00000 00000 00000 00000 00000 00000 00000',
    '0': '01110 10001 10011 10101 11001 10001 01110', '1': '00100 01100 00100 00100 00100 00100 01110',
    '2': '01110 10001 00001 00010 00100 01000 11111', '3': '11110 00001 00001 01110 00001 00001 11110',
    '4': '00010 00110 01010 10010 11111 00010 00010', '5': '11111 10000 11110 00001 00001 10001 01110',
    '6': '00110 01000 10000 11110 10001 10001 01110', '7': '11111 00001 00010 00100 01000 01000 01000',
    '8': '01110 10001 10001 01110 10001 10001 01110', '9': '01110 10001 10001 01111 00001 00010 01100',
}
FONT = {k: tuple(v.split()) for k, v in FONT.items()}


def text(px, s, x, y, scale=1):
    """draw s with its top left corner at (x, y); unknown characters are blanks."""
    for i, ch in enumerate(s.upper()):
        g = FONT.get(ch, FONT[' '])
        for r, row in enumerate(g):
            for c, bit in enumerate(row):
                if bit == '1':
                    for dy in range(scale):
                        for dx in range(scale):
                            xx, yy = x + (6 * i + c) * scale + dx, y + r * scale + dy
                            if 0 <= xx < W and 0 <= yy < H:
                                px[yy][xx] = 1


def blank():
    return [[0] * W for _ in range(H)]


def placeholder():
    px = blank()
    text(px, 'DIGIGLIDE', (W - (6 * 9 - 1) * 2) // 2, 18, scale=2)
    for x in range(12, W - 12):                         # a glide: a line that eases from one height to another
        t = (x - 12) / (W - 25)
        px[44 - round(6 * (3 * t * t - 2 * t * t * t))][x] = 1
    return [px]


def load():
    """-> (frames as rows of 0 / 1, their file names)"""
    names = sorted(f for f in glob.glob(os.path.join(DIR, '*')) if f.lower().endswith(('.png', '.bmp', '.pbm', '.gif')))
    if not names:
        return placeholder(), ['(built in)']
    from PIL import Image
    out = []
    for f in names:
        im = Image.open(f)
        if im.size != (W, H):
            raise SystemExit(f'splash: {os.path.basename(f)} is {im.size[0]} x {im.size[1]}, not {W} x {H}')
        g = im.convert('L')
        out.append([[1 if g.getpixel((x, y)) > 127 else 0 for x in range(W)] for y in range(H)])
    return out, [os.path.basename(f) for f in names]


def ticks_for(n):
    p = os.path.join(DIR, 'timing.txt')
    if os.path.exists(p):
        t = [int(w) for w in open(p).read().split()]
        if len(t) != n or min(t) < 1:
            raise SystemExit(f'splash: timing.txt has {len(t)} numbers for {n} frames (one a frame, 1 or more)')
        return t
    t = [2] * n
    t[-1] = max(2, DEFAULT_TICKS - 2 * (n - 1))
    return t


def stamp(frames, build):
    """stamp.txt: "off", or any of: "x y" (the cleared box's top left corner), "centre y" (centred, box top at y),
    "text WORD" (the word before the number, BUILD without it), "from n" (frames n and later only), "last"."""
    p = os.path.join(DIR, 'stamp.txt')
    words = open(p).read().split() if os.path.exists(p) else []
    if words[:1] == ['off'] or build is None:
        return 'off'
    after = lambda w, d: words[words.index(w) + 1] if w in words[:-1] else d
    s = f'{after("text", "BUILD")} {build}'
    bw, bh = 6 * len(s) - 1 + 2, 9
    x, y = W - bw - 1, H - bh - 1
    if 'centre' in words:
        x, y = (W - bw) // 2, int(after('centre', y))
    elif len(words) >= 2 and words[0].lstrip('-').isdigit():
        x, y = int(words[0]), int(words[1])
    first = len(frames) - 1 if 'last' in words else int(after('from', 0))
    for px in frames[first:]:
        for yy in range(max(0, y), min(H, y + bh)):
            for xx in range(max(0, x), min(W, x + bw)):
                px[yy][xx] = 0
        text(px, s, x + 1, y + 1)
    return f'"{s}" at {x}, {y} from frame {first}'


def pack(px):
    b = bytearray(1024)
    for y in range(H):
        for x in range(W):
            if px[y][x]:
                b[8 * x + 7 - y // 8] |= 1 << (y % 8)
    return bytes(b)


def unpack(b):
    return [[(b[8 * x + 7 - y // 8] >> (y % 8)) & 1 for x in range(W)] for y in range(H)]


def make(build):
    """-> (packed frames, ticks, a line for the build's output)"""
    frames, names = load()
    if len(frames) > MAX_FRAMES:
        raise SystemExit(f'splash: {len(frames)} frames, at most {MAX_FRAMES}')
    t = ticks_for(len(frames))
    if sum(t) > MAX_TICKS:
        raise SystemExit(f'splash: {sum(t)} ticks ({sum(t) / 30:.1f} s), at most {MAX_TICKS} (3 s)')
    where = stamp(frames, build)
    return [pack(f) for f in frames], t, (f'splash: {len(frames)} frame(s) {names[0]}{" .." if len(names) > 1 else ""}, '
                                          f'{sum(t)} ticks ({sum(t) / 30:.2f} s), {1024 * len(frames)} bytes, build stamp {where}')


def write(path, build):
    frames, t, line = make(build)
    L = ['/* generated by splash_gen.py from mod/splash/: the boot splash\'s frames in the panel\'s layout */',
         f'#define SPLASH_N {len(frames)}',
         'static const uint8_t SPLASH_TICKS[SPLASH_N] = {' + ', '.join(map(str, t)) + '};',
         'static const uint8_t SPLASH_FR[SPLASH_N][1024] = {']
    L += ['    {' + ','.join(map(str, f)) + '},' for f in frames]
    L.append('};')
    open(path, 'w').write('\n'.join(L) + '\n')
    return line


if __name__ == '__main__':                              # a look at the frames: splash_gen.py OUT_DIR [BUILD]
    import sys
    from PIL import Image
    frames, t, line = make(sys.argv[2] if len(sys.argv) > 2 else '35')
    print(line)
    os.makedirs(sys.argv[1], exist_ok=True)
    for i, f in enumerate(frames):
        im = Image.new('L', (W, H))
        im.putdata([255 * v for row in unpack(f) for v in row])
        im.resize((W * 4, H * 4), Image.NEAREST).save(os.path.join(sys.argv[1], f'splash_{i:02d}.png'))
