# DigiGlide sound pack: 20 new sounds for Digitone II

Nov 10, 2026 · Michael Tietjen · rev 1

Twenty original sounds designed for the Digitone II's own engines, each paired with DigiGlide settings that suit it. They don't copy Brickglide's patches; between them they use every PATH, TIME, ORDR and MOVE, and most chord types.

**How to read this:** sound settings are **musical targets** (Hz, seconds, character), because exact knob values depend on the Digitone's parameter ranges. The local Claude session finds the real values in the emulator (see "Building them" at the end) and fills in a dial-in table for each sound.

**Design rules for every sound**

- Sustaining or slow-decaying, so voices are still sounding when the next chord arrives (that's when DigiGlide glides instead of retriggering).
- Pitch-stable oscillators: no pitch envelopes fighting the glide.
- Amp release long enough to cover the glide's tail.
- Loudness matched within 1 dB across the pack.
- Only Elektron's built-in waves and tables.

**Machines (decided 2026-11-10):** DigiGlide is WAVETONE-only for the first flash. FM TONE leaves too few unused slots for DigiGlide's 16 parameters, so FM TONE and SWARMER support is a later milestone (GLIDE_SPEC.md). The ten FM TONE and SWARMER sounds below are rebuilt on WAVETONE, as close to their character as possible (detuned oscillators plus DRFT and SPRD for the swarm sounds, bright tables with phase distortion for the bells and plucks), and marked "WAVETONE version".

**Key to the DigiGlide rows:** VCNT voices · BASS · CHRD chord · GLID time · PATH · TIME · ORDR / STAG · MOVE (p-locked on one step unless "always") · DRFT / VIB in cents · SPRD spread.

## Overview

| # | Name | Engine | Character | Shows off |
| --- | --- | --- | --- | --- |
| 1 | GLASSHOUSE | WAVETONE | Clear, glassy, floating | Lydian chords, Outside-in order |
| 2 | NIGHT FERRY | WAVETONE version (was SWARMER) | Dark, wide supersaw haze | 8-bar glides, Bass lags |
| 3 | VELVET HALL | WAVETONE version (was FM TONE) | Soft, warm, rounded | Major 9 with the Swell path |
| 4 | SLOW TIDE | WAVETONE | Breathing, oceanic | SCRB on an LFO |
| 5 | POLAR | WAVETONE + COMB+ | Cold, crystalline, metallic air | Quartal, Converge |
| 6 | BELL GARDEN | WAVETONE version (was FM TONE) | Soft inharmonic bells | Snap path |
| 7 | TEMPLE GLASS | WAVETONE + COMB- | Resonant, hollow, ritual | Scale steps path |
| 8 | CHIME FIELD | WAVETONE version (was FM TONE) | Shimmering, scattered | Cluster with Scatter |
| 9 | IRON DRONE | WAVETONE version (was SWARMER) | Heavy, low, slow-turning | EVOL, 16-bar glides |
| 10 | DUST CHOIR | WAVETONE | Breathy, vocal, old | Wobble path |
| 11 | STATIC BLOOM | WAVETONE (noise) + COMB+ | Pitched noise, ghostly | Bloom |
| 12 | FOG LIGHTS | WAVETONE | Muffled, slowly opening | Late path |
| 13 | ELECTRIC DUSK | WAVETONE version (was FM TONE) | Electric piano, mellow | Short jazzy slides |
| 14 | MUTED STRINGS | WAVETONE | Small string section | Semitones path |
| 15 | KALIMBA DRIFT | WAVETONE version (was FM TONE) | Plucked, woody, ringing | Bounce path |
| 16 | GLIDE BASS | WAVETONE | Round bass with slides | Root + sub, fast glides |
| 17 | SUNBEAM | WAVETONE version (was SWARMER) | Bright, rising, hopeful | Cascade up, Low first |
| 18 | BROKEN RADIO | WAVETONE + SRR + drive | Lo-fi, detuned, nostalgic | Heavy drift, Loose |
| 19 | AURORA | WAVETONE version (was SWARMER) | Huge, wide, 6 voices | Spiral, Swell |
| 20 | ALMOST STILL | WAVETONE version (was FM TONE) | Barely moving, meditative | EVOL every other bar |

---

## Pads

### 1. GLASSHOUSE

Clear and glassy, floating above everything.

- **Sound:**
  - WAVETONE, two oscillators on a bright glassy table, ±6 cents.
  - Phase distortion slightly up for sparkle.
  - MULTIMODE low-pass at about 4 kHz, low resonance.
  - Amp attack 0.8 s, release 3 s.
- **Sends:** reverb 55 %, delay 25 % (dotted 1/4), chorus 20 %.
- **DigiGlide:** VCNT 5 · BASS off · CHRD **Lydian** · GLID 1 bar · PATH Ease · TIME Together · ORDR **Outside in** / STAG 1 · MOVE none · DRFT 6 / VIB 3 · SPRD 100.
- **Play it:** I to II to I in a major key. The raised fourth glides in and out.

### 2. NIGHT FERRY (WAVETONE version)

Dark, wide supersaw haze, like lights across water.

- **Sound:**
  - SWARMER, detune medium, mix towards the swarm.
  - LOWPASS 4 at about 700 Hz; the filter envelope opens slightly over 2 s.
  - Amp attack 2 s, release 5 s.
- **Sends:** reverb 60 %, delay 20 %, chorus 0 (the swarm is already wide).
- **DigiGlide:** VCNT 5 · BASS root · CHRD **Minor 11** · GLID **8 bars** · PATH Smooth · TIME **Bass lags** · ORDR Together · MOVE none · DRFT 10 / VIB 3 · SPRD 110.
- **Play it:** two chords per pattern, a slow minor i to VI. The bass arrives last, like a ship docking.

### 3. VELVET HALL (WAVETONE version)

Soft, warm, rounded. The "nice" pad.

- **Sound:**
  - FM TONE with a low modulation index for a gentle, mellow tone, ratio 1 : 1 with a little feedback.
  - LOWPASS 4 at about 1.5 kHz.
  - Amp attack 1 s, release 4 s.
- **Sends:** reverb 50 %, delay 15 %, chorus 30 %.
- **DigiGlide:** VCNT 5 · BASS root · CHRD **Major 9** · GLID 2 bars · PATH **Swell** · TIME Together · ORDR Together · MOVE none · DRFT 6 / VIB 4 · SPRD 80.
- **Play it:** I, IV, vi, V. The Swell path gives every change a slight lift.

### 4. SLOW TIDE

Breathes between two chords on its own.

- **Sound:**
  - WAVETONE, a smooth, soft table, ±8 cents.
  - LOWPASS 4 at about 1 kHz, with an LFO on cutoff (very slow, small depth).
  - Amp attack 1.5 s, release 4 s.
- **Sends:** reverb 55 %, delay 25 %, chorus 25 %.
- **DigiGlide:** VCNT 4 · BASS root · CHRD **Sus4** · GLID 4 bars · PATH Smooth · TIME Together · ORDR Together · MOVE none · DRFT 8 / VIB 2 · SPRD 90.
- **Special:** an LFO on **SCRB** (triangle, 2 to 4 bars per cycle, full depth), so the voices sweep back and forth along the glide between two chords. If SCRB can't be an LFO destination, note it and set SCRB by hand.
- **Play it:** alternate two chords every 4 bars and let the LFO do the rest.

### 5. POLAR

Cold, crystalline, metallic air.

- **Sound:**
  - WAVETONE with a thin, bright table plus a little noise.
  - **COMB+** filter tracking the note, with moderate feedback for a ringing, tuned shimmer.
  - Amp attack 1.2 s, release 4 s.
- **Sends:** reverb 65 %, delay 20 %, chorus 0.
- **DigiGlide:** VCNT 4 · BASS off · CHRD **Quartal** · GLID 2 bars · PATH **Linear** · TIME Together · ORDR Together · MOVE **Converge** · DRFT 4 / VIB 0 · SPRD 120.
- **Play it:** stacked fourths that meet in the middle, then spread apart. The comb rings as the voices slide.

## Bells and metal

### 6. BELL GARDEN (WAVETONE version)

Soft inharmonic bells that keep ringing.

- **Sound:**
  - FM TONE with an inharmonic ratio (around 1 : 3.5) and a medium modulation index that decays to a lower level.
  - Amp: fast attack, slow decay to about 40 % sustain, release 4 s, so the voices are still sounding when the next chord comes.
- **Sends:** reverb 50 %, delay 30 % (dotted 1/8), chorus 15 %.
- **DigiGlide:** VCNT 4 · BASS off · CHRD **Sus2** · GLID 1/4 · PATH **Snap** · TIME Together · ORDR Together · MOVE none · DRFT 3 / VIB 0 · SPRD 100.
- **Play it:** chords every 2 steps. Snap makes the bells bend quickly into each new chord and then ring.

### 7. TEMPLE GLASS

Resonant, hollow, ritual.

- **Sound:**
  - WAVETONE, a soft wave plus noise.
  - **COMB-** filter tracking the note, with high feedback for a hollow, bowl-like tone.
  - Amp attack 0.5 s, release 5 s.
- **Sends:** reverb 70 %, delay 15 %, chorus 0.
- **DigiGlide:** VCNT 4 · BASS root · CHRD **Open** · GLID 2 bars · PATH **Scale steps** · TIME Together · ORDR Together · MOVE none · DRFT 2 / VIB 0 · SPRD 90.
- **Play it:** in a minor or phrygian scale. Each voice walks through the scale's notes on the way, like bells being struck in turn.

### 8. CHIME FIELD (WAVETONE version)

Shimmering, scattered, a wind-chime cloud.

- **Sound:**
  - FM TONE, bright, with a high ratio and a short modulation decay for the strike.
  - Amp sustain about 30 %, release 3 s.
- **Sends:** reverb 60 %, delay 35 % (dotted 1/4), chorus 20 %.
- **DigiGlide:** VCNT 5 · BASS off · CHRD **Cluster** · GLID 1 bar · PATH Ease · TIME **Loose** · ORDR **Random** / STAG 1 · MOVE **Scatter** · DRFT 6 / VIB 2 · SPRD 127.
- **Play it:** a slow loop of two chords. Clusters, random order and Scatter make it feel like chimes in the wind.

## Drones and textures

### 9. IRON DRONE (WAVETONE version)

Heavy, low, slowly turning.

- **Sound:**
  - SWARMER low in register, detune low, slightly driven (overdrive on).
  - LOWPASS 4 at about 400 Hz, moderate resonance.
  - Amp attack 3 s, release 8 s.
- **Sends:** reverb 45 %, delay 0, chorus 0.
- **DigiGlide:** VCNT 4 · BASS root+sub · CHRD **Fifths** · GLID **16 bars** · PATH Smooth · TIME **By distance** · ORDR Together · MOVE **EVOL** (always: p-lock on every chord step) · DRFT 5 / VIB 0 · SPRD 60.
- **Play it:** one trig every 16 bars. Each one sends the voices wandering to nearby scale notes, never quite repeating.

### 10. DUST CHOIR

Breathy, vocal, like an old recording of a choir.

- **Sound:**
  - WAVETONE, a vocal or formant-ish table, ±10 cents, plus noise at about 20 %.
  - EQUALIZER peak around 1 kHz (the "ah"), and a little sample-rate reduction for age.
  - Amp attack 1.5 s, release 4 s.
- **Sends:** reverb 55 %, delay 15 %, chorus 40 %.
- **DigiGlide:** VCNT 4 · BASS off · CHRD Seventh · GLID 2 bars · PATH **Wobble** · TIME Together · ORDR Together · MOVE none · DRFT 14 / VIB 6 · SPRD 80.
- **Play it:** a minor ii, V, i. Wobble plus heavy drift makes the voices sound like singers finding the note.

### 11. STATIC BLOOM

Pitched noise, ghostly.

- **Sound:**
  - WAVETONE with the oscillators low and **noise high** (most of the sound).
  - **COMB+** tracking the note with high feedback, so the noise becomes pitched and the comb's pitch glides with the voices.
  - Amp attack 2 s, release 6 s.
- **Sends:** reverb 70 %, delay 20 %, chorus 0.
- **DigiGlide:** VCNT 5 · BASS off · CHRD Ninth · GLID 4 bars · PATH Ease · TIME Together · ORDR Together · MOVE **Bloom** · DRFT 4 / VIB 0 · SPRD 120.
- **Play it:** one Bloom chord every 4 bars. The pitched hiss gathers on one note and fans out.
- **Check:** confirm the comb filter actually tracks the glided pitch. If it doesn't, note it and use a resonant MULTIMODE band-pass instead.

### 12. FOG LIGHTS

Muffled, opening slowly, as if seen through fog.

- **Sound:**
  - WAVETONE, a warm table, ±8 cents.
  - LOWPASS 4 at about 300 Hz with a slow LFO on cutoff (8 bars, medium depth), so the sound opens and closes on its own.
  - Amp attack 1 s, release 4 s.
- **Sends:** reverb 60 %, delay 25 %, chorus 20 %.
- **DigiGlide:** VCNT 5 · BASS root · CHRD Seventh · GLID 2 bars · PATH **Late** · TIME Together · ORDR Together · MOVE none · DRFT 8 / VIB 3 · SPRD 90.
- **Play it:** Late holds each chord, then slides at the end of the glide, like lights appearing.

## Keys and plucks

### 13. ELECTRIC DUSK (WAVETONE version)

Mellow electric piano, with jazzy slides between voicings.

- **Sound:**
  - FM TONE, an electric-piano style: ratio 1 : 1 carrier, a high-ratio tine with a short decay.
  - Amp: medium decay to about 50 % sustain, release 1.5 s.
- **Sends:** reverb 30 %, delay 15 %, chorus 40 % (classic EP chorus).
- **DigiGlide:** VCNT 4 · BASS root · CHRD Seventh · GLID **1/8** · PATH **Snap** · TIME **Bass leads** · ORDR Together · MOVE none · DRFT 3 / VIB 0 · SPRD 60.
- **Play it:** ii, V, I with chords every 4 steps and long notes. Short Snap glides sound like a pianist sliding into voicings.

### 14. MUTED STRINGS

A small, intimate string section.

- **Sound:**
  - WAVETONE, saw-like, ±7 cents.
  - LOWPASS 4 at about 2 kHz.
  - Amp attack 0.4 s, release 1.5 s.
  - A slow LFO on pitch at a very small depth for bow movement.
- **Sends:** reverb 45 %, delay 0, chorus 25 %.
- **DigiGlide:** VCNT 4 · BASS root · CHRD Triad · GLID 1/2 · PATH **Semitones** · TIME Together · ORDR Together · MOVE none · DRFT 6 / VIB 5 · SPRD 70.
- **Play it:** chromatic voice slides, like players shifting position. Good for film-cue changes, for example i to bVI.

### 15. KALIMBA DRIFT (WAVETONE version)

Plucked, woody, ringing.

- **Sound:**
  - FM TONE with a woody ratio (around 1 : 4) and a fast modulation decay for the pluck.
  - Amp: fast decay to about 25 % sustain, release 3 s.
- **Sends:** reverb 40 %, delay 40 % (dotted 1/8, ping-pong feel), chorus 0.
- **DigiGlide:** VCNT 4 · BASS off · CHRD Ninth · GLID 1/4 · PATH **Bounce** · TIME Together · ORDR **Low first** / STAG 0.5 · MOVE none · DRFT 4 / VIB 0 · SPRD 100.
- **Play it:** chords every 2 steps. Bounce overshoots and settles, and the low-first stagger makes it roll like a thumb piano.

## Bass

### 16. GLIDE BASS

A round bass that slides between roots and fifths.

- **Sound:**
  - WAVETONE, saw plus sub, little detune.
  - LOWPASS 4 at about 600 Hz with medium resonance and a short filter envelope for punch.
  - Amp: fast attack, full sustain, release 0.3 s.
- **Sends:** reverb 5 %, delay 0, chorus 0.
- **DigiGlide:** VCNT **3** · BASS **root+sub** · CHRD **Fifths** · GLID **1/16** · PATH **Snap** · TIME Together · ORDR Together · MOVE none · DRFT 0 / VIB 0 · SPRD 0.
- **Play it:** on its own track under a pad, with the same DEG p-locks as the pad. Fast slides between roots, mono and centred.

## Bright and leads

### 17. SUNBEAM (WAVETONE version)

Bright, rising, hopeful.

- **Sound:**
  - SWARMER, bright, detune medium-high.
  - MULTIMODE low-pass at about 5 kHz.
  - Amp attack 0.6 s, release 3 s.
- **Sends:** reverb 50 %, delay 30 % (dotted 1/4), chorus 10 %.
- **DigiGlide:** VCNT 5 · BASS root · CHRD Sus2 · GLID 1 bar · PATH Ease · TIME Together · ORDR **Low first** / STAG **2** · MOVE **Cascade up** · DRFT 6 / VIB 2 · SPRD 110.
- **Play it:** IV to I at the end of a phrase. The voices rise one after another, bass first.

### 18. BROKEN RADIO

Lo-fi, detuned, nostalgic.

- **Sound:**
  - WAVETONE, a soft square-ish table.
  - Sample-rate reduction medium plus overdrive light.
  - Band-limited with MULTIMODE band-pass around 1.2 kHz (the radio speaker).
  - Amp attack 0.5 s, release 2 s.
- **Sends:** reverb 30 %, delay 35 % (dark, high feedback), chorus 30 %.
- **DigiGlide:** VCNT 4 · BASS off · CHRD Seventh · GLID 1 bar · PATH **Wobble** · TIME **Loose** · ORDR Together · MOVE none · DRFT **30** / VIB 8 · SPRD 50.
- **Play it:** an old-song progression, I, vi, IV, V. Heavy drift and loose timing sound like a warped tape on a bad radio.

### 19. AURORA (WAVETONE version)

Huge, wide, the showpiece. Six voices.

- **Sound:**
  - SWARMER, detune high.
  - LOWPASS 4 at about 2 kHz; the filter envelope opens over 3 s.
  - Amp attack 2 s, release 6 s.
- **Sends:** reverb 70 %, delay 25 %, chorus 20 %.
- **DigiGlide:** VCNT **6** · BASS root+sub · CHRD **Lydian** · GLID 4 bars · PATH **Swell** · TIME Bass lags · ORDR Together · MOVE **Spiral** · DRFT 8 / VIB 4 · SPRD **127**.
- **Play it:** two chords, 8 bars each, with Spiral p-locked on the second. Voices swing through octaves into the new chord.

### 20. ALMOST STILL (WAVETONE version)

Barely moving, meditative. For long, quiet pieces.

- **Sound:**
  - FM TONE, very low modulation (nearly a sine choir), ratio 1 : 2.
  - LOWPASS 4 at about 1.2 kHz.
  - Amp attack 4 s, release 10 s.
- **Sends:** reverb 65 %, delay 10 %, chorus 25 %.
- **DigiGlide:** VCNT 5 · BASS root · CHRD Seventh · GLID 30 s · PATH Smooth · TIME **By distance** · ORDR Together · MOVE **EVOL** (on every other chord trig) · DRFT 5 / VIB 2 · SPRD 80.
- **Play it:** one trig every 8 bars at a slow tempo, alternating a real chord with EVOL. Harmony drifts and returns.

---

## Exact values (filled in by the local Claude session)

One dial-in table per sound, in the Digitone's own page and parameter names and values:

| Sound | Page | Parameter | Value |
| --- | --- | --- | --- |
| 1 GLASSHOUSE | | | |

## Building them (instructions for the local Claude session)

1. **Use the real parameter names and ranges** from `dn2setup.py`'s parameter dump. Never guess value scales. Machines, filters, overdrive, sample-rate reduction and LFO destinations must exist as named; if one doesn't (for example comb filters tracking the note, or SCRB as an LFO destination), pick the nearest alternative and note it.
2. **Build each sound in the emulator** with its DigiGlide values, and save it.
3. **Match the targets by rendering** a held chord in the SHARC emulator:
   - cutoff within about 15 % of the target Hz;
   - attack and release within about 10 %;
   - loudness across all 20 within 1 dB.
4. **Check that every sound glides:** with the sound's own GLID, voices are still sounding at the next chord trig in its "Play it" pattern. Render it and confirm the pitch traces glide rather than retrigger.
5. **Render a demo WAV per sound** using its "Play it" suggestion (C minor or C major as fits, 90 BPM unless noted), with MOVE p-locked where listed. **Stop so I can listen** before finalising. Expect a round of tweaks.
6. **Delivery:** say which works (a Transfer-compatible sound file or SysEx dump, factory sounds in the patcher, or by hand), and always fill in the exact-values tables.
7. Save the results, update this file and commit. No em dashes.
