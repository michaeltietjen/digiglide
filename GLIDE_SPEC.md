# DIGIGLIDE: Brickglide for the Digitone II

Nov 9, 2026 · Michael Tietjen · rev 3 (Nov 10, 2026): rebuilt around Brickglide's actual behaviour

## Overview

DigiGlide brings Brickglide to the Digitone II. A track holds a chord, and on each new chord its voices glide into the next one along shaped paths, with Brickglide's Moves (Bloom, Cascade, Spiral...), timing styles, drift and scrubbing. It's for ambient pads and slow harmonic movement.

- **Target:** Digitone II, built with the [digitone-2-modding-skill](https://github.com/complex-ping/digitone-2-modding-skill) in Claude Code.
- **Base OS:** 1.11 (the skill's target). A port to 1.12 to coexist with [Overtone](https://github.com/complex-ping/overtone) is a later milestone.
- **Reference implementation:** Brickglide, in [michaeltietjen/brickchord](https://github.com/michaeltietjen/brickchord), `brickchord/ambient.py` and `brickchord/engine.py`. **When this spec and Brickglide disagree on musical behaviour, Brickglide wins**, except where the Digitone forces a change (noted below).
- **Gap it fills:** existing DN2 mods on [elektronmods](https://elektronmods.com/mods.php?device=8) cover effects, machines and sequencing. None are harmony-focused.

## What it is on the Digitone

DigiGlide is a **pitch brain on top of a stock machine**, not a new sound engine. A track keeps its machine (FM TONE, WAVETONE...), filter, envelopes and FX; DigiGlide adds two parameter pages that decide which notes the track's voices play and how they travel between chords.

- **Brickglide-like sound:** WAVETONE with detuned saw-ish waves, slow amp attack and long release, plus the starter FX below. FM TONE pads work too.
- **Voices:** Brickglide uses 5 drone voices plus an optional sub. DigiGlide targets **up to 6 voices per track** (5 + sub), if the stock voice allocator allows it (open question 1); otherwise 4.

## Musical behavior (from Brickglide)

1. **First trig:** voices attack on the chord, stacked upward from the bass.
2. **Next chord trig while voices are sounding:** no retrigger. Each voice is assigned a chord tone by the voice-leading rule and glides there along the PATH, with the TIME and ORDR spreads, through the MOVE's turning points if one is set.
3. **Next chord trig after the voices have finished:** attacks fresh, no glide.
4. **GLID p-locked to 0:** hard chord change, for punctuation.
5. **Sounding** means the amp envelope hasn't finished, including release. A releasing voice keeps releasing while it glides.
6. **New chord mid-glide:** every voice starts its new glide from its current pitch. No jumps, ever.
7. **Evolve:** a trig with MOVE = EVOL sends every voice to a nearby scale note instead of a chord, which gives the slow harmonic turn of a film cue.

### Voice leading (Brickglide's `amb_voicelead`)

Port this exactly; it is what gives Brickglide its sound:

1. Candidate notes are every MIDI note 24..96 whose pitch class is in the chord.
2. Sort the sounding voices by current pitch, low to high.
3. If BASS is on (and more than one voice): the lowest voice takes the chord **root in the bass octave C2..B2** (MIDI 36..47), the one nearest its current pitch.
4. Each remaining voice, low to high, takes the candidate **above the previous voice's note** that minimises `|candidate - current pitch|`, plus a **2.5 semitone penalty** for a pitch class already used while the chord is still incomplete. That gives complete chords, no crossing, and minimum movement.
5. If no candidate is above the previous voice, take the highest candidate.
6. **SUB on:** the sub voice sits an octave below the bass voice and follows it.

Fewer voices than chord tones: the rule covers the tones low to high and the rest go unplayed. More voices than tones: tones double, as in Brickglide.

## Chords (rev 5, Orchid-style: one key = one chord)

Decided 2026-11-11 (owner), after two flashes showed the chord controls were the problem: the chord side plays like the Telepathic Instruments Orchid. The glide engine, the voice leader, the paths and Moves and the M1 to M5 work stay. SCL, DEG and CHRD are gone, and so is the rev 4 rule of keys choosing scale degrees.

When VCNT is not OFF on a WAVETONE track:

1. **One key = one chord.** The played note is the chord's root, at its own pitch class and octave. Several notes at once (within 40 ms) are one event and the lowest is the root.
2. **DigiGlide owns every note on the track.** Sequencer trigs, chord mode, held keys and MIDI in all arrive as note-ons on the track's voices; none reaches the DSP as stock sent it (`mod/digiglide.c`, `dg_tx`). The track's VOICES (VOICE menu) is raised to VCNT automatically ("VOICES SET TO 5", or "VOICES 4 OF 5" when other tracks hold the rest) and put back when VCNT goes OFF: to what it was when this session raised it; to the default when the voices came with the kit from an earlier session (VCNT switched off, or at the first look after power-on at a sound that was a DigiGlide sound and holds 3 to 6). When the reservation leaves no free voice the message is "OTHER TRACKS: NO VOICES": stock gives tracks without reserved voices only the unreserved ones, so they are silent. With fewer than 3 voices the track plays stock notes. One DigiGlide track plays at a time.
3. **Chord tones:** TYPE and EXT, or KEY. With KEY set and the root in its scale, the triad and the 6 / 7 / 9 are the scale's own (each root gets its diatonic quality: I a major seventh, V a dominant seventh, VII of a major key half-diminished); MAJ7 is always literal. A root outside the scale, KEY OFF, or a p-locked TYPE / EXT on the step uses TYPE's triad and EXT's literal intervals.
4. **Voices.** The chord voices sit over the root where VOIC (spacing) and POS (position) aim them, each on its nearest chord tone; between chords each is led from where it is (Brickglide), but never from more than a fifth away from its VOIC / POS place, so the chord stays around the key and cannot creep. Turning VOIC or POS while a chord sounds glides the voices to the new voicing.
5. **Bass:** a separate mono voice on the root, BASS's octaves down: Follow (under the chord), Solo (alone, the chord muted) or Off.
6. **GLID 0** = no glide: every chord retriggers. Otherwise a chord change glides whenever voices sound, and a chord that was released but still rings (within the sound's amp release) counts as sounding: the next chord attacks again and glides from it.
7. **HOLD on:** a chord keeps sounding after key release, the next chord glides from it, the same key again releases it, [STOP] releases it. Sequenced trigs follow their note length (a note counts as sequenced when the sequencer plays and the track's current step has a trig).
8. **The pages show the sounding chord by name** over the title ("C MAJ7", "D MIN7", "G 7", "B MIN7B5"), changing with every chord played.
9. **Defaults on first use.** Stock sounds hold leftover values in DigiGlide's slots (39 where SCRB first lived: every glide stopped a third of the way on the unit). The first time VCNT is on for a sound that was never a DigiGlide sound (its HOLD slot holds neither 0 nor 0x0100), every parameter is given its default.

Later builds (owner's additions, 2026-11-11): **PLAY modes** (Strum, Slop, Arp, Pattern, Harp from Brickchord's `engine.py`; struck notes need their own envelope, so pad plus strum wants an accent track); **the performance key layout** (7 chord keys, 4 type keys, 4 extension keys, HOLD; LEDs green / blue / purple / red; recorded trigs storing root, type and extension; a LAYOUT setting); a SPRD knob. All of these need more than the 17 saved slots a WAVETONE sound has free, so extending what a sound saves comes first.

Tests: `mod/tests/test_rev5.py`.

## Rev 6: every machine, settings owned by the track (2026-11-13, image 15)

Decided by the owner: DigiGlide is a track setting saved with the kit, not part of a sound. Any FM TONE, WAVETONE, FM DRUM or SWARMER sound can be loaded on a DigiGlide track and the chords stay. There is no new entry in the MACHINE menu. Where this section and an older one disagree, this one holds.

- **Where the settings are.** 18 bytes a track in the kit's record of the working project image (the copy the box keeps across power-off and writes with a project SAVE). A kit record uses 0x28af bytes of its 0x2a00-byte slot; DigiGlide keeps "DGK1" and 16 x 18 bytes in the 337 spare bytes after it. Stock neither writes nor reads them (naturarum/dn2-cfw T6.0, from the 1.12 serializer and loader; in the emulator a pattern written there survives a sound edit, a pattern save, a reload and playing; on the owner's unit they were zero in all 129 kits). A kit is not written until a DigiGlide setting on it is changed. Each pattern has its own kit, so the settings are per pattern and per track.
- **A track never set up** reads as the defaults with VCNT OFF. Its first setting writes the defaults for that track, then the setting.
- **Machines.** Every synth machine (0..3). On a MIDI track the shortcuts answer "DIGIGLIDE: NOT ON MIDI". The chord voices carry the track's own sound record and machine word, as before.
- **Pages.** CHORD, MOTION and SETUP follow each machine's own SYN pages (FM TONE 4 + 3, WAVETONE 3 + 3, FM DRUM 4 + 3, SWARMER 1 + 3). DigiGlide draws them in place of the whole stock SYN page draw (`0x40018118`), because each machine draws its pages its own way.
- **Knobs.** The 18 parameter records name the kit's FX set, words k 70..87, which stock has no parameter for and sends nowhere. That is one buffer for the kit: the UI copies the selected track's settings into it and copies a turned knob's value from it into the store. The knob rows are copies of stock rows with the lock flag (bit 3) set and the randomiser emptied, because stock files a lock or a randomised value under (track, k) as if k were a sound slot, which would be the filter envelope.
- **P-locks: played, not made.** Locks made with images up to 14 sit in the sequencer's lanes for sound slots 50..64, 93 and 94 of a WAVETONE track. They are still read on a WAVETONE track that has DigiGlide settings, so older patterns play their locked chord changes. A lock value that is not a value of the parameter is skipped (FM TONE's own locks stay in those lanes when a machine is changed). On the other machines those lanes are the machine's own parameters and are not read. **No new lock can be made from the panel in image 15**, on any machine: the knob rows are deliberately unlockable (see Knobs). Making locks is build 16.
- **Which tracks are on.** SETUP's lower row shows the 16 tracks: a track's last digit where DigiGlide is on, a dot where it is off.
- **Older sounds.** A WAVETONE sound made with image 14 or older carries VCNT's code in slot 54 and HOLD's mark in slot 94. On a track that has no settings of its own its 18 values are taken over once; the sound itself is left as it is. After that the track's settings win.
- **Not carried yet:** SAVE KIT, kit copy and paste, the +Drive kit library and exports go through stock's kit serializer, which does not move these bytes. Inside a project the settings stay with the pattern's kit. A later build can hook the serializer and loader (`0x400ddfa8`, `0x400dddb6`).
- **On stock OS** the project loads and plays single notes; stock ignores the bytes and an in-place project save keeps them (Digiwerk's analysis; the save paths were not run by us).
- **To check on the unit:** the settings survive a power cycle and a project save and reload; a new project starts with every track OFF; SWARMER (no emulator coverage: the demo project has no SWARMER track).

## Parameters

Three DigiGlide pages after the machine's own SYN pages. Since rev 6 the values are the track's, kept in the kit, and cannot be p-locked (see Rev 6 above). Until image 14 they were sound slots 50..64, 93 and 94 of a WAVETONE sound.

### Page 4: CHORD

| Knob | Param | Range | Default | What it does |
| --- | --- | --- | --- | --- |
| A | TYPE | MAJ, MIN, SUS, DIM | MAJ | The triad, when KEY does not decide |
| B | EXT | NONE, 6, 7, MAJ7, 9, 6+9, 7+9, M7+9 | NONE | Extensions |
| C | KEY | OFF, C to B (major), Cm to Bm (natural minor) | OFF | Diatonic chords for roots in the scale |
| D | VOIC | 0 to 127 | 127 | Spacing of the chord voices: 0 a tight cluster, 64 close position, 127 wide (the default, owner's choice 2026-11-11) |
| E | POS | -64 to +63 | 0 | Moves the chord voices' position, through inversions and octaves (two octaves each way) |
| F | GLID | 0, 1/16 .. 16 bars, 15 s, 30 s, 60 s | 1/8 bar | Glide time; 0 = retrigger. Stored in stock's portamento-time slot (the TRIG page's PTIM turns it) |
| G | PLAY | CHRD | CHRD | Reserved for the PLAY modes |
| H | HOLD | OFF, ON | OFF | Also [FUNC] + push encoder H |

### Page 5: MOTION

PATH, TIME, ORDR, STAG / MOVE, DRFT, VIB, SCRB, as before:


| Param | Range | Default | What it does |
| --- | --- | --- | --- |
| PATH | Smooth, Linear, Ease, Swell, Bounce, Late, Snap, Wobble, Semitones, Scale steps | Smooth | Glide curve, Brickglide's `PATHS` |
| TIME | Together, By distance, Bass lags, Bass leads, Loose | Together | How long each voice takes, Brickglide's `TIMINGS` |
| ORDR | Together, Low first, High first, Outside in, Random | Together | Which voice starts first, Brickglide's `ORDERS` |
| STAG | 0, 0.5, 1, 2, 3, 5, 8 (in 1/16 steps) | 0 | Gap between voices for ORDR, before the whole change is fitted into GLID |
| DRFT | 0 to 50 cents | 8 | Per-voice slow random detune (Brickglide drones default to 8) |
| VIB | 0 to 50 cents | 4 | Per-voice vibrato depth; each voice runs at its own slow rate (below) |
| SCRB | 0 to 127 | 127 | **Scrub:** how far along the current glide the voices may go. 127 = all the way. Turn it to play the glide by hand, as Brickglide's R2 + stick; put an LFO on it to breathe between two chords |
| MOVE | none, Bloom, Cascade up, Cascade down, Spiral, Swoop, Scatter, Converge, Fall, EVOL | none | How voices travel into this step's chord. P-lock on single steps for gestures |

### Page 6: SETUP

| Knob | Param | Range | Default | What it does |
| --- | --- | --- | --- | --- |
| A | VCNT | OFF, 3, 4, 5, 6 | OFF | **DigiGlide's switch** and the voices used, the bass voice included. Also [FUNC] + push encoder E |
| B | BASS | OFF, FL-2, FL-1, FOL, SL-2, SL-1, SOLO | FL-1 | The bass voice: Follow or Solo, two, one or no octaves under the root |

SPRD has no knob in this build: the stereo spread is Brickglide's default (77).

### Earlier design (rev 3 and 4), kept for reference


Notes:

- **Trig note (rev 3 only; since rev 5 the note is the chord's root):** C5 on screen (MIDI 60, the stock TRIG page default) = no change; other notes transpose KEY by their distance from 60, so keyboard input still works. (Decided 2026-11-10; was "C3".)
- **Note numbering:** the MIDI number Elektron calls C3 is confirmed in M0 and recorded here: `C3 = MIDI 36`.
  *Measured (emulator, OS 1.11, 2026-11-10, `experiments/c3_number.py`):* the TRIG page shows NOTE 48 as "C 4 (48)" and 60 as
  "C 5 (60)", so Elektron C3 = MIDI 36. MIDI numbers in this spec (bass octave 36..47, candidates 24..96) are the
  numbers sent to the DSP; the screen names them one octave higher (36..47 shows as C3..B3).
  The stock TRIG page default note is MIDI 60 (C5 on screen); that is the "no change" trig note (see Trig note above).
- **Vibrato rates:** voice *i* runs at `0.15 + 0.05 * i` Hz (Brickglide's defaults), so voices never move in lockstep.
- **SCRB detail:** while SCRB < 127, each voice sits at `min(glide progress, SCRB / 127)` of the way along its path. Knob moves are smoothed over 60 ms (Brickglide's scrub glide is 0.06 s).

## Glide shapes (port exactly from `engine.py` `amb_shape`)

`p` runs 0..1 over the glide; each shape returns 0..1 of the way to the target:

| PATH | Formula |
| --- | --- |
| Smooth | `(1 - exp(-5p)) / (1 - exp(-5))` |
| Linear | `p` |
| Ease | `e = p*p*(3 - 2p)` |
| Swell | `e + 0.45 * sin(pi*p) * p` |
| Bounce | `1 - (1-p)^4 * cos(3*pi*p)` |
| Late | `q = max(0, (p - 0.65) / 0.35)`, then `q*q*(3 - 2q)` |
| Snap | `q = min(1, p / 0.25)`, then `q*q*(3 - 2q)` |
| Wobble | `e + 0.09 * sin(6*pi*p) * sin(pi*p)` |
| Semitones | linear, quantised to whole semitones on the way |
| Scale steps | walks through the scale's notes on the way (Ease between them) |

A path with turning points (from a MOVE) runs through each point in turn; Brickglide uses Ease between points.

## Timing and Moves (port from `ambient.py` `amb_glide_all`)

**TIME** (per voice, k = 0 for the bass up to 1 for the top voice):

| TIME | Voice glide time |
| --- | --- |
| Together | GLID |
| By distance | `GLID * clamp(semitones moved / 5, 0.35, 2.5)` |
| Bass lags | `GLID * (1.8 - 0.9k)` |
| Bass leads | `GLID * (0.6 + 0.9k)` |
| Loose | `GLID * random(0.6, 1.6)` |

**GLID is the whole change** (2026-11-13; Brickglide differs). GLID is the time from the chord event until the last voice lands, and everything fits inside it:

- Each voice's start delay (ORDR / STAG, a Cascade) and glide time (TIME) are planned as in Brickglide, relative to GLID. Then the latest landing over the voices that move is taken, and every delay and glide time is multiplied by GLID / that landing. The last voice lands exactly at GLID (to the block), no voice later.
- With TIME Together, ORDR Together and no Move nothing is scaled: block for block as before.
- A Move adds no time (Brickglide: at least 2.5 s, and Bloom, Spiral, Swoop and Scatter twice GLID). Its turning points stay at the same proportions of each voice's own glide.
- STAG is the spacing between voice starts before the fit. With ORDR on, the staggers and glides together always exceed GLID, so the spacing heard is STAG x GLID / (GLID + (voices - 1) x STAG): at 120 BPM, GLID 1 bar, STAG 1 step, 5 voices, 0.100 s where STAG says 0.125 s, each glide 1.6 s. The starts stay evenly spaced and in ORDR's order.
- The fit also stretches: if TIME would land every voice before GLID (By distance with small moves), the longest glide is brought up to GLID.
- GLID 0 is a hard change: no Move, no delays.
- Tests: `mod/core/test_glid_fit.py` (model and C core: every MOVE x TIME x ORDR, GLID 1/16 bar to 15 s, 60 to 240 BPM; GLID 1 bar at 90 and 120 BPM lands on the bar line), `mod/core/test_equiv.py`. Demos: `model/render_glid_fit.py`.

**MOVE**:

| MOVE | What the voices do |
| --- | --- |
| Bloom | All gather on the lowest target note, then fan out into the chord |
| Cascade up | One after another, bass first (the starts spread over about the first third of GLID; each voice glides for about two thirds of it) |
| Cascade down | One after another, top first |
| Spiral | Alternate voices swing an octave up or down on the way |
| Swoop | Every voice dips an octave below its target, then rises into it |
| Scatter | Each voice passes through a random scale note within ±7 semitones |
| Converge | All meet at the midpoint between lowest and highest target, then spread |
| Fall | Every voice drops in from an octave above |
| EVOL | Instead of the chord, each voice glides to a random nearby scale note (±5 semitones) |

**Randomness** (Loose, Scatter, EVOL, ORDR Random, DRFT) uses a seed from (pattern, step, voice), so playback and renders repeat exactly. This is a change from Brickglide, which is free-running random; it's needed for repeatable tests.

## Starter sound: "BRICKGLIDE PAD"

Brickglide starts wet and wide (`amb_fx_defaults`). The Digitone version, built from stock FX:

- **Reverb:** large hall character, send at about 50 %.
- **Delay:** dotted 1/4, tape-ish (some damping), send at about 30 %.
- **Chorus:** on, send at about 35 %.
- **SPRD** 77, **DRFT** 8, **VIB** 4, **GLID** 1 bar, **PATH** Smooth, **CHRD** Seventh, **VCNT** 5, **BASS** root.
- **Machine:** WAVETONE, slow amp attack (about 1/2 bar), long release.

Saved as a sound in M4, so any track can load it: loading it turns DigiGlide on (VCNT 5).

*Built (M4, 2026-11-10, `mod/tests/make_brickglide_pad.py`):* WAVETONE, osc 1 and 2 on the PRIM table's saw (WAV 0), osc 2 a few cents up (TUN2 0x4008), osc DRIF 0x2000, amp ATK 0x5400 (slow), HOLD / DEC / SUS full, REL 0x6800 (long), sends REV 0x4000 (about 50 %), DEL 0x2600 (about 30 %), CHR 0x2d00 (about 35 %), and the DigiGlide values above. The reverb's and delay's own character (large hall, dotted 1/4 tape-ish) are the kit's FX settings, not part of a sound: set them in the kit. Saved with stock's own sound converter (`0x400dd6a6`) into `sounds/BRICKGLIDE_PAD.stored.bin`, then loaded into another track (an FM TONE track) with stock's loader (`0x400dd1ea`): it became WAVETONE, named BRICKGLIDE PAD, with VCNT 5, and its first trig played the DigiGlide C minor 7 chord (MIDI 36 43 46 55 60). Every value is listed in `sounds/BRICKGLIDE_PAD.json`, so it can be built by hand on the unit and saved there like any sound. Getting the stored file onto the unit directly (sound pool file or SysEx dump) is not done.

## Switching DigiGlide on and off

Decided 2026-11-10 (owner): **VCNT is the switch**, plus a shortcut.

- **VCNT** takes OFF, 3, 4, 5, 6. It is stored as a code in slot 54: 0 = OFF, 1..4 = 3..6 voices. OFF is the default.
  - **Only the exact codes 0x0100..0x0400 turn DigiGlide on.** Anything else, 0 included, is OFF. This matters because stock sounds are not guaranteed to hold 0 there: slot 54 belongs to FM TONE (AB Attack, default 0x4000), and in the 1.11 demo project 4 of the 7 WAVETONE sounds hold 0x4000 (tracks 1, 3, 4 and 8; `experiments/m4_slot54.py`). So a project or sound saved on stock OS loads with VCNT OFF. The one case this cannot rule out is a sound whose FM TONE AB Attack was set to exactly 1, 2, 3 or 4 (no fine offset) before it was switched to WAVETONE; it would load with DigiGlide on.
  - Other DigiGlide parameters holding a value outside their range (the same FM TONE leftovers) read as their defaults, so switching a stock sound on gives sensible settings.
  - **OFF is exactly stock:** the track plays notes as stock does, and with VCNT OFF on every track the frames sent to the DSP and the renders are byte-identical to stock OS (`mod/tests/test_m4c_switch.py`, A).
  - **A p-lock to OFF** on a step plays that trig as a normal note; a DigiGlide chord still sounding releases. P-locks between voice counts are fine.
  - Switching OFF while a chord sounds releases it at the next block: note-offs for every DigiGlide voice, and each voice keeps its pitch while it rings out (no stuck notes, no clicks). Switching on takes effect at the next trig.
  - DigiGlide's two pages show on every WAVETONE track, so VCNT can be reached while it is OFF.
- **Shortcut: [FUNC] + push encoder E** (VCNT's own knob on the HARMONY page). On the active track it flips VCNT between OFF and the last voice count that track had (5 if none), and shows "DIGIGLIDE ON (5 VOICES)" / "DIGIGLIDE OFF" for about 1.3 s. It writes the same stored VCNT as the knob, so it saves with the sound and project like any edit. The last voice count is kept in RAM while the unit is on; after a reload, a track that was saved OFF comes back with 5.
  - **Why this combo:** every [FUNC] + page key is taken in stock 1.11 (TRIG: QUANTIZE, FLTR: SETUP, AMP: euclidean page, FX: FX page, MOD: the page area cleared; SYN is the MACHINE menu), and so are [FUNC] + [PAGE] (SEQUENCER PAGE SETUP), [PRESET], [+] / [-] (track transpose) and [ARP] (it silently flips a sound byte, +351). [FUNC] + any knob push changes nothing in stock: on every page tried (TRIG, SYN, FLTR, AMP, FX, MOD) the app object, all 16 sounds, the arp state, the playing pattern and the screen are byte-identical to a run without the keys (`experiments/m4_funcany_mem.py`, `m4_combos.py`, `m4_combos2.py`, `m4_ch6.py`). Knob E is where VCNT sits on HARMONY, so the combo is on the DigiGlide page itself.
  - How: the audio ISR hook watches the firmware's key-held bitmap for [FUNC] + E and asks the screen for a redraw; the change and the message are made in the UI task at the end of the screen pass (`0x4011d398`).

## Architecture

The voice leading and the glide paths live on the ColdFire, where they're cheap and testable in digikit. The SHARC only receives a pitch per voice per block and smooths it.

```
ColdFire (CPU)                                         SHARC (DSP)
--------------                                         -----------
Sequencer trig + p-locks (stock)
        |
        v
[NEW] Chord builder   (KEY + SCL + DEG + CHRD, Brickglide CHORDS)
        |
        v
[NEW] Voice leader    (Brickglide amb_voicelead, BASS / SUB)
        |
        v
[NEW] Glide planner   (PATH shape, TIME, ORDR / STAG delays, MOVE turning points, seeded random)
        |
        v
[NEW] Per-block pitch: evaluate each voice's path,
      add DRFT + VIB, apply SCRB limit
        |
        v
Per-voice pitch in the frame  ------------------->  [NEW or reused] per-voice pitch smoothing within the block
                                                                |
                                                                v
                                                    Stock machine voice (FM TONE / WAVETONE, filter, amp, FX)
```

Evaluating paths on the ColdFire means every Brickglide shape and Move is plain C, written once. Whether the per-voice pitch rides an existing frame field (no new SHARC code) is open question 2.

## OS 1.12

Decided 2026-11-10 (owner runs 1.12): **DigiGlide targets OS 1.12**, and still builds for 1.11 (`DG_OS=1.11`).

- 1.12 changes only the ColdFire MAIN OS (section 3, 4,096 bytes longer: Outbox 8 routing of the Main outputs). The bootstrap, the SHARC code (section 7) and section 8 are byte-identical, so the DSP renders, M5 and the DSP side of everything above carry over.
- Every address DigiGlide, its build and its tests use is written as its 1.11 value and mapped by `port/addr_1.12.json` (made and checked by `port/addrmap.py`: code and image data by a masked byte match around the address, RAM by the literals in the mapped code, every reference agreeing). Code below 0x400C0000 did not move; later code moved 0x164 or 0x2E0 bytes; tables 0x410 to 0x540; RAM in 0x42.. and 0x44.. moved 0x1000; 0x8000.. did not move. `mod/osver.py` selects the OS; the sources use `OSA_<1.11 address>` macros. The 1.11 build from the ported sources is byte-identical to DIGIGLIDE_13.
- The build tools' own 1.11 constants (dnfw's loader cave and area, the parameter table and its bounds) are set for 1.12 by `mod/port_os.py` without editing dnfw; the parameter-table scanners still count exactly 56 bases and 55 bounds on 1.12.
- The emulator needed three 1.12 fixes, none in DigiGlide: digikit's device file lists 1.12; the audio ISR's DMA buffers moved 0x8000 up (the harness's faked DMA position now comes from the ISR's own bound); and the skill's Python EMAC hooks came from a 1.11 list (`data/emac_rows_1.12.txt` is the 1.12 one). Before the last fix, stock 1.12 ran but sent empty frames.
- Recovery on 1.12 means the **stock 1.12** file (`Digitone_II_OS1.12.syx`), sent over DIN in the STARTUP menu.

## Build milestones and tests

Each milestone must pass its test before anything is flashed. Commit to git after each milestone passes.

- [x] **M0: Setup and research.**
  - Verify the stock .syx checksum (sha256 `2af43e65e3d8390b41c9f66222620f8cce027d73ed87db00c80b440f628472e0`).
  - Install the skill, run `scripts/dn2setup.py`, and pass both bundled examples (`double_time`, `track_trim`).
  - Clone `michaeltietjen/brickchord` for reference.
  - Record the C3 MIDI number above.
  - Answer the open questions and write the answers into this file.
- [x] **M1: Reference model (host only, no firmware).**
  - Extract Brickglide's `amb_voicelead`, `amb_shape`, `amb_path_at`, the CHORDS / SCALES tables, the Moves and the timings into a standalone Python module, with seeded random.
  - Render WAVs with a simple saw pad of:
    - a I-VI-IV-V progression in C minor with GLID 1 bar;
    - the same progression with each MOVE;
    - each PATH on one chord change.
  - **Stop and let me listen**, and compare with Brickglide on the Brick.
- [x] **M2: C port of the model.**
  - The ColdFire C version, compiled for the host too.
  - Test: across 1,000 seeded random progressions (all CHRD, SCL, MOVE, PATH, TIME, ORDR, BASS values), the C output matches the M1 Python note-for-note, and pitch curves match within 0.1 cent.
- [x] **M3: Chord on one trig (ColdFire, in digikit).**
  - A trig on a DigiGlide track plays the voice-led chord.
  - Test: with KEY C, SCL major, DEG I, CHRD Triad, BASS root, the DSP frame carries C2 (bass) and the chord above it, matching the M1 model. Repeat for every CHRD.
- [x] **M4: Glides, params and p-locks.**
  - Both pages on screen and p-lockable.
  - Tests:
    - a 4-step progression plays from p-locked DEG values, with the frame pitches matching M1 block by block;
    - GLID = 0 gives a hard change;
    - a chord change mid-glide shows no jump;
    - screenshots of both pages;
    - the BRICKGLIDE PAD sound is saved.
- [x] **M5: DSP render.** (passed 2026-11-10 on DIGIGLIDE_13 / OS 1.11; `mod/tests/render_m5.py`, WAVs in `renders/M5/`)
  - A/B render against stock in the SHARC emulator.
  - Tests:
    - each voice's pitch trace matches the M1 curve within ±1 cent; *result:* 0.728 cent at most over 76,800 voice-blocks (the note words sent vs the model 0.195, the quantization of 1/256 semitone; the DSP's pitch vs those words 0.532, measured by demodulating each voice's fundamental from a solo sine render, since the WAVETONE "sine" carries 3rd and 5th harmonics);
    - no pitch step larger than 5 cents between consecutive blocks, except Semitones and Scale steps by design; *result:* 0.391 cent (progression, all 10 MOVEs, midglide), at most 1.562 (Snap, Bounce) over the paths at GLID 1 bar. Very fast glides (GLID 1/16 with Snap or Bounce) still exceed 5 cents per block; an owner decision (DSP smoothing or accept);
    - two renders are bit-identical; *result:* yes;
    - VCNT OFF identical to stock; *result:* frames and render identical (after STOP the OS restores the demo project's 81 BPM over the harness's 90 on both OSes, at a UI-timing-dependent frame: that one word is left out of the last 4 frames).
  - Render the M1 progression as a WAV from the emulator. **Stop and let me listen.**
- [ ] **Later milestone: FM TONE and SWARMER support.** DigiGlide is WAVETONE-only for the first flash (owner, 2026-11-10). What was found:
  - **FM TONE** uses slots 25..33, 35..48 and 50..64 for its own parameters; the only slots it leaves unused that a sound save and load keep are 34 and 49 (slot 65 comes back as 0 after a reload, and 93 / 94 are stock portamento). So the 16 parameters do not fit: FM TONE needs its own storage (a side table saved with the sound or project, and every p-lock routine taught about it).
  - **SWARMER** uses only slots 25..32, so 33..64 (32 slots, all kept by save and load: stored words 41..72) are free. Proposed map: the 16 parameters in slots 49..64, in Params order (no portamento slot needed). To do: prove the SWARMER DSP engine ignores 49..64 (A/B render with junk values, as `experiments/m3_wavetone_slots.py`), a per-machine slot map in the hook and the records, SWARMER's page count and descriptors, and tests that each machine's own sound is unchanged with VCNT OFF and that switching a track's machine keeps or safely resets the DigiGlide values.
- [x] **M5.5: Regression.** (passed 2026-11-10 on DN2_1.12_DIGIGLIDE_1 / OS 1.12; `mod/tests/test_m55_regression.py`)
  - Stock projects load unchanged. *Result:* after loading the demo project, the app object (451,596 bytes), the 16 live sounds and the playing pattern are byte-identical to stock 1.12.
  - Non-DigiGlide tracks render identically to stock. *Result:* with DigiGlide playing 4 chords on track 1 and 8 other tracks playing, 6,004 frames carry voices 6..15 and the FX block byte-identical to stock, and their render is bit-identical.
  - DigiGlide params survive save and reload. *Result:* `test_m4c_switch.py` C (stock's converters) and `make_brickglide_pad.py` on 1.12; the stored BRICKGLIDE PAD is byte-identical to the 1.11 one.
  - Static hardware-rule checks pass. *Result:* DigiGlide ships Elektron's section 7 unchanged (byte-identical to stock), so the SHARC rules hold as in stock; `dnfw inspect` is all ok (Elektron's limits, HMAC, 2 MiB buffer).
  - Also on 1.12: M3, M4a, M4b, M4c and the M5 checks pass; the progression's 31,954 frames are byte-identical to the 1.11 build's (bar the post-STOP tempo word).
- [ ] **CORE (scope freeze, owner, 2026-11-11).** Until the owner says otherwise this is the only goal: a solid core on the unit. Nothing else is worked on.
  - The core, each item confirmed on the unit by the owner:
    1. twelve keys give twelve chords in the set key;
    2. chord changes glide;
    3. HOLD works (played by hand, recorded, played back);
    4. no stock notes underneath;
    5. live recording and grid recording work, and play back as they sounded;
    6. DigiGlide off is identical to stock.
  - Open against the core (see `notes/build_log.md`, builds 8 and 9):
    - HOLD on, sequenced playback, slow-attack sound: silent on builds 7 and 8 (every trig struck the chord again and restarted the amp envelope). Fixed in build 9 in the emulator; not yet confirmed on the unit.
    - HOLD off, slow-attack sound: each new chord after a gap fades in from silence (DigiGlide reuses its voices; AMP RSET on restarts the envelope). Workaround: AMP RSET off on the sound, by hand. Forcing it from the hook broke live recording in the emulator and is not understood.
    - Reserved voices: confirmed on the unit that a full pool silences the other tracks; the warning and the hand-back are in build 8, the 2 s start-up wait is untested on the unit.
    - The live-recording brief is not finished: HOLD recorded as a parameter lock by live recording (seen on the unit), and the stock features the note interception might break (retrigs, trig conditions, MIDI out, track mute under a held chord, sound locks) are untested.
    - Item 6 is proven in the emulator only (`test_m55_regression.py`); on the unit it has not been checked since build 1.
- [ ] **Parked until the core is confirmed (owner, 2026-11-11). Not to be worked on.**
  - **Arp** (stock arpeggiator as the clock for DigiGlide's Arp mode; design brief and stock findings in `notes/build_log.md`, "Arp investigation").
  - **Live function keys** (the performance key layout: type and extension keys with LEDs, recorded with the trig).
  - **Strums** and the other PLAY modes (Strum, Slop, Harp, Pattern), with the storage extension they need.
  - **Accent track.**
  - **Sound pack** and importable presets.
  - Also waiting: FM TONE and SWARMER support (below), VCNT counting chord voices only, the fast-glide step decision.
- [ ] **M6: First flash.** Only after asking.
  - **Before:** DIN MIDI recovery interface connected, the stock OS 1.12 file on hand, +Drive backed up.
  - **Listen test on the unit:**
    - glides smooth;
    - no clicks or zipper noise;
    - SCRB playable by hand;
    - other tracks unaffected;
    - no stuck notes after stop.
- [ ] **M7: Polish and release.** Video demo, Brickchord site page, elektronmods listing. (The 1.12 port moved forward: see "OS 1.12".)

### Later milestone: a personal build with Digiwerk (not started)

For the owner's unit only: DigiGlide together with Digiwerk (naturarum/dn2-cfw, GPL-2.0-or-later). This is a reading of both sources (Digiwerk at c3cf6c2, 2026-11-10; elekloader/elekloader at 59acfff, 2026-11-13; DigiGlide image 15), all addresses OS 1.12. Nothing here was built or run. Digiwerk's main-OS changes are elekloader format-2 mods on naturarum's fork (its own core-dn2 0.2), not on upstream core-dn2 0.4. Most hard collisions come only with its compressor ("C" packs: param-grow, param-rows, comp-ui, comp-link).

| Where | DigiGlide | Digiwerk | Collision | Can DigiGlide move cheaply now? |
| --- | --- | --- | --- | --- |
| Parameter table operands | 56 bases repointed, 55 bounds +18 (dnfw paramtable, table built at build time) | param-grow: the same 56 bases, 57 bounds to 0x180, table copied at boot to 0x47D00000 (C packs) | Hard | No. DigiGlide becomes a client of Digiwerk's grown table: build-time coordination |
| Display-row reader 0x400C257C | `jsr dg_row_stub` (10 bytes) | `jmp pg_disp_get` (C packs) | Hard, same instruction | No. Same answer: use Digiwerk's row service (it offers a borrowed display entry, flags, no randomiser) |
| Table entries | 321..338 | 321..340 compressor, 341 parked trig slides | Hard in C packs | Partly: ids from the top (366..383) are one constant, but only inside the shared table |
| Live FX words (knob edit buffer) | k 70..87 | k 70..89 compressor, k 70..96 sent to the DSP and saved | Hard in C packs: DigiGlide's knob values would be read as band settings | No: only k 90..100 are free there (11, DigiGlide needs 18). The buffer needs another home |
| Stock rows edited in place | The relocated table is a copy of the stock one | lfo-dejavu, flanger and echo names patch stock rows (every pack) | Medium, silent: those edits are lost in DigiGlide's copy | Yes: build the table from the Digiwerk image, a small build change |
| Appended code | dnfw area at the stock image end 0x4030C980, runs at 0x46800000..0x4680F570 | Blob at the same image end, runs at 0x47E00000..0x47F00000 | Build time only (RAM does not overlap) | Yes: place DigiGlide's area after Digiwerk's blob (`port_os.py` sets the address); the stock-hash check and preflight must accept a Digiwerk image |
| Audio interrupt | 0x40025E82 | 0x40025e9e (C), 0x400272d4, 0x400269e6, 0x40026d86; frame tail 0xa80..0xabb | Near miss: different instructions, different frame bytes | Not needed. The combined interrupt time must be measured |
| SysEx router 0x4012197A | The probe (device 0x7D) | Not hooked on the fork; upstream core-dn2 0.4 hooks the same 6 bytes | None on the fork | Yes if needed: subscribe to the core's SysEx event |
| SYN page hooks 0x400C2636, 0x400C2656, draw 0x40018118 | Yes | None; upstream's optional machines-dn2 hooks the two page sites | None with Digiwerk | n/a (do not link machines-dn2) |
| Stored kit record | +0x28af..+0x29d2 ("DGK1" + 288 bytes, the padding) | FX record +0x60..+0x97 = kit record +0x170c..+0x1743, check word 0xC3B1 | **None.** Digiwerk names the padding only as a further candidate, unused | Not needed |
| Kit serializer | No hook today (planned: 0x400ddfa8, 0x400dddb6) | comp-link hooks 0x400dcf34, 0x400dcef0 and a vtable word (C) | Near miss | Yes: stay off those two functions' first bytes |
| DSP | No DSP change; up to 5 more voices of a track sound | Replaces section 7; code room 80,404 of 83,838 bytes in the largest pack; estimated 73 to 77 % load typical, about 84 % worst (its notes) | Load only. If stock renders all 16 voices every block (open question 4), the chord voices add nothing; unconfirmed on a unit | n/a. The preflight must allow a non-stock section 7 |
| Keys, pages, messages | [FUNC] + push E / F / G / H, three SYN pages, device id 0x7D | [FUNC] + turn on flanger SPD, MIXER pages 5 to 7, a fourth USB CONFIG item, arp menu | None found | n/a |

**Kit bytes: no move proposed.** The stored bytes do not overlap, and Digiwerk's serializer hooks write only their own words. What overlaps is the live edit buffer (FX k 70..87), which holds nothing a project depends on: the store is the padding. Moving the buffer changes no saved data, so it can wait for this milestone. Optional, cheap and worth doing before more projects exist only if Digiwerk ever claims the padding: move "DGK1" to the end of the padding (+0x28dc..+0x29ff) and keep reading the old place.

**Route.** elekloader's linker refuses two mods that touch the same bytes, overlapping regions, duplicate names, more than one core and undeclared image changes. It does not check shared FX slots, row ids (unless claimed, as Digiwerk does with `param-row:<id>`), kit padding, interrupt time or key combos. Upstream core-dn2 0.4 has no parameter-row or kit service on the Digitone II and its hooks collide with Digiwerk's comp-link, so the cleaner route is DigiGlide as a mod on **Digiwerk's fork**, not on upstream: drop dnfw's loader, area and paramtable, link relocatable, declare the 6 sites (interrupt, two SYN, draw, screen pass, SysEx), contribute 18 rows to its row collection, and find a new home for the edit buffer. Licences allow it for a personal build (GPL-2.0-or-later with AGPL-3.0-or-later combines under version 3 terms; a reading, not legal advice). The cheapest first step is smaller: a Digiwerk pack without the compressor, with DigiGlide applied on top of the Digiwerk main image (table built from that image, area moved after its blob, hash checks relaxed).

Not determined: the fork's core and built mods were not in the clone (site lists come from its scripts and notes); the interrupt cost of Digiwerk's hooks and the combined ColdFire budget; combined flash headroom; whether DSP load depends on sounding voices; whether another parameter set has 18 free unsaved words for the edit buffer; how Digiwerk's arp and DigiGlide's planned arp sit together.

## Risks, open questions, safety

The biggest unknown is how the stock OS allocates voices per track; M0 / M3 answer it before any DSP work.

**Open questions (answer in M0 and write answers here)**

1. How many voices can one track hold (is 6 possible), and how does stock voice stealing behave when a chord needs them? *Answer (emulator, 2026-11-10):* **6 is possible.** The DSP renders 16 voices shared by all tracks. By default every track is DYN: its notes land anywhere in the pool and steal from other tracks. Through the stock VOICE setter (`0x40029094(cfg, track, n)`, the VOICES field of the VOICE menu) a track reserves n voices: track 1 with 6 (also 7 and 8) reserved got voices 0..n-1 to itself and every other track stayed on n..15 (`experiments/q1_reserve6.py`, `q1_reserve.py`). Writing the config byte directly does nothing; only the setter's change notification rebuilds the allocator. So DigiGlide's track reserves 6 voices (VCNT counts the sub when BASS is root+sub) and DigiGlide drives exactly those; no stealing between DigiGlide and other tracks, at the cost of a smaller shared pool for the rest of the kit.
2. Can a per-voice pitch per block ride on existing fields in the ColdFire to DSP frame, or does smoothing need new SHARC code? *Answer (emulator, 2026-11-09):* **It rides on the frame.** The per-voice note word (frame +0x02+2v, MIDI note << 8) is read by the DSP every block, fractional byte included (1/256 semitone = 0.39 cent), and changing it without a note-on bends the sounding voice with no new attack (`experiments/q2_note_word.py`: 60 -> 60.59 for +0x80, a 67 -> 69 ramp tracked block by block, same level as the control). Glides on the M3 build matched the frame words within 0.07 semitone in the DSP's own voice buffers. **Within a block (measured in M0, 2026-11-10, `experiments/q2b_block_smoothing.py`):** the DSP does **not** ramp. A new note word takes effect as a hard step 11 to 12 samples into the block after the one that carried it (about 0.9 ms latency) and holds for the rest of that block; the oscillator phase stays continuous (no click; tested with an octave jump and a 25-cent step on a sine). So pitch reaches the DSP as a 1500 Hz staircase with steps exactly as large as the per-block moves we send. Slow glides move well under 5 cents per block, but the fastest cases (GLID 1/16 with Snap or Bounce and a leap of several semitones) reach 15 to 25 cents per block, so those will fail M5's 5-cent rule unless the ColdFire limits the per-block step or the SHARC gets per-sample pitch ramping. Decided at M5.
3. Where can two extra parameter pages (16 params) live without breaking project files saved on stock OS? If only one page fits, which 8 params stay (suggested: KEY, DEG, CHRD, MOVE, GLID, PATH, TIME, SCRB) and where do the rest go (a settings page)? *Answer (static, 2026-11-10):* **Both pages fit on a WAVETONE track; not on FM TONE.** A sound has 101 value slots, all owned by some parameter, but slot ids 25..64 mean different things per machine. WAVETONE uses 25..49 only, so on a WAVETONE track **slots 50..64 (15 slots) belong to FM TONE / FM DRUM parameters and WAVETONE never reads them**; portamento time and on/off (slots 93, 94) are ColdFire-only and meaningless under DigiGlide. That is 17 slots for 16 params plus an on/off flag. They are saved with the sound by stock code, and the stock p-lock, LFO and copy routines all accept slots <= 100, so p-locks work without new storage. A project saved with DigiGlide loads on stock OS as a plain WAVETONE track (the values sit in slots it ignores). To do: prove in M3 that the WAVETONE DSP engine ignores those slots (A/B render with junk values), and add 16 parameter records (relocated table, as dnfw's LFO4 does) plus page / label / value-text hooks (as dnfw's Waverider pages do). FM TONE uses nearly every slot up to 64 (free: 34, 93, 94), so DigiGlide on FM TONE needs the heavy route (own storage and every lock routine hooked); proposed as a later milestone. **Final layout (M4, 2026-11-10):** parameters in slots 50..64 and SCRB in 93, the ones a sound save and load keep (stored words 58..72 and 100; slot 65 comes back as 0 after a reload and slot 100 is not saved, `mod/digiglide.c`); no separate on/off flag: VCNT is the switch (see "Switching DigiGlide on and off"), so slot 94 stays stock.
4. Is there DSP budget for per-voice smoothing at full polyphony? *Answer (2026-11-09):* With pitch in the frame (question 2) the DSP does **no new work**: stock renders all 16 voices' engines every block whether they sound or not, and a glide is only a different number in an existing word. If question 2's open part shows fast glides need per-sample ramping, that is a short per-voice ramp of the pitch increment for at most 6 voices (well under 1 % of the ~666k cycle block budget by instruction count), but it means new SHARC code with the skill's hardware-rule checks; decided at M5.
5. Can the ColdFire evaluate 6 voice paths per block within the audio ISR budget (Smooth uses exp; a lookup table is fine)? *Answer (estimate from measurement, 2026-11-10):* **Yes, with fixed point and tables.** The MCF5445x has no FPU, so floats would be soft-float library calls: the C port uses fixed point (pitch in 1/1024 cent internally, 1/256 semitone in the frame) and lookup tables for exp, sin and cos. Measured on the M3 build: stock's audio ISR runs ~43,800 instructions on average (max ~57,100); the 4-voice build added ~900 on average (max ~1,180), mostly copying sound records. Estimate for 6 voices: ~80 to 120 instructions per voice per block for path, drift, vibrato and scrub, plus ~450 for 5 record copies, about 1.2k to 1.6k per ISR (~3 % of stock's count, ~12 % of its time at the skill's ~4x cycles per instruction for code in DDR; stock is ~64 % busy). Per-trig work (voice leading over at most 73 candidates for 6 voices, Move planning) runs only on trig blocks and can be spread over the next blocks if needed. Measured again at every milestone from M3.

**Risks**

- This is far bigger than the bundled examples. Expect several sessions; this file is the memory between them.
- Emulators miss some hardware rules. The skill warns each such rule once silenced a real unit, so run its static hardware-rule checks every build.
- Projects saved with DigiGlide may not load cleanly on stock OS. Back up the +Drive before M6.

**Safety**

- **Recovery:** hold FUNC at power-on, press TRIG 4, then send the stock OS over **DIN** MIDI (USB doesn't work in this mode), about 12 to 15 minutes. This is confirmed by the skill's `references/setup.md`. Keep a USB-to-DIN MIDI interface on hand.
- Flashing modified firmware may affect warranty.
- Never redistribute Elektron's firmware or modified images. Release DigiGlide as source plus a patcher, the way Overtone does.

## Kickoff prompt for Claude Code

Paste this into Claude Code after installing the skill, with this file as `GLIDE_SPEC.md` in the workspace.

```markdown
Use the digitone-2-modding-skill. Read GLIDE_SPEC.md, the spec for DigiGlide: Brickglide's chord glides as a pitch brain for Digitone II tracks.

1. Initialize a git repo here and commit GLIDE_SPEC.md. Commit after each milestone passes.
2. Verify my stock OS 1.11 .syx at <path> against the sha256 in the spec. Stop if it doesn't match.
3. Run scripts/dn2setup.py and fix anything missing, then build and pass both bundled examples in the emulators.
4. Clone github.com/michaeltietjen/brickchord for reference. Brickglide's code in brickchord/ambient.py and brickchord/engine.py is the reference for all musical behaviour.
5. Answer the open questions using the skill's reference notes and write the answers into GLIDE_SPEC.md before writing DigiGlide code. If an answer changes the plan, tell me before continuing.
6. Do M1 and stop so I can listen. Then work milestone by milestone (M2 to M5.5), passing each milestone's test and running the hardware-rule checks before moving on. Stop again at M5 so I can listen.
7. Stop before M6 and ask me before flashing anything to the unit.
8. House rule: no em dashes in any output (code comments, docs, commit messages, UI text, chat).
```
