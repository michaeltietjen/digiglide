# GLIDE: answers to the spec's four open questions

Date: 2026-11-09 · OS 1.11 (sha256 2af43e65…72e0) · all results from the emulators, not yet from the unit.
Scripts: `~/glide/experiments/`.

## 1. How many voices can one track hold, and how does stock stealing behave when a chord needs 4?

- The DSP renders **16 voices**, shared by all tracks. Each track has a VOICE config (VOICE menu: VOICES = DYN or a
  reserved count, VOICE = REUSE / STEAL, UNISON, V.AMNT). Default: every track DYN, reserve 0, free pool 16.
- **DYN (stock default):** a track's notes land on any free voice; consecutive notes of one track are spread over the pool
  (track 1 used voices 0, 4, 8, 14), and voices are taken from other tracks as needed. A 4-voice chord would compete
  with every other track (`q1_reserve.py`).
- **Reserved:** setting track 1's VOICES to 4 through the stock setter `0x40029094(cfg, track, n)` (clamps to the free pool,
  writes, notifies) gives track 1 voices **0–3 exclusively**; all other tracks then stay on 4–15 (`q1_reserve.py`).
  Writing the config byte without the setter does nothing: the allocator only rebuilds on the change notification.
- Voice config: `cfg = 0x40030af8(0x4003e41a(0x4018a97a()))`, per-track 5-byte records at `vtable[40](cfg) + 5t`
  (+1 reserved count, +2 low 7 bits unison amount); free pool getter `0x40028ffc(cfg)`.
- **Decision:** the GLIDE track reserves 4 voices through the stock setter. GLIDE drives exactly those voices; stock never
  hands them to another track, so no stealing between GLIDE and the rest of the kit.

## 2. Can the glide ride on existing per-voice pitch in the ColdFire→DSP frame, or does it need SHARC code?

**It rides on the frame. No SHARC code.** The per-voice note word (frame +0x02+2v, `note << 8`) is read by the DSP every
block, fractional byte included, and a change without a note-on bends the sounding voice without retriggering the
envelope (`q2_note_word.py`, WAVETONE, one held voice):

| segment | word sent | measured (MIDI) | control |
|---|---|---|---|
| hold | 60 | 60.08 | 60.08 |
| fine | 60 + 0x80 | 60.59 | 60.04 |
| jump | 67 | 67.04 | 60.17 |
| ramp 67→69 per block | 67.25 … 68.75 | 67.32 / 67.87 / 68.27 / 68.83 | ~60.2 |

Same RMS in both renders: no new attack. Resolution is 1/256 semitone (~0.4 cent).
So **M3 is ColdFire only**: the slide is a per-block update of the note words of the GLIDE voices.

Side finding: `0x8000dda0[voice]` is a per-voice pitch word (0x3C00-centred, clamped 0..127 semitones), written by
`0x40025ce2` for every voice of a given sound. The reference note calling it the voice→track map is wrong for 1.11.

## 3. Which machine slot and parameter page can GLIDE take without breaking project files saved on stock OS?

- Machine types are 0..4 (FM TONE, WAVETONE, FM DRUM, SWARMER, MIDI). A sound load clamps the machine byte
  (`0x400dd2ae`: kept only if machine + 1 < 6) and every per-type accessor is bounded `type <= 4`.
- Sound value slots: 101 per sound, all used (0 / 65 / 100 are holes); every stock value / lock / LFO routine bounds
  `slot <= 100`. Stored sounds have no free bytes except dnfw LFO4's reserved lane.
- Option A: **new machine type 5 (spec as written).** On the DSP it plays as FM TONE (GLIDE sends machine 0 for its
  voices). On stock OS the load clamp turns it into a plain machine, so a GLIDE project degrades to "FM TONE without the
  chord brain" instead of failing. Cost: re-enter every `type <= 4` accessor and the MACHINE menu (digikit's
  `machinepatch.py` lists the pattern for DT2) plus a side table for the 6 params.
- Option B: **GLIDE as a mode on an FM TONE track** (a GLIDE on/off + the 6 params on a new page, in a side table keyed
  by track, saved with the project). No machine-type plumbing; stock OS ignores the side table, the track loads as its
  plain FM TONE sound.
- Both options need the 6 parameters outside the 101 slots (new param records past the table, own lock records): that is
  M4's main work and the same either way.
- **Recommendation: B for M4** (smaller, keeps the spec's "pitch brain on the stock synth"); A can follow if a MACHINE-menu
  entry matters. M1–M3 do not depend on it: they use a build-time GLIDE track and constants.

## 4. Is there free DSP cycle budget for per-voice slides at full polyphony?

- After Q2 the DSP does no new work: stock renders all 16 voices' engines and filters every block whether they sound or
  not, and the slide is only a different number in an existing word. **Extra DSP load: 0.**
- The cost moves to the ColdFire audio ISR (~0.67 ms period, stock ~64 % busy while playing; mod code ~4x stock's
  cycles per instruction from DDR). GLIDE per block: 4 voices × (curve step + one halfword store) + per-trig voice leading
  (≤ 24 permutations, on trig blocks only). Plan: keep slide state small, per-trig work bounded, and measure the ISR in the
  emulator each milestone; on the unit, read the DSP's own cycle word for the A/B.
