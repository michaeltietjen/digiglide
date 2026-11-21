"""The DigiDrone sounds in order, with the DigiGlide settings each sets (make_drones.py, test_b31_drones.py)."""
# DigiGlide settings a drone sets when it is loaded: (K_ index, value). K_: TYPE 0 EXT 1 VOIC 3 GLID 5 HOLD 7 DRFT 13
# VIB 14 VCNT 16 (code = voices - 2) TUNE 24 FAN 25. HOLD 3 = on.
def dg(vcnt, glid, drft, vib, typ, ext, voic, tune=0, fan=0):
    # image 34: and the settings that would make a drone strike again or play a figure are put to rest (owner, image
    # 33: "why does the drone keep repeating or restarting after 3 seconds": a load left the track's STRK, BPAT, PLAY
    # and BLOOM as they were): PLAY 6 = CHRD, BPAT 19 = off, BLOOM 21 = 64 (off), STRK 22 = off
    return [(16, vcnt - 2), (5, glid), (7, 3), (13, drft), (14, vib), (0, typ), (1, ext), (3, voic), (24, tune), (25, fan),
            (6, 0), (19, 0), (21, 64), (22, 0)]


# image 33 (the deep set, experiments/b33_patches.py). Every chord but HOLLOW FIFTHS has its third: measured on image
# 32 at four voices (scratch voicings.py, C3), MAJ with EXT 9 or 6+9 plays C1 C2 G2 D3 and plain MAJ at VOIC 90 plays
# C1 C2 G2 C3 (a root, fifths and ninths over the bass: they fuse into one tone); MAJ with EXT MAJ7 or 6 plays
# C1 C2 G2 E3, MIN plays C1 C2 G2 Eb3. Three voices with BASS on are bass, root and fifth: BEAT FIELD has four now.
STILL, CHAIN, RING = dg(4, 6, 30, 2, 0, 3, 90, 0, 24), dg(4, 5, 12, 3, 1, 2, 90), dg(4, 6, 10, 2, 1, 0, 70)
ORDER = [('still', STILL), ('chain', CHAIN), ('ring', RING), ('bells', dg(4, 4, 20, 4, 0, 1, 100)),
         ('beat', dg(4, 7, 6, 0, 1, 0, 70, 0, 30)), ('organ', dg(4, 6, 4, 0, 0, 3, 90, 1, 40)), ('undertow', RING),
         ('wire', CHAIN), ('hollow', dg(4, 7, 6, 0, 4, 0, 127, 0, 24)), ('storm', STILL)]
