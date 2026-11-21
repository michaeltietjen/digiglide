Boot splash frames (see ../splash_gen.py).

Put the frames here as 128 x 64 PNG files (BMP, PBM and GIF also work), white = lit, black = off. They are shown in
name order: frame_00.png, frame_01.png, ...

timing.txt (optional): one whole number a frame, how many ticks it stays; a tick is 1/30 second. Without it every
frame stays 2 ticks and the last fills the splash up to 45 ticks (1.5 s).

stamp.txt (optional): where "BUILD n" goes. "off", or "x y" for the top left corner of its 49 x 9 box; add "last" to
stamp the last frame only. Without it: bottom right, every frame.

Limits: 48 frames, 90 ticks (3 s). With no frames here a plain "DIGIGLIDE" is built in.
Preview what the unit will show: python splash_gen.py OUT_DIR [BUILD]
