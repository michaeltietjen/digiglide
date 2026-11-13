# M6: first flash (owner approved 2026-11-10)

Image: `~/dn2-workspace/build/DN2_1.12_DIGIGLIDE_1.syx`
sha256 `d113b72c7658c930c10a9e3e995423a31263a30d798c49cf8b0d0517da9e24da` (commit fa022cb), on a unit running OS 1.12.

## Before
- [ ] +Drive backed up (projects and sounds)
- [ ] USB-to-DIN MIDI interface at hand
- [ ] Stock `Digitone_II_OS1.12.syx` at hand (`~/Downloads/Digitone_II_OS1.12_dist.zip`)

## Flash
Elektron Transfer, USB: CONNECTION page (the Digitone II's MIDI in and out), DROP page: drop the .syx, press [YES]
on the unit. The unit restarts by itself. Do not power off during the update.

## On the unit (write what happened next to each)
1. Boots to the main screen; the project you had loads and plays as before.
2. A WAVETONE track: [SYN] cycles 5 pages, the last two are HARMONY and MOTION.
3. HARMONY: VCNT to 5. Trigs on steps 1, 5, 9, 13 with DEG p-locked I, VI, IV, V (hold the trig, turn knob C).
   Play: chords glide between trigs.
4. Glides smooth: no clicks, no zipper noise (try GLID 1 bar, then 1/4, then 1/16 with PATH Snap and Bounce).
5. SCRB (MOTION page, last knob) playable by hand while a glide runs.
6. The other tracks sound as before while the DigiGlide track plays.
7. STOP: nothing keeps sounding (no stuck notes).
8. [FUNC] + push encoder E: "DIGIGLIDE OFF", the track plays plain notes; again: "DIGIGLIDE ON (5 VOICES)".
9. Save the project, power off and on, reload: the DigiGlide settings come back.

## If something goes wrong
- The unit boots but misbehaves: flash the stock 1.12 file the same way (Transfer, USB).
- The unit does not boot: hold [FUNC] at power-on, press [TRIG 4] (OS UPGRADE), Transfer's LEGACY OS UPGRADE page,
  your DIN MIDI interface, the stock 1.12 file. About 12 to 15 minutes.

## Verdict
(fill in)

## Second image (rev 4), not flashed until the owner says

Image: `~/dn2-workspace/build/DN2_1.12_DIGIGLIDE_2.syx`
sha256 `defe7d6f9a96af8c59652e17eff1a941d84e2d2d2db912902a6eed9fa8ad8471`

Before testing: track transpose back to 0 on the test track.

1. WAVETONE track, [SYN] to HARMONY (4th page), VCNT to 5: the screen shows "VOICES SET TO 5".
2. Chord mode off: play up the scale from the KEY note. Each key is a different chord (I to VII), the next octave is
   the first chord higher. No plain note underneath, ever.
3. Chord mode on: a key plays that chord's notes, glided into by the DigiGlide voices; again no stock chord underneath.
4. Same key with VCNT OFF and then ON: the bass of the DigiGlide chord is the same note name as the stock note.
5. [FUNC] + push encoder H: "LATCH ON". Press and release a key: the chord holds. Another key: it glides there.
   The same key again: it fades. [STOP]: a held chord fades.
6. Sequenced trigs with different notes: every change glides, trigs end with their length.
7. The other tracks still play normally (they share the 11 voices left).
