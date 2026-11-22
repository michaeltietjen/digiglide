#!/usr/bin/env python3
"""The DigiGlide logo animation as video, for YouTube and Instagram.

The boot screen's frames (make_assets.py) without the build label, in the logo's two colours, scaled by whole
numbers so the pixels stay square. Five seconds each: half a second of dark, the animation at 12 frames a second,
then a hold on the finished logo. Needs Pillow and ffmpeg.  Run: python3 assets/make_video.py
"""
import os
import subprocess
import tempfile

from PIL import Image

import make_assets as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "video")
BONE, COAL = (0xf2, 0xf0, 0xea), (0x11, 0x12, 0x14)
STEPS = [None] * 6 + list(range(17)) + [16] * 37          # in 12ths of a second: 5 s in all
JOBS = [("digiglide-logo-youtube-1920x1080", 1920, 1080, 12, False),
        ("digiglide-logo-instagram-reel-1080x1920", 1080, 1920, 8, False),
        ("digiglide-logo-instagram-post-1080x1350", 1080, 1350, 8, False),
        ("digiglide-logo-overlay-transparent-1920x1080", 1920, 1080, 12, True)]


def picture(step, w, h, scale, alpha):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0) if alpha else COAL + (255,))
    if step is not None:
        img = m.frame(step, build="")
        small = Image.new("RGBA", (m.W, m.H), (0, 0, 0, 0))
        px = small.load()
        for y in range(m.H):
            for x in range(m.W):
                if img[y][x] and y < 50:                  # the build label's rows stay empty
                    px[x, y] = BONE + (255,)
        big = small.resize((m.W * scale, m.H * scale), Image.NEAREST)
        im.alpha_composite(big, ((w - m.W * scale) // 2, (h - m.H * scale) // 2))
    return im if alpha else im.convert("RGB")


for name, w, h, scale, alpha in JOBS:
    with tempfile.TemporaryDirectory() as d:
        made = {}
        for n, step in enumerate(STEPS):
            if step not in made:
                made[step] = picture(step, w, h, scale, alpha)
            made[step].save(os.path.join(d, "s%03d.png" % n))
        src = ["ffmpeg", "-y", "-v", "error", "-framerate", "12", "-i", os.path.join(d, "s%03d.png")]
        if alpha:                                          # QuickTime Animation: lossless, keeps transparency
            out = os.path.join(OUT, name + ".mov")
            cmd = src + ["-r", "30", "-c:v", "qtrle", "-pix_fmt", "argb", out]
        else:                                              # H.264 with a silent stereo track, which uploads cleanly
            out = os.path.join(OUT, name + ".mp4")
            cmd = src + ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest", "-r", "30", "-c:v", "libx264",
                         "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p", "-colorspace", "bt709",
                         "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "aac", "-b:a", "128k",
                         "-movflags", "+faststart", out]
        subprocess.check_call(cmd)
        print(os.path.relpath(out, HERE), os.path.getsize(out), "bytes")
