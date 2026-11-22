# DigiGlide brand assets

DigiGlide's own logo and boot screen. They use no Elektron logo, name or typeface: DigiGlide is unofficial and
should not look like an Elektron product.

## Logo

The idea: how DigiGlide would look as a line on the Digitone's screen. A small one-bit icon (two voices stepping
from one chord to the next, over a ground line) and the name in 5 x 7 pixel lettering, on a plate like a selected
menu line. Two colours only.

| Colour | Value | Use |
| --- | --- | --- |
| Screen white | `#f2f0ea` | Plate on dark grounds, lettering on light plates |
| Panel black | `#111214` | Plate on light grounds, lettering on dark plates |

| File (in `logo/`) | Use |
| --- | --- |
| `digiglide-lockup-on-dark.svg` / `.png` | Icon and name on a white plate, for dark backgrounds |
| `digiglide-lockup-on-light.svg` / `.png` | Icon and name on a black plate, for light backgrounds |
| `digiglide-wordmark-on-dark.svg`, `-on-light.svg` | The name alone, no plate |
| `digiglide-icon-on-dark.svg`, `-on-light.svg`, `-512.png` | The icon alone |
| `favicon-32.png`, `apple-touch-icon.png` | Browser tab and home screen icons |

Keep the pixels square: scale by whole numbers where you can, and never smooth or blur it. Leave clear space of
at least half the plate's height around the lockup.

## Boot screen

`boot/` holds a splash for the Digitone's 128 x 64 one-bit screen, to show after Elektron's own logo screen
(which stays as it is):

1. Frames 0 to 9: four voices draw across the screen, gliding from one chord to the next in the middle.
2. Frames 10 to 15: the name appears from left to right.
3. Frames 16 to 23: hold. From frame 17 the build label sits under the name.

| File | What |
| --- | --- |
| `boot/frames/boot_NN.png` | The 24 frames at real size, 128 x 64 |
| `boot/frames/boot_NN@6x.png` | The same at six times the size, for looking at |
| `boot/preview.gif` | The animation at 12 frames a second |
| `boot/boot_frames.bin` | The frames for the firmware: 24 x 1024 bytes, each frame 64 rows of 16 bytes, leftmost pixel in the top bit, 1 = lit |

The frames in `boot_frames.bin` carry no build number. The firmware draws its own: the text `BETA ` and the
number from `DG_BUILD`, in the 5 x 7 lettering, centred on x = 64 with its top at y = 54, from frame 17 on. The
PNGs and the GIF show `BETA 28` as an example.

## Logo animation for video

`video/` holds the boot animation without the build label, five seconds each: half a second of dark, the
animation, then a hold on the finished logo. All are 30 frames a second.

| File (in `video/`) | Use |
| --- | --- |
| `digiglide-logo-youtube-1920x1080.mp4` | YouTube and other 16:9 video |
| `digiglide-logo-instagram-reel-1080x1920.mp4` | Instagram Reels and Stories, YouTube Shorts (9:16) |
| `digiglide-logo-instagram-post-1080x1350.mp4` | Instagram feed posts (4:5) |
| `digiglide-logo-overlay-transparent-1920x1080.mov` | Transparent background, to lay over footage in an editor |

```bash
python3 assets/make_video.py
```

That rewrites the four files. It needs Pillow and ffmpeg.

## Thumbnails

`thumbnail/` holds the finished logo as stills: `digiglide-logo-transparent-white.png` and `-black.png` to lay over a
photo, and three finished 1280 x 720 thumbnails (logo alone, with "CHORDS THAT GLIDE", with "FOR DIGITONE II").
`python3 assets/make_thumbnail.py` rewrites them; it needs Pillow.

## Regenerating

```bash
python3 assets/make_assets.py
```

That rewrites the SVGs, the frames and `boot_frames.bin`. It needs only Python. The PNG exports of the logo and
`preview.gif` were made from those files with a browser and ffmpeg.
