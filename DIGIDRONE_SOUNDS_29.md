# DigiDrone: five FM TONE sounds for DigiGlide tracks

Nov 18, 2026 · image 29 · rev 1

Each DigiGlide voice is a four operator FM voice, so each chord note is its own small coupled network of oscillators. DigiGlide stacks them into a chord and glides them. The idea comes from coupled drone instruments (the Lyra-8, and Caravel's DRONE engine for the FM-1, whose docs were read for reference only; no code was taken).

Renders: `~/glide/renders/b29/NAME.wav`. Machine readable sheets with stored words: `~/glide/sounds/b29/NAME.json`. Patches as code: `~/glide/experiments/b29_patches.py`.

## COUPLE

On all five sounds COUPLE is **AB LEVEL** (LVAB, FM TONE SYN page). It scales A LEVEL and B LEVEL together inside the DSP, so one knob moves all the FM in the voice.

| Stored word | Effect (measured in the emulator) |
| --- | --- |
| 0x3000 and below | no FM left, the operators are plain sines |
| 0x4000 (default) | the sound as saved |
| 0x5000 | about three times as bright |
| 0x6000 | harsh |

So the useful ride is from a quarter below the default to a quarter above it.

## How to read the tables

Every value is a row of the stock parameter table, starting from an initialised FM TONE sound. Knob values are the stored word's high byte (0 to 127). Ratio offsets are given in thousandths of the ratio (+1.0 = 0.1 % sharp); they were set as stored words, finer than a knob step, so on the unit dial the nearest value.

Operator routing as measured: algorithm 1: X = C, Y = B1, A into C with feedback on A, B2 into B1 into C. Algorithm 5: X = C, Y = A, full chain B2 into B1 into A into C, feedback on B2. Algorithm 7: X = C + A (A also modulates C), Y = B1 + B2, all four heard. MIX 0 is X only, 64 both, 127 Y only.

## 1. STILL AIR

Four sines a voice near unison, each a hair off the others. Pure and slowly beating.

| Parameter | Value |
| --- | --- |
| ALGO | 7 |
| MIX | 64 |
| Ratios C / A / B1 / B2 | 1 / 1 / 1 / 1 |
| Offsets C / A / B1 / B2 | 0 / +1.2 / -1.0 / +2.3 |
| A LEVEL / B LEVEL | 6 / 6 |
| FDBK | 0 |
| Filter FREQ | 112 |
| Amp ATK / HOLD / DEC / SUS / REL | 85 / 127 / 127 / 127 / 105 |
| Reverb send | 45 |

DigiGlide: VCNT 4, GLID 2 bars, HOLD on, DRFT 30, VIB 2, TYPE MAJ, EXT 9, VOIC 90.

COUPLE: AB LEVEL. A little goes far here: it turns the beating sines into a slowly turning tone. No LFO assigned; ride it by hand.

## 2. SLOW CHAIN

B2 into B1 into A into C at low levels, the modulators a hair off pitch. The FM amount breathes from pure to restless.

| Parameter | Value |
| --- | --- |
| ALGO | 5 |
| MIX | 0 |
| Ratios | 1 / 1 / 1 / 1 |
| Offsets A / B1 / B2 | +0.7 / -0.5 / +1.1 |
| A LEVEL / B LEVEL | 34 / 30 |
| FDBK | 0 |
| Filter FREQ | 112 |
| Amp ATK / HOLD / DEC / SUS / REL | 72 / 127 / 127 / 127 / 102 |
| Reverb send | 45 |

LFO1: DEST AB LEVEL, WAVE triangle, bipolar, one cycle every 8 bars (SPD x MULT = 16; use 8 for 16 bars). Depth: a quarter of the range either side of the centre (stored 0x3000 to 0x5000).

DigiGlide: VCNT 4, GLID 1 bar, HOLD on, DRFT 12, VIB 3, TYPE MIN, EXT 7, VOIC 90.

COUPLE: AB LEVEL. The LFO already rides it; turn the LFO depth down to ride it by hand.

## 3. DARK RING

The same chain with feedback on B2, its last operator, and more FM. The filter sits low and opens slowly.

| Parameter | Value |
| --- | --- |
| ALGO | 5 |
| MIX | 0 |
| Ratios | 1 / 1 / 1 / 1 |
| Offsets A / B1 / B2 | +0.9 / -0.6 / +1.4 |
| A LEVEL / B LEVEL | 44 / 38 |
| FDBK | 34 |
| Filter FREQ / RESO | 48 / 20 |
| Amp ATK / HOLD / DEC / SUS / REL | 78 / 127 / 127 / 127 / 104 |
| Reverb send | 45 |

LFO1: DEST filter FREQ, triangle, one cycle every 16 bars (SPD x MULT = 8), sweeping FREQ from 48 to 84.

DigiGlide: VCNT 4, GLID 2 bars, HOLD on, DRFT 10, VIB 2, TYPE MIN, VOIC 70.

COUPLE: AB LEVEL. FDBK is the second knob to ride: it is the ring.

## 4. IRON BELLS

High FM, the operators at the fifth (A 1.5), the octave (B1 2) and the twelfth (B2 3), each a little off. Bright, with the brightness falling to a held level.

| Parameter | Value |
| --- | --- |
| ALGO | 1 |
| MIX | 36 |
| Ratios C / A / B1 / B2 | 1 / 1.5 / 2 / 3 |
| Offsets A / B1 / B2 | +3.0 / -2.0 / +4.0 |
| A LEVEL / B LEVEL | 74 / 52 |
| FDBK | 14 |
| A env DECAY / END | 92 / 60 |
| B env DECAY / END | 84 / 48 |
| Filter FREQ | 127 |
| Amp ATK / HOLD / DEC / SUS / REL | 4 / 127 / 110 / 96 / 98 |
| Reverb send | 55 |

DigiGlide: VCNT 4, GLID 1/2, HOLD on, DRFT 20, VIB 4, TYPE MAJ, EXT 6+9, VOIC 100.

COUPLE: AB LEVEL. Up: clangorous. Down: a soft organ bell. A good macro target.

## 5. BEAT FIELD

Two pairs a voice: C with A, and B1 with B2 0.4 % above them. No FM from one pair to the other, a little inside each. Each voice beats at its own slow rate, and lower notes beat slower.

| Parameter | Value |
| --- | --- |
| ALGO | 7 |
| MIX | 64 |
| Ratios | 1 / 1 / 1 / 1 |
| Offsets C / A / B1 / B2 | 0 / 0 / +4.0 / +4.0 |
| A LEVEL / B LEVEL | 22 / 22 |
| FDBK | 0 |
| Filter FREQ | 115 |
| Amp ATK / HOLD / DEC / SUS / REL | 76 / 127 / 127 / 127 / 105 |
| Reverb send | 45 |

DigiGlide: VCNT 3, GLID 4 bars, HOLD on, DRFT 0, VIB 0, TYPE 5TH.

COUPLE: AB LEVEL. It adds harmonics inside each pair, and each harmonic beats faster than the one below.

## Extra render: pure.wav

STILL AIR on the same chords with DRFT 4, VIB 0, TUNE PURE and FAN 64 (image 29's two new settings), to compare against still.wav.

## What the renders are and are not

- The note words, glides, DRFT, VIB and gates come from image 29 running in the ColdFire emulator: two chords of four bars each, played twice, then a 6 second release.
- The audio is the stock DSP image in the SHARC emulator. Each file is normalised to -3 dBFS peak; before that they sat within 6 dB of each other.
- The LFOs are not the stock LFO. It runs in the ColdFire and is not emulated, so the render writes the destination's value block by block as a triangle. The LFO depth and the SPD x MULT figures are therefore unverified on the unit.
- None of this has been heard on hardware.

# Second set (image 30)

Same method. The note words reuse the first set's chord captures (named under each sound). Patches: `~/glide/experiments/b30_patches.py`. Algorithm 3 as measured: X = C + B2, Y = B1, A modulates all three, feedback on A.

## 6. GLASS ORGAN

Four partials a voice, 1 2 3 4, each a hair off, almost no FM: a soft additive organ. Made for TUNE PURE, where the partials of the chord notes line up.

| Parameter | Value |
| --- | --- |
| ALGO | 7 |
| MIX | 58 |
| Ratios C / A / B1 / B2 | 1 / 2 / 3 / 4 |
| Offsets A / B1 / B2 | +0.6 / -0.4 / +0.9 |
| A LEVEL / B LEVEL | 8 / 10 |
| FDBK | 0 |
| Filter FREQ | 104 |
| Amp ATK / HOLD / DEC / SUS / REL | 80 / 127 / 127 / 127 / 104 |
| Reverb send | 45 |

DigiGlide: VCNT 4, GLID 2 bars, HOLD on, DRFT 4, VIB 0, TUNE PURE, FAN 64, TYPE MAJ, EXT 9, VOIC 90 (the `pure` capture).

COUPLE: AB LEVEL. Up: the partials start to bend each other and the organ turns reedy.

## 7. UNDERTOW

The chain an octave down: every operator at 0.5, B2 with feedback, the filter low. A heavy floor that turns over slowly.

| Parameter | Value |
| --- | --- |
| ALGO | 5 |
| MIX | 0 |
| Ratios | 0.5 / 0.5 / 0.5 / 0.5 |
| Offsets A / B1 / B2 | +0.8 / -0.7 / +1.5 |
| A LEVEL / B LEVEL | 40 / 34 |
| FDBK | 22 |
| Filter FREQ / RESO | 60 / 10 |
| Amp ATK / HOLD / DEC / SUS / REL | 82 / 127 / 127 / 127 / 108 |
| Reverb send | 45 |

LFO1: DEST AB LEVEL, triangle, one cycle every 16 bars (SPD x MULT = 8), stored 0x3400 to 0x4c00.

DigiGlide: VCNT 4, GLID 2 bars, HOLD on, DRFT 10, VIB 2, TYPE MIN, VOIC 70 (the `ring` capture).

COUPLE: AB LEVEL. Up: the floor growls.

## 8. WIRE CHOIR

One modulator (A, with feedback) drives the three operators that are heard: the nearest thing here to a shared coupling line. The three are a hair apart, so they answer it differently.

| Parameter | Value |
| --- | --- |
| ALGO | 3 |
| MIX | 64 |
| Ratios C / A / B1 / B2 | 1 / 1 / 1 / 2 |
| Offsets A / B1 / B2 | +1.5 / -0.8 / +1.2 |
| A LEVEL / B LEVEL | 36 / 20 |
| FDBK | 18 |
| Filter FREQ | 108 |
| Amp ATK / HOLD / DEC / SUS / REL | 74 / 127 / 127 / 127 / 102 |
| Reverb send | 45 |

LFO1: DEST AB LEVEL, triangle, one cycle every 16 bars (SPD x MULT = 8), stored 0x3000 to 0x5000.

DigiGlide: VCNT 4, GLID 1 bar, HOLD on, DRFT 12, VIB 3, TYPE MIN, EXT 7, VOIC 90 (the `chain` capture).

COUPLE: AB LEVEL. FDBK roughens the one modulator, and so all three at once.

## 9. HOLLOW FIFTHS

Each voice carries its own fifth: C at 1 with A at 1.5, and above them B1 at 2 and B2 at 3. Little FM. On fifth chords the stack is all open intervals.

| Parameter | Value |
| --- | --- |
| ALGO | 7 |
| MIX | 54 |
| Ratios C / A / B1 / B2 | 1 / 1.5 / 2 / 3 |
| Offsets A / B1 / B2 | +0.5 / +1.0 / -0.7 |
| A LEVEL / B LEVEL | 14 / 12 |
| FDBK | 0 |
| Filter FREQ | 106 |
| Amp ATK / HOLD / DEC / SUS / REL | 78 / 127 / 127 / 127 / 105 |
| Reverb send | 45 |

DigiGlide: VCNT 3, GLID 4 bars, HOLD on, DRFT 0, VIB 0, TYPE 5TH (the `beat` capture).

COUPLE: AB LEVEL. Up: A at the fifth puts a tone an octave under each note.

## 10. STORM GLASS

The chain with its operators spread: B2 at 0.5 (with feedback) into B1 at 3 into A at 2 into C. The FM amount swells and falls every 8 bars, from glassy to weather.

| Parameter | Value |
| --- | --- |
| ALGO | 5 |
| MIX | 0 |
| Ratios C / A / B1 / B2 | 1 / 2 / 3 / 0.5 |
| Offsets A / B1 / B2 | +1.0 / -1.5 / +2.0 |
| A LEVEL / B LEVEL | 28 / 24 |
| FDBK | 10 |
| Filter FREQ | 104 |
| Amp ATK / HOLD / DEC / SUS / REL | 76 / 127 / 127 / 127 / 104 |
| Reverb send | 55 |

LFO1: DEST AB LEVEL, triangle, one cycle every 8 bars (SPD x MULT = 16), stored 0x3000 to 0x4c00.

DigiGlide: VCNT 4, GLID 2 bars, HOLD on, DRFT 30, VIB 2, TYPE MAJ, EXT 9, VOIC 90 (the `still` capture).

COUPLE: AB LEVEL. The LFO rides it; at the top of the swell it is meant to be rough. The first version was harsh (levels 36 / 34, FDBK 20) and was turned down to the values above.

# Loading the sounds on the unit (image 31)

From image 31 all ten sounds are inside the firmware. Nothing has to be programmed by hand.

- **[FUNC] + push knob A**: step to the next sound. The screen shows its number and name ("DRONE 3 DARK RING"). After the tenth it starts again at the first. Picking alone changes nothing.
- **[FUNC] + push knob B**: load the sound shown onto the current track. The screen shows "LOADED" and the name.

What a load does:

- It replaces the current track's sound: machine (FM TONE), name and every parameter, as a sound loaded from the +Drive would. The sound that was on the track is gone unless it was saved. The +Drive itself is not touched.
- It sets the DigiGlide settings listed under each sound (VCNT, GLID, HOLD, DRFT, VIB, TYPE, EXT, VOIC, and TUNE / FAN for GLASS ORGAN). The second set uses the settings of its closest relative in the first: UNDERTOW as DARK RING, WIRE CHOIR as SLOW CHAIN, HOLLOW FIFTHS as BEAT FIELD, STORM GLASS as STILL AIR.
- It works on synth tracks only. On a MIDI track the screen shows "DIGIGLIDE: NOT ON MIDI".

LFO, corrected against the tables above:

- The loaded sounds use the unit's own LFO1 (the renders wrote the movement into the data by hand). LFO2 and LFO3 are at their defaults, with no destination.
- Measured in the emulated OS on DARK RING: the LFO reaches the filter, and the sweep is the designed one at the 16 bar rate. The stock LFO swings twice as far as its depth value, so the stored depth is half the figure the tables imply.
- The other LFO sounds (SLOW CHAIN, UNDERTOW, WIRE CHOIR, STORM GLASS, all on AB LEVEL) use the same encoding but were not measured one by one.
- The LFO wave is the sound default, not set to triangle. If the movement sounds stepped or lopsided on the unit, set LFO1 WAVE to TRI.

Known leftovers and limits:

- A small leftover movement, three knob steps at most, on filter resonance, overdrive, amp attack and one more parameter. It comes from the demo sound the patches were built on; its source was not found.
- Checked in the emulator only: the loaded sound reaches the sound engine on the first chord, all ten load. Not yet heard on hardware.

# The deep set (image 33)

Owner on image 32: "the digidrones are too shallow sounding". Measured on the first renders: eight of the ten had nothing under 90 Hz and most had nothing over 1 kHz. From image 33 the ten sounds inside the firmware are reworked for body. Same names, same order, same COUPLE knob, same way to load them. The tables above describe the old set; the values below replace the rows they name, everything else stays. Patches: `~/glide/experiments/b33_patches.py`. Renders: `~/glide/renders/b33/NAME.wav`.

What changed in every sound: an operator an octave down where the voice had none, more FM and feedback under a lower filter, wider operator offsets (slower, wider beating), and chorus, delay, overdrive and more reverb.

The chords changed too. Measured on image 32, several of the old settings played only roots, fifths and a ninth (MAJ with EXT 9 at VOIC 90 gives C2 C3 G3 D4 from a C3 trig), which is part of why they sounded thin. Every drone but HOLLOW FIFTHS now plays the chord's third.

| Sound | Changed rows | Sends REV / CHR / DLY / OD |
| --- | --- | --- |
| 1 STILL AIR | ALGO 6, ratios C 1, A 3, B 1 and 2, offsets A +2.5, B1 -2.0, B2 +3.5, A LEVEL 20, B LEVEL 18, filter 104 | 75 / 70 / 15 / 0 |
| 2 SLOW CHAIN | B ratios 1 and 0.5, offsets A +1.6, B1 -1.2, B2 +2.4, A LEVEL 46, B LEVEL 42, FDBK 14, filter 98, reso 14 | 68 / 50 / 20 / 18 |
| 3 DARK RING | B ratios 1 and 0.5, A LEVEL 54, B LEVEL 48, FDBK 46, filter 56, reso 38, LFO on the filter over 16 bars | 72 / 40 / 28 / 24 |
| 4 IRON BELLS | A LEVEL 80, B LEVEL 58, FDBK 20, amp REL 108 | 84 / 34 / 44 / 0 |
| 5 BEAT FIELD | ratios C 1, A 3, B 1 and 2, A LEVEL 34, B LEVEL 30, filter 106 | 72 / 62 / 12 / 10 |
| 6 GLASS ORGAN | ratios C 1, A 3, B 2 and 3, A LEVEL 16, B LEVEL 16, MIX 60, filter 108 | 62 / 78 / 0 / 8 |
| 7 UNDERTOW | A LEVEL 54, B LEVEL 46, FDBK 42, filter 84, reso 18, LFO on AB LEVEL over 16 bars | 66 / 42 / 18 / 44 |
| 8 WIRE CHOIR | ratios C 1, B 1 and 2, A LEVEL 50, B LEVEL 30, FDBK 32, filter 102, LFO on AB LEVEL over 16 bars | 68 / 66 / 20 / 12 |
| 9 HOLLOW FIFTHS | ratios C 1, A 3, B 2 and 3, offsets A +1.5, B1 +2.2, B2 -1.8, A LEVEL 24, B LEVEL 20, filter 108 | 74 / 60 / 16 / 8 |
| 10 STORM GLASS | A LEVEL 40, B LEVEL 34, FDBK 24, filter 100, reso 12, LFO on AB LEVEL over 8 bars | 78 / 52 / 34 / 14 |

Ratio values are the stock table's rows as the patch file sets them; read them off the unit after a load rather than from this table if you want the dial positions.

DigiGlide settings a load now sets:

| Sound | Settings |
| --- | --- |
| STILL AIR, STORM GLASS | VCNT 4, GLID 2 bars, HOLD on, DRFT 30, VIB 2, TYPE MAJ, EXT MAJ7, VOIC 90, FAN 24 |
| SLOW CHAIN, WIRE CHOIR | VCNT 4, GLID 1 bar, HOLD on, DRFT 12, VIB 3, TYPE MIN, EXT 7, VOIC 90 |
| DARK RING, UNDERTOW | VCNT 4, GLID 2 bars, HOLD on, DRFT 10, VIB 2, TYPE MIN, VOIC 70 |
| IRON BELLS | VCNT 4, GLID 1/2, HOLD on, DRFT 20, VIB 4, TYPE MAJ, EXT 6, VOIC 100 |
| BEAT FIELD | VCNT 4, GLID 4 bars, HOLD on, DRFT 6, VIB 0, TYPE MIN, VOIC 70, FAN 30 |
| GLASS ORGAN | VCNT 4, GLID 2 bars, HOLD on, DRFT 4, VIB 0, TUNE PURE, FAN 40, TYPE MAJ, EXT MAJ7, VOIC 90 |
| HOLLOW FIFTHS | VCNT 4, GLID 4 bars, HOLD on, DRFT 6, VIB 0, TYPE 5TH, VOIC 127, FAN 24 |

Limits: judged from renders and measurements only, not heard on hardware. The sounds are louder and busier than the old set (overdrive, more FM); if one is too much, turn its overdrive and A LEVEL / B LEVEL down first. All ten drones now want 4 voices.
