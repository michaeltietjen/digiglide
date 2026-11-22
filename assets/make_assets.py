"""DigiGlide brand assets: the logo as SVG and the boot screen as 128 x 64 one-bit frames.

Run from the repository root:  python3 assets/make_assets.py
Needs only Python. The PNG exports of the logo and the boot preview GIF are made from
these files afterwards (see assets/README.md).

The logo is DigiGlide's own. It uses no Elektron logo, name or typeface.
"""
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
BONE, COAL = "#f2f0ea", "#111214"

FONT = {
    "D": "11110 10001 10001 10001 10001 10001 11110", "I": "11111 00100 00100 00100 00100 00100 11111",
    "G": "01111 10000 10000 10111 10001 10001 01111", "L": "10000 10000 10000 10000 10000 10000 11111",
    "E": "11111 10000 10000 11110 10000 10000 11111", "B": "11110 10001 10001 11110 10001 10001 11110",
    "T": "11111 00100 00100 00100 00100 00100 00100", "A": "01110 10001 10001 11111 10001 10001 10001",
    "U": "10001 10001 10001 10001 10001 10001 01110", " ": "00000 00000 00000 00000 00000 00000 00000",
    "0": "01110 10001 10011 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111", "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
}

# The mark: two voices stepping from one chord to the next, over a ground line. 16 x 16.
ICON = ["................", "................", "........########", ".......#........", "......#.........", "#####.#.........",
        ".....#..........", "................", ".........#######", "........#.......", "#######.#.......", ".......#........",
        "................", "################", "................", "................"]


# ---------------------------------------------------------------- SVG
def svg_pixels(word, x0, y0, p, col):
    out, x = [], x0
    for ch in word:
        for r, row in enumerate(FONT[ch].split()):
            for c, bit in enumerate(row):
                if bit == "1":
                    out.append('<rect x="%d" y="%d" width="%d" height="%d"/>' % (x + c * p, y0 + r * p, p, p))
        x += 6 * p
    return '<g fill="%s">%s</g>' % (col, "".join(out)), x - p


def svg_icon(x0, y0, p, col):
    out = []
    for r, row in enumerate(ICON):
        for c, ch in enumerate(row):
            if ch == "#":
                out.append('<rect x="%d" y="%d" width="%d" height="%d"/>' % (x0 + c * p, y0 + r * p, p, p))
    return '<g fill="%s">%s</g>' % (col, "".join(out))


def lockup(plate, ink):
    """The icon and the name on a plate, as the screen shows a selected line."""
    p = 5
    text, x2 = svg_pixels("DIGIGLIDE", 78, 12, p, ink)
    w = x2 + 16
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d 60" role="img" aria-label="DigiGlide" '
            'shape-rendering="crispEdges"><title>DigiGlide</title><rect width="%d" height="60" rx="6" fill="%s"/>%s%s</svg>\n'
            % (w, w, plate, svg_icon(12, 6, 3, ink), text))


def wordmark(ink):
    """The name alone, no plate."""
    text, x2 = svg_pixels("DIGIGLIDE", 0, 0, 5, ink)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d 35" role="img" aria-label="DigiGlide" '
            'shape-rendering="crispEdges"><title>DigiGlide</title>%s</svg>\n' % (x2, text))


def icon(plate, ink):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="DigiGlide" '
            'shape-rendering="crispEdges"><title>DigiGlide</title><rect width="64" height="64" rx="8" fill="%s"/>%s</svg>\n'
            % (plate, svg_icon(8, 8, 3, ink)))


# ---------------------------------------------------------------- boot screen
W, H = 128, 64
N_FRAMES = 24


def blank():
    return [[0] * W for _ in range(H)]


def text(img, word, x0, y0, scale=1, upto=None):
    x = x0
    for ch in word:
        for r, row in enumerate(FONT[ch].split()):
            for c, bit in enumerate(row):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            px, py = x + c * scale + dx, y0 + r * scale + dy
                            if 0 <= px < W and 0 <= py < H and (upto is None or px < upto):
                                img[py][px] = 1
        x += 6 * scale
    return x - scale


def voices(img, upto):
    """Four voices crossing the screen, gliding from one chord to the next in the middle."""
    starts, ends = [9, 14, 19, 24], [6, 12, 20, 26]
    for a, b in zip(starts, ends):
        for x in range(8, min(120, upto)):
            t = min(1.0, max(0.0, (x - 46) / 36.0))
            y = int(round(a + (b - a) * (t * t * (3 - 2 * t))))
            img[y][x] = img[y + 1][x] = 1


def frame(i, build="28"):
    """Frame i of the splash. The firmware draws the real build number; this one is for the preview."""
    img = blank()
    voices(img, 8 + (i + 1) * 12 if i < 10 else W)
    if i >= 10:
        name_w = 9 * 12 - 2
        x0 = (W - name_w) // 2
        text(img, "DIGIGLIDE", x0, 34, 2, upto=x0 + (i - 9) * 20 if i < 16 else None)
    if i >= 17:
        label = "BETA " + build
        text(img, label, (W - (len(label) * 6 - 1)) // 2, 54, 1)
    return img


BUILD_LABEL = {"text": "BETA ", "x_centre": 64, "y": 54, "scale": 1, "from_frame": 17}


def png(path, img, scale=1):
    """A small PNG writer: one bit per pixel in, 8-bit greyscale out."""
    rows = []
    for row in img:
        line = bytes(b for v in row for b in ([255 if v else 0] * scale))
        rows += [b"\x00" + line] * scale
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W * scale, H * scale, 8, 0, 0, 0, 0))
                + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def packed(img):
    """1024 bytes: 64 rows of 16 bytes, leftmost pixel in the top bit."""
    out = bytearray()
    for row in img:
        for b in range(0, W, 8):
            v = 0
            for k in range(8):
                v = (v << 1) | row[b + k]
            out.append(v)
    return bytes(out)


if __name__ == "__main__":
    logo = os.path.join(HERE, "logo")
    for name, svg in (("digiglide-lockup-on-dark.svg", lockup(BONE, COAL)), ("digiglide-lockup-on-light.svg", lockup(COAL, BONE)),
                      ("digiglide-wordmark-on-dark.svg", wordmark(BONE)), ("digiglide-wordmark-on-light.svg", wordmark(COAL)),
                      ("digiglide-icon-on-dark.svg", icon(BONE, COAL)), ("digiglide-icon-on-light.svg", icon(COAL, BONE))):
        with open(os.path.join(logo, name), "w") as f:
            f.write(svg)
    boot = os.path.join(HERE, "boot")
    blob = bytearray()
    for i in range(N_FRAMES):
        img = frame(i)
        png(os.path.join(boot, "frames", "boot_%02d.png" % i), img)
        png(os.path.join(boot, "frames", "boot_%02d@6x.png" % i), img, 6)
        blob += packed(frame(i, build=""))            # the firmware's copy has no number: it draws its own
    with open(os.path.join(boot, "boot_frames.bin"), "wb") as f:
        f.write(blob)
    print("logo: 6 SVGs; boot: %d frames, %d bytes packed" % (N_FRAMES, len(blob)))
