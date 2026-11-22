#!/usr/bin/env python3
"""The YouTube thumbnail for the DigiGlide showcase, 1280 x 720. Needs Pillow.
Run: python3 assets/make_youtube_thumbnail.py

Drawn on a 320 x 180 grid of 4-pixel squares in the logo's lettering: four voices gliding from one chord to the
next (the moving part in amber), the hook line, and the name.
"""
import os

from PIL import Image

import make_assets as m

HERE = os.path.dirname(os.path.abspath(__file__))
BONE, COAL, AMBER, SEAM = (0xf2, 0xf0, 0xea), (0x11, 0x12, 0x14), (0xff, 0x8a, 0x1f), (0x2a, 0x2c, 0x31)
GW, GH, CELL = 320, 180, 4
m.FONT.update({                                            # letters the boot screen never needed
    "C": "01111 10000 10000 10000 10000 10000 01111",
    "F": "11111 10000 10000 11110 10000 10000 10000",
    "H": "10001 10001 10001 11111 10001 10001 10001",
    "M": "10001 11011 10101 10101 10001 10001 10001",
    "N": "10001 11001 10101 10101 10011 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110",
    "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110",
    "W": "10001 10001 10001 10101 10101 11011 10001",
})
grid = [[COAL] * GW for _ in range(GH)]


def box(x0, y0, x1, y1, colour):
    for y in range(max(0, y0), min(GH, y1)):
        for x in range(max(0, x0), min(GW, x1)):
            grid[y][x] = colour


def text(word, x0, y0, scale, colour):
    x = x0
    for ch in word:
        for r, row in enumerate(m.FONT[ch].split()):
            for c, bit in enumerate(row):
                if bit == "1":
                    box(x + c * scale, y0 + r * scale, x + (c + 1) * scale, y0 + (r + 1) * scale, colour)
        x += 6 * scale


def width(word, scale):
    return len(word) * 6 * scale - scale


# faint staff lines behind the voices, like a screen's grid
for y in range(24, 100, 8):
    box(10, y, 310, y + 1, SEAM)
# the tag, top left: dark lettering on an amber plate
tag = "DIGITONE II FIRMWARE MOD"
box(10, 8, 10 + width(tag, 1) + 8, 21, AMBER)
text(tag, 14, 11, 1, COAL)
# four voices: steady, gliding (amber), steady again
X0, X1, G0, G1, THICK = 10, 310, 118, 202, 5
for a, b in zip([34, 50, 66, 82], [28, 46, 70, 88]):
    for x in range(X0, X1):
        t = min(1.0, max(0.0, (x - G0) / float(G1 - G0)))
        y = int(round(a + (b - a) * (t * t * (3 - 2 * t))))
        box(x, y, x + 1, y + THICK, AMBER if G0 <= x < G1 else BONE)
# the hook, then the name
hook, name = "CHORDS THAT GLIDE", "DIGIGLIDE"
text(hook, (GW - width(hook, 3)) // 2, 106, 3, AMBER)
text(name, (GW - width(name, 5)) // 2, 136, 5, BONE)

im = Image.new("RGB", (GW, GH))
im.putdata([c for row in grid for c in row])
out = os.path.join(HERE, "thumbnail", "digiglide-youtube-thumbnail-1280x720.png")
im.resize((GW * CELL, GH * CELL), Image.NEAREST).save(out)
print(out, os.path.getsize(out), "bytes")
