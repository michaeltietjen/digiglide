#!/usr/bin/env python3
"""DigiGlide logo files for video thumbnails. Needs Pillow.  Run: python3 assets/make_thumbnail.py

The finished boot frame (voices and name, no build label), scaled by whole numbers so the pixels stay square.
"""
import os

from PIL import Image

import make_assets as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "thumbnail")
# letters the boot screen never needed, drawn to match its 5 x 7 lettering
m.FONT.update({
    "C": "01111 10000 10000 10000 10000 10000 01111",
    "F": "11111 10000 10000 11110 10000 10000 10000",
    "H": "10001 10001 10001 11111 10001 10001 10001",
    "N": "10001 11001 10101 10101 10011 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110",
    "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110",
})
BONE, COAL, AMBER = (0xf2, 0xf0, 0xea), (0x11, 0x12, 0x14), (0xff, 0x8a, 0x1f)


def art(grid, colour, scale, rows=None):
    """A one-bit grid as a transparent picture, cropped to what is lit."""
    im = Image.new("RGBA", (m.W, m.H), (0, 0, 0, 0))
    px = im.load()
    for y in range(m.H):
        for x in range(m.W):
            if grid[y][x] and (rows is None or y < rows):
                px[x, y] = colour + (255,)
    im = im.crop(im.getbbox())
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def words(s):
    g = m.blank()
    m.text(g, s, 2, 2, 1)
    return g


def stack(size, parts, gap, ground=None):
    w, h = size
    im = Image.new("RGBA", size, (ground + (255,)) if ground else (0, 0, 0, 0))
    y = (h - sum(p.height for p in parts) - gap * (len(parts) - 1)) // 2
    for p in parts:
        im.alpha_composite(p, ((w - p.width) // 2, y))
        y += p.height + gap
    return im


logo = m.frame(16, build="")
# the logo alone, no background, to lay over a photo or a still
art(logo, BONE, 16, rows=50).save(os.path.join(OUT, "digiglide-logo-transparent-white.png"))
art(logo, COAL, 16, rows=50).save(os.path.join(OUT, "digiglide-logo-transparent-black.png"))
# finished 1280 x 720 thumbnails
stack((1280, 720), [art(logo, BONE, 10, rows=50)], 0, COAL).convert("RGB").save(
    os.path.join(OUT, "digiglide-thumbnail-logo-1280x720.png"))
stack((1280, 720), [art(logo, BONE, 9, rows=50), art(words("CHORDS THAT GLIDE"), AMBER, 6)], 54, COAL).convert("RGB").save(
    os.path.join(OUT, "digiglide-thumbnail-chords-that-glide-1280x720.png"))
stack((1280, 720), [art(logo, BONE, 9, rows=50), art(words("FOR DIGITONE II"), AMBER, 6)], 54, COAL).convert("RGB").save(
    os.path.join(OUT, "digiglide-thumbnail-for-digitone-ii-1280x720.png"))
for f in sorted(os.listdir(OUT)):
    print(f, Image.open(os.path.join(OUT, f)).size)
