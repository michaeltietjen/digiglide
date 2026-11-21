# GLIDE build log

Workspace: `~/dn2-workspace` (images in `build/`), sources in `~/glide/mod`, tests in `~/glide/mod/tests`.
Nothing here has been flashed. Stock recovery image: `~/glide/stock-backup/Digitone_II_OS1.11.syx` (read-only copy,
sha256 2af43e65…72e0).

## Setup (M0), 2026-11-09
- Toolchain: binutils 2.42 + GCC 13.3 for m68k-linux-gnu built from source into `~/dn2-workspace/m68k`. The Xcode CLT
  ship a stale `usr/include/c++/v1` (3 files) that hides the SDK's libc++ headers: C++ builds need
  `-nostdinc++ -isystem $SDK/usr/include/c++/v1` (used for GCC and python-rtmidi). Reinstalling the CLT would fix it.
- digikit pinned to `42a226e9` (branch `skill-pin`, the last commit before it dropped the Python emulator the skill
  uses), skill patch applied, patched Unicorn built (all compat cases pass, fractional EMAC correct).
- dnfw at HEAD. `.venv-fast` -> `.venv` (digikit's own patched Unicorn already fixes EMAC).
- Examples: double_time OK (16ths: stock 4, mod 8); track_trim OK (ratio 0.5000 / 1.0000), hwrules 0 violations vs stock.

## GLIDE_1 (M1), sha256 4fb8aaab…7ed6
- Hook: `jsr glide_stub` over `move.l 0x402876f8,%d0` at 0x40025e82 (audio ISR, before the frame goes to the DSP);
  the stub replays the move last (the `bnes` after it reads its flags).
- Track 1 with VOICES = 4 owns DSP voices 0-3; GLIDE copies the source voice's record to all chord voices and writes
  the chord tones. Code 2.8 KB, flash 220,067 B free.
- test_m1: OK (stock 1 voice note 60; GLIDE voices 0-2 = 48 52 55 in one block, same record; other tracks unchanged).

## GLIDE_2 (M2), sha256 463d3232…8f02
- + `glide_seq` test table (stand-in for p-locks until M4). ColdFire has no scale-8 index: copy by byte offset.
- Host tests (tests/test_voicelead.c): OK.
- test_m2: OK (C maj -> A min: no retrigger, C and E hold, G 55 -> 57 over 745 blocks = 1/4 at 120 BPM, monotonic).

## GLIDE_3 (M3), sha256 6f464287…3ab2
- Slides keep ticking after the trig ends (a release no longer stops a slide part-way).
- M3 render (tests/render_progression.py M3 --glid 1bar --drft 0): 25/25 checks. One attack; every slide lands on a chord
  tone at GLID (1 bar = 3000 blocks), monotonic, 75 % of the way at half time (ease-out); DSP voice pitch matches the
  note words within 0.07 semitone. Stock reference = the same chords on tracks 1-3 (stock per-trig NOT2..NOT4 storage
  not found yet: the TRIG-page defaults and p-locks on slots 9..12 did not add chord notes).
- Renders: ~/glide/renders/M3/ (hybrid: OS note / mask / velocity words + the same explicit FM TONE pad patch).

## M0 wrap-up (spec rev 3), 2026-11-10
- Note numbering (`experiments/c3_number.py`, screenshots in `experiments/out/c3/`): the TRIG page shows MIDI 48 as C4 and
  60 as C5, so Elektron C3 = MIDI 36. The stock TRIG page default note is 60 (C5).
- Within-block pitch (`experiments/q2b_block_smoothing.py`): no ramp. A new note word becomes a phase-continuous hard step
  11 to 12 samples into the next block. Pitch reaches the DSP as a 1500 Hz staircase; the 5-cent rule is decided at M5.

## M1 reference model (spec rev 3), 2026-11-10
- `model/digiglide.py`: Brickglide's chord building, amb_voicelead, amb_shape / amb_path_at, amb_glide_all (Moves,
  timings, orders, Scale-steps vias), amb_sub_follow, amb_evolve, drift and vibrato, per Digitone block, seeded random.
- `model/test_vs_brickglide.py`: OK, 26,067 cases against Brickglide's own functions (chord tones for every
  KEY x SCL x DEG x CHRD, voice leading, all shapes and paths, glide plans for every non-random MOVE x PATH x TIME x ORDR).
- `model/test_model.py`: OK (repeatable, no jumps, GLID 0, fresh after release, sub, Moves, EVOL, SCRB, VIB, DRFT).
- Renders (`model/render_m1.py`, saw pad `model/padsynth.py`): `renders/M1/` (WAVs not in git, regenerate).
- Deviations from Brickglide (Digitone or spec): seeded random; GLID in bars; STAG in 1/16 steps; VCNT includes the
  sub; no >2-octave re-render jump; MOVE ignored on a fresh trig; EVOL leaves the sub following the bass.

## M2 C port (spec rev 3), 2026-11-10
- `mod/core/dg_core.c/.h`: the M1 model in 32-bit fixed point (pitch Q16 cents, shapes Q29, time Q16 blocks for
  glides that fit 65536 blocks, else Q12; sine and Smooth lookup tables from `gen_tables.py`). Same seeded random
  streams as the model.
- **Toolchain finding:** this GCC's libgcc is built for the 68020. Its 64-bit helpers (`__muldi3`, `__divdi3`,
  `__udivdi3`) use 64-bit `mulu.l` / `divu.l` and `bfffo`, which the ColdFire does not have; the emulator's generic
  m68k core runs them anyway, so only the hardware would fault. The core uses its own 32-bit multiply / divide
  helpers and `build_selftest.py` fails the build if any `__` runtime helper is linked. Struct assignment links
  `memcpy` (absent): copy field by field.
- Model pinned for exact matching: tie tolerances in voice leading / ORDR sorting / Scale steps, Semitones rounds
  half up, integer drift interval, integer SCRB smoothing (see the model's docstring).
- `mod/core/test_equiv.py`: OK. 1,000 seeded random progressions (every value of every parameter, 60..240 BPM,
  trig notes, gate-offs, SCRB moves), 13.0 M blocks x 6 voices: same voices, gates and notes in every block,
  largest pitch difference 0.0035 cent (limit 0.1); 5,000-seed sweep: 0 failures, largest 0.008 cent.
- `mod/core/test_selftest_emu.py`: the ColdFire build (`DG_SELFTEST.syx`, no hooks, not for flashing) run in the
  emulated OS gives bit-identical output to the host build on 4 progressions (24,000 blocks).
- Cost on the ColdFire (emulator instruction counts): a block with 6 voices median 616, max 1,556 instructions; a trig
  block 14,600 to 23,300 (planning: mostly the software 64-bit divisions). Decide in M3 where planning runs (audio ISR
  vs the sequencer's step handler) against the ISR budget.
- Core size: about 7 KB code + 16 KB tables.

## DIGIGLIDE_1 (M3, spec rev 3), sha256 d836e091...
- `mod/digiglide.c` + `hooks_dg.S` (same frame hook 0x40025e82 as GLIDE) + the M2 core. Track 1 reserves 6 voices;
  a trig calls dg_trig (seed step = playhead 0x446483d0 + track, live tempo word), the source's release dg_gate_off,
  every block dg_block -> note words; voices attack only on a gate's rising edge; each started voice gets the source's
  record / velocity / curve / level / machine / track plus its SPRD pan (record slot 89). Parameters from the
  dg_seq test table (M4 replaces it), pattern seed 0. `build_dg.py` fails on any linked runtime helper.
- `tests/test_m3_dg.py`: OK. 13 fresh trigs (KEY C, major, DEG I, BASS root, every CHRD): 5 voices attack in one
  block, bass C2 (MIDI 36), chord tones stacked above; all 11,278 blocks x 6 voices match the M1 model within 0.195
  cent (note word resolution); attacks exactly at the model's gate edges; records and pans as specified.
- `experiments/m3_wavetone_slots.py`: OK. The WAVETONE DSP engine ignores sound slots 50..64: renders with those
  slots filled at random are bit-identical (a still note and one with a note-word glide and moving wave / filter).
- Faster planning: 64/32 division from 16-bit digits on the CPU's own divide (fuzzed: 20 M cases exact), voice
  leading stops once candidates are farther than the best. Trig blocks 3,300 to 6,200 instructions (were 14,600 to
  23,300); outputs unchanged (test_equiv, emulator self-test).
- ISR cost (`tests/isr_cost_dg.py`, emulator instructions): stock mean 43,729 / max 57,179; DigiGlide mean 45,401 /
  max 59,636. Added: median 1,916 per block, at most 4,853 on a trig block. Our code runs from DDR at roughly 4x
  stock's cycles per instruction, so the trig block is the one to watch on hardware (UI lag, dropped trigs). Planning
  stays in the ISR for now; fallbacks if the unit shows trouble: core state in SRAM, or planning one block after the
  note block.

## DIGIGLIDE_2 (M4a, spec rev 3): parameters from the sound and p-locks
- A track is DigiGlide when its sound is WAVETONE with 0x4447 ('DG') in slot 100 (a slot no machine uses): the switch
  travels with the sound. The 16 parameters are sound slots 50..65 in Params order, knob << 8. Slot 65 is the third
  hole (0 / 65 / 100); 93/94 (portamento) stay stock.
- Found (`experiments/m4_readpath.py`): for slots WAVETONE does not use, the frame carries p-locks (in the voice's
  record at the note-on block, unramped) but not the sound's own values. So a trig reads each parameter where the
  sequencer would: the playing pattern's lock table (`*0x42C5A9A0 + 97872`: index byte at +20640 + 101 t + slot,
  258-byte records, s16 per step, -1 = none), else the live sound (`*0x800052A0 + 52 + 1163 t`, slot at +0x14 + 2 s).
  The held-trig lock recorder for tests: `0x4004f8fe(ctx, step, slot, value)`. SCRB is read every block.
- Without the switch the hook returns before touching the frame.
- `tests/test_m4a.py`: OK. Steps 1/17/33/49/53 with p-locked DEG I/VI/IV/V/I (GLID 0 on 33): each trig read exactly
  its own locks and the sound's other values; the hook saw the placed steps; 14,994 blocks x 6 voices match the M1
  model within 0.196 cent; GLID 0 changes in one block; step 53 interrupts a glide 218 cents in with no jump (1.17
  cents largest step); the same sound without the switch plays stock.

## DIGIGLIDE_12 (M4b, spec rev 3): the two pages
- Slots (final): parameters in 50..64 and SCRB in 93 (PTIM); the DigiGlide switch is 0x4447 in 94 (PORT). These are
  the slots a sound SAVE / LOAD keeps on WAVETONE (converters 0x400dd6a6 / 0x400dd1ea and their maps 0x401fcf20 /
  0x401fd0b0: 50..64 <-> stored 58..72, 93 <-> 100, 94 <-> 99). Slot 65 is saved into stored word 0 but loaded back
  into slot 0 (load zeroes every slot first), and slot 100 is not saved: both were wrong homes.
- Parameter records 321..336 in the relocated table (dnfw.patch.paramtable: 56 bases, 55 bounds +16), generated at
  build time from the stock image into build/digiglide_gen/ptable.S (never committed: Elektron data). Ranges per
  parameter, our long / short names and formatters, NRPN / CC none, ids from the table's free gaps, mask 0.
- Pages: WAVETONE's count and descriptor readers (0x400c24d2 / 0x400c24f2) answer 5 pages on a DigiGlide track;
  HARMONY / MOTION descriptors with refcount -1 std::strings. Stock knob rows draw values with their own pictures and
  texts (MOD's glyphs, MULT's "BPM n"), so the two pages are drawn by dg_grid (hook 0x40018214, as Waverider M8.1):
  value text from our formatter over the label, inverted when locked, then the stock level meter and page dots. The
  companion-row accessor 0x400c2418 still answers stock rows for our entries (encoders need a row).
- **Found the hard way:** 0x4018a97a is not a getter. It constructs the app singleton (451,596 bytes) when
  0x446478d0 is still 0, and the page readers run while the app is being built at boot: calling it from a page hook
  froze the UI on some builds (boot-timing dependent: DIGIGLIDE_5/6/8 froze, 4/7 did not). dg_ui_active reads
  0x446478d0 directly and answers "not DigiGlide" until it is set.
- `tests/test_m4b_ui.py`: OK. [SYN] cycles 5 pages; knob A turns KEY (slot 50) and stops at B; GRID RECORDING + held
  trig 1 + knob C p-locks DEG on step 1 (inverted cell), the sound unchanged, and the hook's read (dg_test_read) gives
  the locked DEG with KEY from the sound; a plain WAVETONE track keeps 3 pages. Screenshots: renders/M4/.
  Emulator limitation: the emulated panel sometimes drops a key while its input queue is busy (the test retries the
  lock gesture), and after the GRID RECORDING gestures PLAY does not start again in that session (no key held, play
  state 0); playback of locks is covered by test_m4a.py through 0x4004f8fe, the function the held-trig turn calls.
- M3 and M4a tests re-run on this build (CHRD per step now a p-lock): OK.

## DIGIGLIDE_13 (M4, spec rev 3): VCNT is the switch, the shortcut, BRICKGLIDE PAD (sha256 45d6c2f2...)
- Owner's decision (2026-11-10): VCNT (slot 54) is the switch, stored as a code: 0 OFF (default), 1..4 = 3..6 voices.
  Only the exact codes 0x0100..0x0400 are on: stock sounds are not guaranteed 0 there (slot 54 is FM TONE's AB
  Attack; the 1.11 demo's WAVETONE tracks 1, 3, 4, 8 hold 0x4000: experiments/m4_slot54.py), and they read OFF.
  Out-of-range values in the other parameters read as defaults. The slot-94 magic is gone.
- OFF = stock: a trig with VCNT OFF (sound or p-lock) plays a stock note; a sounding chord releases; DigiGlide gives a
  voice back the moment stock starts a note on it; with no DigiGlide voice left the frame is untouched. Switching OFF
  while sounding releases at the next block, released voices keep their pitch while they ring.
- Shortcut [FUNC] + push encoder E: flips the active track's VCNT between OFF and its last count (5 if none), message
  "DIGIGLIDE ON (n VOICES)" / "DIGIGLIDE OFF" for 1.3 s. The ISR watches the key-held bitmap 0x445a1e30 and sets the
  screen's "redraw due" byte (+32); the toggle and the message happen in the UI task at the end of the screen pass
  (hook 0x4011d398: a2 = screen, d3 = canvas). Combo survey on stock 1.11: every [FUNC] + page key, [PAGE], [PRESET],
  [+]/[-] and [ARP] is used ([ARP] silently flips sound byte +351); [FUNC] + any knob push changes no state on any
  page (experiments/m4_combos*.py, m4_ch6.py, m4_funcany_mem.py). Panel group 6: bit 4 = [ARP], 5 = [+], 6 = NOTE
  EDIT, 7 = [-]; bits 0..3 do nothing on this unit (firmware names VOICE / LEVEL etc. are not wired here).
- Pages now show on every WAVETONE track (VCNT must be reachable while OFF); FM TONE keeps its stock page count.
- tests/test_m4c_switch.py: OK. A: VCNT OFF everywhere (demo project): 3,004 frames byte-identical to stock and DSP
  renders bit-identical. B: shortcut on (5), off, restores 4 voices, messages (renders/M4/switch_*.png). C: survives
  stock's sound save / load converters (the [FUNC]+[YES] / [FUNC]+[NO] gesture reloaded no sound value in the
  emulator, stock's own amp volume included: experiments/m4_reload.py). D: the combo's keys alone are stock (state and
  screen identical to stock). E: OFF mid-chord: note-offs, nothing stuck, no pitch jump (0.004 semitone); next trig
  stock; ON applies from the next trig. F: a p-lock to OFF plays a stock note, the chord releases.
- tests/make_brickglide_pad.py: BRICKGLIDE PAD built, saved with stock's converter (sounds/BRICKGLIDE_PAD.stored.bin,
  values in sounds/BRICKGLIDE_PAD.json), loaded into an FM TONE track: WAVETONE, its name, VCNT 5, and its trig plays
  the DigiGlide chord. Putting the file on the unit directly (sound pool / SysEx) is not done.
- test_m3_dg, test_m4a, test_m4b_ui re-run on this build: OK.

## M5 (spec rev 3): DSP render, on DIGIGLIDE_13 / OS 1.11
- tests/render_m5.py: OK. Progression i VI iv v (C minor, 90 BPM, GLID 1 bar): 4 trigs; DSP pitch within 0.728 cent of
  the M1 model (words vs model 0.195 + DSP vs words 0.532, 76,800 voice-blocks); largest step 0.391 cent; two renders
  bit-identical; all 10 MOVEs (on step 33, the second chord: step 9 has no trig with a chord every 2 bars) 0.391;
  paths at most 1.562 (Snap, Bounce), Semitones / Scale steps by design; VCNT OFF frames and render identical to stock.
- The pitch check: the first version read the per-voice DSP buffer with an 8-sample sine fit and failed by hundreds of
  semitones. The WAVETONE "sine" (WAV1 120) carries 3rd and 5th harmonics (FFT 523 / 1570 / 2619 Hz). Now each voice
  is rendered alone and its fundamental demodulated with the phase its sent words predict (40 ms window; windows that
  touch the voice's own note-on / off left out). The frame -> model alignment is offset 0 (0.195 cent, quantization).
- VCNT OFF first failed on 3 frames: after STOP the OS puts back the demo project's 81 BPM over the harness's 90; it
  does so on stock too, at a UI-timing-dependent frame. That word is left out of the last 4 (post-STOP) frames.
- WAVs (one shared gain, -1 dBFS peak): renders/M5/progression, stock, move_*, path_*, paths_all, midglide.

## OS 1.12 port: DN2_1.12_DIGIGLIDE_1 (sha256 d113b72c...)
- Only section 3 differs from 1.11 (+4,096 B); sections 2, 7, 8 identical. port/addrmap.py maps 1.11 -> 1.12
  (port/addr_1.12.json, 98 addresses); mod/osver.py selects the OS (DG_OS, default 1.12); mod/port_os.py sets
  dnfw / cfmod constants (area 0x4030C980, loader cave 0x4028DFAE, table 0x401F83D8, companion 0x4243425C) and builds
  the runtime loader from a copy of dnfw csrc with DNFW_AREA changed (in the build directory: dnfw's code).
- Build: 56 bases, 55 bounds found on 1.12 (the scanners' own counts), dnfw inspect all ok, flash 1,905,163 of
  2,097,152 B. DG_OS=1.11 rebuild of the same sources is byte-identical to DIGIGLIDE_13.
- Emulator on 1.12 (no DigiGlide change): digikit devices/digitone-ii.toml gained a 1.12 entry (local); the audio
  ISR's DMA buffers moved 0x8000 up (bound 0x4E6E0900 -> 0x4E6E8900), so cfkit's faked DMA position reads the ISR's
  own cmpi operand; cfkit installed Python EMAC hooks from data/emac_rows_1.11.txt, which on 1.12 landed at
  0x400DB3C2 / 0x400DB3C6 (plain instructions there) and corrupted the ISR's stack: stock 1.12 sent empty frames.
  data/emac_rows_1.12.txt (from a 1.12 disassembly) fixed it: stock 1.12 plays the demo as 1.11 does.
- Tests on DN2_1.12_DIGIGLIDE_1: test_m3_dg OK; test_m4a OK; test_m4b_ui OK; test_m4c_switch OK (A..F);
  make_brickglide_pad OK (stored sound byte-identical to the 1.11 one); render_m5 progression (pitch 0.728 cent,
  step 0.391, bit-identical), VCNT OFF, move_bloom, move_evol OK; test_m55_regression OK (demo project loads
  byte-identical to stock 1.12; voices 6..15 and FX byte-identical, render bit-identical, while DigiGlide plays).
- Progression frames 1.12 vs 1.11 build: all 31,954 identical except the post-STOP tempo word; stock 1.12 vs stock
  1.11 frames identical.
- test_m4b on 1.12 first failed: dg_ui_page is set when a page is drawn, and on 1.12 the redraw lands later after a
  tap, so syn_page() stopped one page late (knob A then edited MOTION's GLID). dgkit.drawn_page() waits for the
  redraw; the page-cycle check is by order (a late tap shows the same page twice). Same on 1.11 with the wait.
- test_m55_regression: trigs every half bar (steps 1 9 17 25) so 4 land in its 6,000 blocks.

## M6 first flash (DN2_1.12_DIGIGLIDE_1), owner's report 2026-11-10, and the repro
- Unit: A stock notes sound underneath (chord mode on: the stock chord too); B glides only sometimes; C every key
  the same chord, no transpose heard.
- Cause, reproduced (experiments/m6_repro.py, 8 trigs C..C on track 1, VCNT 5): every test gave track 1 VOICES = 6
  (reserved voices 0..5) and soloed it; the unit had VOICES at its default. Default: stock rotates the track's notes
  over the whole 16-voice pool and dg_tx only looks at voices 0..5. Reserved: 8 of 8 trigs DigiGlide. Default, other
  tracks silent: 6 of 8, trigs 7 and 8 on voices 6 and 7 as plain stock notes. Default, demo playing: 3 of 8, and
  other tracks' notes take voices 0..5 back (a chord with 2 voices). Chord mode: one voice is the source, the
  chord's other voices are "stock's" and sound. Trig-note transpose does work on a taken trig (D -> bass 38).
- Reservation on other tracks (experiments/m6_reserve_other.py, stock 1.12): reserved blocks are packed from voice
  0 in track order (track 5 VOICES 6 -> voices 0..5, track 9 VOICES 4 -> 6..9), the rest is the shared pool.

## DN2_1.12_DIGIGLIDE_2 (rev 4): DigiGlide owns the track's notes, keys choose the chord, latch (sha256 defe7d6f...)
- Owner's design change after the first flash (GLIDE_SPEC.md, "Notes and chords"). Not flashed yet.
- Hook (mod/digiglide.c): every note-on of a WAVETONE track with VCNT on is swallowed (16 voices scanned, by the
  voice -> track word) and becomes a chord event; its note-off is swallowed with it. DigiGlide's voices are the
  track's reserved block, read from the kit's voice config (5 B a track, +1 = VOICES; blocks packed from voice 0 in
  track order). Events: one note -> dg_degree_of (nearest degree of KEY + SCL, octave from MIDI 60 + KEY); several
  note-ons in one block -> their pitch classes, lowest = bass; notes within 60 blocks (40 ms) join the event. DEG
  p-locked overrides, the sound's DEG is added. The trig note no longer transposes KEY.
- Core / model: dg_trig takes a chord word (pitch classes, root, octave); the voice leader's reference pitches move
  by the change of octave; the bass register moves with the octave. test_equiv: 1,000 progressions with random
  octaves and chords, 0.0067 cent; dg_degree_of = the model for 128 notes x 12 keys x 4 scales.
- VOICES: the UI task (end of the screen pass) raises a VCNT-on track's VOICES to VCNT with stock's setter
  0x40029094 ("VOICES SET TO n" / "NO FREE VOICES") and restores the old value when VCNT goes OFF. First try failed:
  the config getter returns its pointer in d0 and a C pointer-returning call reads a0.
- LATCH: slot 94, on = exactly 0x0100 (the demo sounds hold 0x3f00 there: off), [FUNC] + push encoder H. Live notes
  latch; sequenced ones (sequencer playing and the step has a trig: the pattern's step words are 2 bytes a step, bit
  0 of the low byte) follow their length; same chord again releases; [STOP] (key or play flag 0x42C5A994 falling)
  releases. Two bugs found by test_m3 on the way: a 4-byte step stride, and "non-zero = on".
- tests/test_m6_notes.py: OK (VOICES default and the demo playing: no stock note-on of the track, 8 of 8 trigs chord
  events, seven keys seven chords = the model, glides without re-attack; track 4 behind a reserved block; DEG lock;
  live keys: one key and three keys at once against stock's own notes, same pitch classes, bass = the key, no
  offset; latch, same key again, [STOP], LATCH off).
- Re-run on this build: test_m3_dg OK, test_m4a OK, test_m4b_ui OK, test_m4c_switch OK (VCNT OFF identical to stock),
  test_m55_regression OK, make_brickglide_pad OK (the pad now has LATCH on). Test changes: m55 lets both OSes settle
  before comparing the app object (a 127-byte block differs for a moment after start-up) and compares the frames
  played, not the 4 after [STOP]; m4b gives the emulator's slow knob more tries; the pad test finds track 6's voices
  by track word.
- ISR cost (isr_cost_dg.py): stock mean 43,754 / max 57,179 instructions; DigiGlide mean 45,800 / max 61,397
  (+2,046 mean; +6,614 on a trig block).
- Not done: chord mode is not read from the OS (the notes decide); one DigiGlide track at a time; a key played by
  hand on a step that has a trig, while the sequencer plays, counts as sequenced.

## DN2_1.12_DIGIGLIDE_4 (rev 5, Orchid-style chords; sha256 be79ee8d...)
- Owner's redesign after two flashes (GLIDE_SPEC.md, "Chords"): one key = one chord, the played note is the root.
  SCL / DEG / CHRD removed. Listening demos from the model first (model/render_rev5.py, renders/rev5), approved.
- Model and core: chord_for (TYPE / EXT / KEY, diatonic when the root is in KEY's scale, locks win), the chord voices
  placed over the root by VOIC (spacing, 64 = close position) and POS (two octaves each way) and led from where they
  are but never from more than a fifth off their place; a mono bass voice on the root (Off / Follow / Solo, 0..2
  octaves down); revoice and tail flags. test_equiv: 6,000 progressions, 0.015 cent; dg_chord_for = the model for
  every root, type, ext, key and lock. Two float ties pinned in the model (a delay just elapsed, a glide just ended).
- Found on the way: every stock sound holds 0x2700 (39) in slot 93, where SCRB lived, so on the unit glides stopped
  a third of the way on any sound not touched; the tests always wrote 127. Now: GLID in slot 93 (PTIM turns it), SCRB
  in slot 58, and the first time VCNT is on for a sound whose HOLD slot (94) is neither 0 nor 0x0100 (stock: 0x3f00)
  every parameter gets its default. Slots: TYPE 50 EXT 51 KEY 52 VOIC 53 VCNT 54 POS 55 BASS 56 MOVE 57 SCRB 58
  PATH 59 TIME 60 ORDR 61 STAG 62 DRFT 63 VIB 64 GLID 93 HOLD 94, PLAY 65 (not saved, one value).
- Hook: the lowest note of an event is the root; GLID 0 retriggers; VOIC / POS turned under a chord revoice it
  (at most every 30 blocks); the release tail covers the bass voice too; the sounding chord's name (dg_name) is drawn
  over the title on the three pages (CHORD, MOTION, SETUP: entry 0 marks an empty cell, as stock pages do).
  "VOICES n OF m" when other tracks hold voices. The status box ([FUNC] + push G) shows the note stock sent (K) and
  the root played (R).
- tests/test_rev5.py: A defaults and VOICES; B twelve keys with the demo playing (no stock note, 12 events, model
  notes, names, glides); C KEY C major triads and sevenths, a TYPE lock; D live key = stock's note (C6 72 = root 72),
  three keys one chord; E HOLD; F short notes glide from the ringing chord (5.5 cent at an attack), fresh without
  release; G VOIC / POS turns; H BASS OFF / SOLO; I VCNT OFF frames = stock. test_rev5_ui.py OK (six pages,
  TYPE knob, "C MIN7" on the page, both shortcuts). test_m55_regression OK. make_brickglide_pad OK (TYPE MIN, EXT 7,
  HOLD on). The rev 3 / 4 tests (test_m3_dg, test_m4a, test_m4b_ui, test_m4c_switch, test_m6_notes, render_m5) are
  written for the old parameters and are not ported.
- Next builds (owner): 2 arp through the stock arpeggiator; 3 Strum / Slop / Harp / Pattern; 4 the key layout.

## DN2_1.12_DIGIGLIDE_5 (sha256 e69c46da...): fixes from the unit with build 4
- Unit, build 4 (read over USB with the Screenshot RPC): the chord side works ("the chords are great"), the name
  display works. Problems seen on the screen: stock chord mode on with BASS OCT -2 (the lowest note, two octaves
  down, was taken as the root: "super low"); a preset (AMBIENTOUS) holds 0 in slot 94, so it looked set up and got
  no defaults: SCRB 64 (glides stopped halfway: "drifting tone-wise"), DRFT / VIB 0; KEY G + EXT MAJ7 gave minor
  chords with a literal major seventh; BASS / VCNT / TYPE turned under a chord did nothing until the next key.
- Fixes: HOLD is stored as 0x0200 (off) / 0x0300 (on), and any other value in slot 94 means "never a DigiGlide
  sound": defaults are written (sounds from build 4 get them once too). With KEY set and the root in the scale, MAJ7
  gives the key's own seventh, as 7 does. The root of an event is its lowest note that is not more than an octave
  under the next one (a detached chord-mode bass is skipped; not tested in the emulator: its keys in one panel
  message span less than an octave). TYPE, EXT, KEY, VOIC, POS, BASS and VCNT turned under a sounding chord revoice it
  at once (checked every 30 blocks). [FUNC] + push encoder F writes the defaults. "B MIN MAJ7" has its space.
- Tests on this build: test_rev5 30 checks OK (A now with 0 in HOLD's slot and 64 in SCRB's, as the preset), its new
  check "TYPE turned under a held chord" was written too strictly and failed; the behaviour is right (C MAJ -> C MIN
  -> C MIN7 -> BASS OFF, each glided, no attack: scratch run) and the check is corrected; test_rev5_ui OK,
  test_m55_regression OK, make_brickglide_pad OK.

## Arp investigation (phase 2, stock 1.12 in the emulator, 2026-11-11)
- [FUNC] + [ARP] sets sound byte +351 from 0 to 1; [ARP] alone opens "ARPEGGIATOR > TRACK n" (MODE, SPEED, RANGE,
  ...). Encoder A there writes the same byte +351 (MODE: 0 off, 1 TRUE, ...), B writes +374, F +354, G +358.
- With MODE on and one key held in keyboard mode, stock sends a note-on every step (278 blocks = 1/16 at 81 BPM)
  and a note-off 148 blocks later, each on the next voice, all with the key's note (RANGE 1): 12 steps in 2 s.
  So each arp step reaches DigiGlide's hook as an ordinary note-on of the track: the clock for a DigiGlide arp.
- Still to find: the MODE list and its numbers, where SPEED / RANGE / length live, the note stream with RANGE > 1.

## DN2_1.12_DIGIGLIDE_7 (sha256 59c9fbf7...): defaults and the silence on new patches
- Owner: defaults GLID 1/8, VOIC 127 (SCRB 127 as before). (Build 6 = build 5 + these defaults; superseded.)
- Unit, build 4, status box read over USB: K = R on every key (71 / 71, 69 / 69, 77 / 77): the note stock sends is
  the root DigiGlide plays, on hardware. Every key a chord event, "held | gate open | HOLD" throughout, while the
  owner heard nothing on new patches until "sometimes it starts working". Cause: with HOLD on a held chord is only
  glided, never struck again, so after a preset load (voices silenced) or on a sound that fades while held, new keys
  glide silence; the same key twice releases it and the next key attacks.
- Fixes: a separate key press (no other key or trig of the track still down) strikes the chord again and still
  glides; only overlapping keys glide without an attack. A preset load on the DigiGlide track (its name / machine
  hash changes, checked every 32 blocks) drops the held chord: note-offs, engine reset.
- Tests on this build: test_rev5_ui OK, test_m55_regression OK, make_brickglide_pad OK. test_rev5: 28 checks OK, 2
  failed, both the test's own: "preset loaded" looked for the next key's attack before the emulator had delivered
  the key (scratch run: note-offs 7 blocks after the name change, the next key attacks a fresh chord); "TYPE turned"
  ran after VOIC 120 / POS +36, where no voice holds the third. Both corrected; the full test re-run is in the log
  below when it finishes.

## DN2_1.12_DIGIGLIDE_8: recording on the unit, the voice pool (2026-11-11)
- Unit, build 7: recorded trigs played nothing or glitchy, live playing not heard while recording, then "none of
  the other machines are working on other tracks". Status box: track 13 at base voice 12 with 4 voices, every trig
  taken, chords named, gate open.
- Ruled out: a second note-on on a gated voice without a note-off (the re-strike of build 7). SHARC render, RMS per
  100 ms identical for held / second note-on / off then on / off and on in one block (experiments/restrike_audio.py).
- Cause of the silent tracks: all 16 voices reserved (12 by tracks 1..12, 4 by DigiGlide). Stock gives a track
  without reserved voices only the unreserved ones: with 12 reserved every other track shares voices 12..15, with 16
  reserved they get no note-on at all (experiments/pool_full.py). The 12 most likely came from VCNT switched on by
  accident on several tracks: the reservation was only put back in the same power session, and it is saved with the
  kit.
- Fixes: "OTHER TRACKS: NO VOICES" when a reservation fills the pool; VCNT off hands back voices that an earlier
  session left (on -> off, or the first look after power-on at a former DigiGlide sound holding 3..6): "VOICES
  FREED: TRACK n". VOICES set by hand later in the session on such a sound stays; a sound that never was a DigiGlide
  sound is never touched. Not known: whether the unit has loaded the kit's voices before the first screen pass
  (the emulator session starts later; the test clears the "looked at" flags instead).
- Also in this build (from the recording work): sequenced or hand-played is decided by the TRIG keys (a hand-played
  note arrives while one is down), not by "the playing step has a trig", which failed on micro-timed live-recorded
  trigs (some latched, some not); the sequencer stopping releases a held chord only after 300 blocks of "not
  playing"; the same-chord release needs a separate hand-played key.
- Open: the DigiGlide track's own silent / glitchy playback on the unit is not reproduced in the emulator; to be
  rechecked on the unit with the pool freed, then on build 8.

## DN2_1.12_DIGIGLIDE_9 (sha256 0fcf4fbd...): HOLD playback silent on slow-attack sounds (2026-11-11)
- Unit, build 8: other tracks sound again once the reserved voices were freed (later silence there was a mute).
  Track 13: "I only hear it when it stops". Status box over USB while playing: every trig taken, a trig about every
  2 s, L111 (held, gate open, HOLD on) although the sound's HOLD was off: live recording had stored HOLD as a lock
  on the steps. Grid trigs with HOLD off played; the same trigs with HOLD on were silent.
- Cause, reproduced end to end (experiments/hold_audio.py: the OS's own frames, sound records included, through the
  SHARC emulator, AMP ATK 100): build 7's "strike the held chord again" is a note-on on gated voices; the amp
  envelope restarts from silence (RMS 0.049 -> 0.010, 1.5 s to recover). With a slower attack and a trig every 2 s
  the chord never gets loud. With a fast attack nothing is heard of it (why experiments/restrike_audio.py passed).
- Fix: the held chord is struck again only on a sound that does not sustain (AMP SUS, slot 84, under 16); a
  sustaining sound glides with no new attack, hand-played or sequenced (build 4's behaviour). Render on build 9:
  no drop at the second trig.
- Not in this build: AMP RSET (slot 92) off removes the restart from silence (hold_audio.py RSET=0 / 1), which
  would also smooth HOLD-off playback of slow-attack sounds (a new chord after a gap attacks the same voices).
  Clearing it in the frame's voice records (all chord voices, or all but the source voice) made the emulator's
  live recording with HOLD on record no trigs (test_rev5_record C; not understood); writing the sound's slot does
  not reach the frame. Workaround: AMP RSET off on the sound, by hand.
- Ruled out on the way: reservation order (experiments/reserve_order.py: blocks are packed from voice 0 in track
  order whatever the order they were made in, also after earlier ones are freed); stock changing the source voice's
  velocity / level after its note ends (experiments/hold_fields.py).
- Tests on build 9: test_rev5 34 OK, test_rev5_ui OK, test_rev5_record 9 OK, test_m55_regression OK,
  test_voices_pool 10 OK, make_brickglide_pad OK. test_rev5: the overlap and preset-load checks moved to their own
  sessions (late in a long session the emulator drops key presses; builds 7 and 8 behave the same there).

## Build 10 (2026-11-12): strike per trig by sound; grid recording tested

- Unit, build 9 (HOLD on, recorded trigs): "trigs aren't sounding on record", confirmed as "no attack per trig". Build 9
  struck no sustaining sound, so recorded trigs under a held chord only glided.
- Rule now, for a separate key or trig arriving on a held chord: strike it again (and glide) when AMP ATK is under 32
  or AMP SUS is under 16; a slow pad (ATK 32 and up, sustaining) only glides. Overlapping keys never attack.
- Grid recording (`experiments/rec_grid.py`, case D in `test_rev5_record.py`): with DigiGlide on, [RECORD] and three
  trig keys store the same 27 pattern bytes as stock, sound nothing while placing, and play back as 5-voice chords.
- Suites on image 10: test_rev5 35 OK, test_rev5_ui OK, test_rev5_record 13 OK, test_m55_regression OK,
  test_voices_pool 10 OK, make_brickglide_pad OK. sha256 d81dadcc...8c509c4a. Not flashed at the time of writing.
- Not done: `experiments/trig_bytes.py` (finding retrig / probability / condition in the trig defaults) gave unstable
  results in one long emulator session and was stopped; retrigs, trig conditions, MIDI out, mute and sound locks
  under DigiGlide stay untested.

## Reading other Digitone II work (2026-11-12, no build)

Sources: dnfw docs (local clone), Modwerk's Digitone II page and OS 1.12 research note, toonst's elekloader fork
(`mods/core-dn2` 0.3), irpina/digitables (Digitone mk1), Overtone (elektronmods id 59).

- Nobody has published a Digitone II mod that plays chords or takes over a track's notes. Overtone is the only
  finished DN2 firmware; it ships as a binary patcher with no source, and it is a whole image, so it and DigiGlide
  cannot be on a unit together.
- Trig page records (dnfw `lock-id-table.md`, `lfo4-feasibility.md`): NOTE VEL LEN uTM COND AMP.T FLT.T LFO.T PROB
  FILL, then Retrig RTRG VFAD LEN RATE. Where a step stores retrig and condition is not established by anyone; the
  working route in an emulator is the panel (TRIG page open, grid recording, trig held, encoder turned:
  dnfw `emu-sequencer-play.md`). Guess, untested: byte +2 of the trig defaults (7 on stock) is the three
  envelope / LFO trig flags.
- AMP.T is a per-trig "fire the amp envelope" switch. It does not solve the pad problem: a struck pad needs the
  envelope to carry on from its level (what AMP RSET off does), not to be skipped.
- dnfw: in grid recording a held trig key plays a preview note. DigiGlide will take that note as a key: with HOLD
  on the preview chord would stay. Not tested (case D presses the keys briefly and sees no note-on). Test next.
- Frame masks (dnfw `drive-load-command.md`): +0x26 / +0x28 always equal +0x22 / +0x24; a note-off can stay in the
  mask for two frames. Matches what the hook assumes.
- digitables (mk1) adds chord notes by copying the trig's note event into the firmware's own event pool, so stock
  allocates the voice and runs the envelope. The DN2 equivalent (posting notes to the sequencer's event pool
  instead of taking voices in the audio interrupt) is not mapped by anyone. It would remove voice reservation and
  the starved-tracks problem; it is a redesign, parked.
- core-dn2 0.3 has key, encoder, draw and tick events, key LEDs and an input bridge at OS 1.12 addresses (UI events
  run on a unit, the rest emulator only). Useful for the parked live function keys, and the route if DigiGlide is
  ever to coexist with other mods.
- Held trig key in grid recording (`experiments/rec_preview.py`, image 10, 2026-11-12): a trig key held 2 s, twice
  (placing a trig, then on the placed trig), on stock, DigiGlide HOLD off and HOLD on. No note-on or note-off in any
  frame in all three, no DigiGlide event, the trig stays. The preview note dnfw describes (OS 1.11) does not appear
  in this emulator on 1.12, on stock either, so the stuck-chord risk is not reproduced and not ruled out: check on
  the unit (grid recording, HOLD on, hold a trig key: nothing should keep ringing).

## Build 11 (2026-11-12): retrig note-off fix, release on mute; trig features tested

- Found in the emulator (`experiments/trig_var.py`, one session per case): probability is byte +16 of the track's
  trig defaults; retrig is a flag in the step's own word (0x0381 -> 0x8383); byte +3 of the defaults must keep bit 7
  (clear: no notes, meaning not known). On a retrigged step stock ends the first note twice: at the retrig (note-off
  and the next note-on in one block) and again at the note's own length.
- Bug (image 10): that second note-off was let through to the DSP on a voice DigiGlide plays and silenced one voice
  of the chord, under HOLD too. Fixed: a stock note-off on a voice DigiGlide controls is swallowed.
- Track mute (`experiments/mute_var.py`): stock mutes upstream, a muted track sends no notes, so DigiGlide plays
  nothing. The mute mask is the u16 at 0x8000521A (bit t = track t + 1; found on 1.12 by memory diff, confirmed on
  tracks 2, 6, 9, 13; the 1.11 address is assumed, not checked). New rule: a chord HOLD keeps is released when its
  track is muted (nothing else would end it).
- Probability 0 / 50 / 100 %: as stock in every mode (upstream of the hook).
- New suite `test_rev5_trigs.py` (6 checks). Image 11: test_rev5 35 OK, test_rev5_ui OK, test_rev5_record 13 OK,
  test_rev5_trigs 6 OK, test_m55_regression OK, test_voices_pool 10 OK, make_brickglide_pad OK.
  sha256 90de1b3a...51539769. Not flashed.
- Still untested: trig conditions (stored per step, not found), MIDI out, sound locks.
- `test_off_is_stock.py` (new, 6 checks, image 11): with no DigiGlide sound switched on, every byte of 3004 frames is
  stock's for the demo project and for a DigiGlide sound with VCNT OFF plus trigs; keys by hand on the switched-off
  track give the same note-ons and note-offs as stock; no chord event in any case. Emulator only: the unit check
  (power cycle, reserved voices handed back) is still owed.

## Build 12 (2026-11-12): the amp envelope carries on at a strike

- Every voice DigiGlide plays has AMP RSET off in its frame record (slot 92, written each block after the sound is
  cloned). An attack on a voice that still sounds rises from its level instead of restarting from silence. The
  sound's own AMP RSET is not used on a DigiGlide track.
- A separate key or trig on a held chord always strikes it again (and it glides); the AMP ATK / AMP SUS rule of
  builds 10 and 11 is gone. Overlapping keys still never attack.
- The earlier attempt at this "broke live recording" in the emulator. It does not: test_rev5_record passes (3 keys
  record 3 trigs, HOLD on and off). That failure was the emulator dropping keys in a long session.
- Audio (`experiments/hold_audio.py`, AMP ATK 90): HOLD on, a second trig strikes at block 1877: RMS 0.042, 0.043,
  0.048, 0.052 (image 11, no strike: 0.039, 0.046, 0.046, 0.041). No drop to silence. HOLD off, second chord after a
  gap: 0.0040 against 0.0031 on image 11.
- Preflight (dnfw v0.50 `safety.py` rules, against stock 1.12): images 8, 11 and 12 pass; product, version 1.12,
  build 0062 and sections 2, 4, 5, 7, 8 identical to stock; 187,949 bytes spare in the USB upgrade buffer.
- Suites on image 12: test_rev5 35 OK, test_rev5_ui 8 OK, test_rev5_record 14 OK, test_rev5_trigs 6 OK,
  test_off_is_stock 6 OK, test_m55_regression 7 OK, test_voices_pool 10 OK, make_brickglide_pad 4 OK.
  sha256 497df42d...32b90ec6.

## Build 13 (2026-11-12): build label, read-only USB probe, preflight in every build

No change to how DigiGlide plays: the three "adopt now" items from the reading of dnfw v0.50.

- Build label: switching the status box on ([FUNC] + push encoder G) shows "DIGIGLIDE BUILD 13" for the usual message
  time. The number comes from the image's file name (`DG_BUILD`), so the screen names the file that was flashed. The
  OS screen still says 1.12.
- USB probe (`mod/probe.S`, from dnfw's `csrc/usbprobe/probe.S`, licence header kept): HELLO and PEEK only, no STATS,
  no command that writes. Hook in the SysEx router before the Elektron header compare (1.11 0x4012169A, 1.12
  0x4012197A, bytes 47f9 + header address checked). Answers on USB only, device byte 0x7D only. PEEK reads RAM
  0x40000000..0x48000000 and SRAM 0x80000000..0x80010000, 1 to 1024 bytes; anything else is refused. Tag "DG 13".
- Host side on the Mac: `tools/dgprobe.py` (system python3 with mido): `ports`, `hello`, `peek ADDR [LEN]`,
  `sym NAME [LEN]` (symbols of the build that answers), `selftest`. dnfw's own `tools/dn2probe.py` is Windows only.
  Not run against a unit: the unit has image 9, which has no probe.
- Preflight (`mod/preflight.py`): dnfw v0.50's safety rules against the stock file of the OS being built. Run at the
  end of `build_dg.py`; an image that fails is renamed `.syx.FAILED` and the build exits 1.
- `test_probe.py` (new, 13 checks): requests handed to the firmware's own SysEx router in the emulator, reply read
  from the probe's send buffer. HELLO, PEEK of DG and of the SRAM frame, refusals (peripheral register, past the end
  of RAM, too long), unknown commands, no answer from DIN / other device byte / empty body, and the build label.
  Not covered: the bytes actually leaving on USB (the send call is stock's SYSEX_SEND, port 2), so the probe needs
  one flash to confirm on hardware.
- Unit report (2026-11-12, image on the unit not confirmed): "can't hear the glides when recording". Not reproduced
  in the emulator. `experiments/rec_glide.py` (three keys about a beat apart, GLID 3, images 9 and 13, HOLD on and
  off): the voices' pitch words move over the same blocks and the same distances with [RECORD] + [PLAY] running as
  with the sequencer stopped. Difference between the images: with HOLD on, image 9 sends no new attack on the second
  and third key, image 13 strikes each one. Open: on the unit GLID was 1/16 (about 125 ms at 120 BPM), short enough
  for an attack to cover it; to be checked on the unit with a longer GLID, and with the probe once 13 is flashed.
- Suites on image 13: test_probe 13 OK, test_rev5 35 OK (run alone; two earlier runs timed out at 31 and 33 checks, none failed,
  with other emulator jobs running), test_rev5_ui 8 OK, test_rev5_record 14 OK, test_rev5_trigs 6 OK, test_off_is_stock 6 OK,
  test_m55_regression 7 OK, test_voices_pool 10 OK, make_brickglide_pad 4 OK.
  sha256 043562c7...9bead57b. Not flashed (the unit has image 12).
- The two October paramtable fixes in dnfw, checked on 1.12: both cmpa.l bounds are raised (0x4006EBA0, 0x40107850;
  55 bounds, 56 bases as on 1.11) and the 8 bytes after record 320 are carried. One compare against 319 at
  0x4006EF0A is outside the lists; it sits before the known switch case and was not disassembled.
- Unit, image 12 (2026-11-12, 45 s of read-only screenshots, `experiments/rec_glide2.py` for the emulator side):
  every key became a chord event (E 30 to 37, T equal, S unchanged). Two releases of a held chord seen, both by
  design (the same key twice; [STOP]). The owner's report turned out to be "could not hear the keys while recording,
  heard them once the pattern played them back", not reproduced, and it "worked better" on the next try. Suspects:
  step or grid recording mode ("Step Rec: Standard" was on screen), keyboard mode off. Open.
- Unit, image 12: previewing FM TONE and SWARMER sounds in the sound browser on a DigiGlide track plays DigiGlide
  chords with those sounds (owner's observation; the track is still WAVETONE during a preview and each chord voice
  copies the arriving note's sound record, machine included). Loading the sound ends it: DigiGlide is WAVETONE only
  because slots 50..64 are free only there. "DigiGlide on every machine" needs its parameters outside the machine's
  slots (a per-track side table, saved with the project); parked under the scope freeze, owner wants it.
- Image 13 flashed by the owner (2026-11-12). The probe answers on the unit: `tools/dgprobe.py hello` gives
  "DG 13", protocol 3; `sym dg_probe_tag`, `sym dg_ui 18`, `sym DG 48` and `peek 0x8000521A 2` (mute mask) return
  data; a peek of a peripheral register (0xFC045640) is refused. The USB send path, the one part the emulator test
  did not cover, works on hardware. Still to check on the unit: the "DIGIGLIDE BUILD 13" message, and the core items.

## Build 14 (2026-11-12): DigiGlide stays on over a sound load

- Unit, image 13, 60 s recorded over the probe (`tools/dgwatch.py`, about 65 samples a second): at 22 s another
  sound arrived on track 13 (nearly every slot changed; DigiGlide's slots held stock values, VCNT off). The held
  chord was dropped and ten of the pattern's trigs played as single stock notes, until DigiGlide was on again at
  37 s. This is the "nothing at first, then it plays" the owner reported; it follows a sound change, not recording.
  Not explained: what switched it on again at 37 s, and why the owner heard nothing rather than single notes.
- Fix (owner: "Yes, keep it on"): `keep_tick` in the UI task remembers each track's 18 DigiGlide slot values while
  VCNT is on. When one track's sound changes (name or machine hash) and the new sound has VCNT off, the values are
  written into it and the screen says "DIGIGLIDE KEPT ON". A sound with its own DigiGlide settings keeps them. When
  more than one track changes within 150 blocks, or the playing pattern pointer changes, nothing is written (a kit
  or pattern change). The voice reservation is left alone while a load is being decided. A track whose DigiGlide
  is off is never written.
- Known limits: a pattern change in which only this one track's sound differs, and the pattern pointer does not
  change, would be taken for a sound load (not tested on the unit: whether the pointer changes with the pattern is
  unknown). A non-WAVETONE sound still ends DigiGlide ("DIGIGLIDE: WAVETONE ONLY").
- `test_keep.py` (new, 7 checks): the load imitated in memory (new name, stock slot values); carried over, message,
  chords on the next trigs, own settings kept, two tracks together untouched, DigiGlide off untouched byte for byte.
- Suites on image 14: test_keep 7 OK, test_probe 13 OK, test_rev5 35 OK, test_rev5_ui 8 OK, test_rev5_record 14 OK,
  test_rev5_trigs 6 OK, test_off_is_stock 6 OK, test_m55_regression 7 OK, test_voices_pool 10 OK,
  make_brickglide_pad 4 OK. Preflight passes. sha256 f218010a...67d29194. Not flashed (the unit has image 13).

## Every machine: research for the next milestone (2026-11-12, no firmware change)

- Owner's plan: DigiGlide settings belong to the track (saved with the kit / project), any machine's sound can be
  loaded onto a DigiGlide track. Next milestone after build 13 is checked on the unit.
- Emulator, `experiments/any_machine.py`: DigiGlide's own frames (WAVETONE track) with each chord voice's sound
  record and machine word replaced by a stock sound's of another machine, rendered in the SHARC emulator; this is
  what the unit does while a sound is previewed on a DigiGlide track.
  - FM TONE (demo track 2's sound): 5 voices per trig, the second chord glides over 711 blocks (the same plan as
    on WAVETONE), HOLD off releases and the level decays to 0.0001; HOLD on sustains 0.02 to 0.04 where the stock
    single note decays to 0.0004. Peak 0.33, all samples finite.
  - FM DRUM (demo track 15's sound): the same voices and glide; HOLD off decays; HOLD on the level rises over two
    seconds (0.02 to 0.08), a held drum patch, not looked at further. Finite.
  - SWARMER: NOT reproduced. The demo project has no SWARMER track, the emulator's MACHINE menu did not select it,
    and writing the machine byte did not change the frame's machine word (the two "SWARMER" runs are WAVETONE).
    The only evidence is the owner's preview on the unit.
- Storage precedents read. dnfw's lfo4 stores in the stored sound (a lane of 8 words per preset, zeroed by a stock
  re-save): per sound, not per track, does not fit. Digiwerk's compressor (naturarum/dn2-cfw, GPL-2.0, notes
  T6.0 and T6.3, written against OS 1.12; its code addresses match our 1.12 image) stores in the kit: fits.
  - Stored kit record: 0x2a00 bytes, 129 per project, working image 0x405ce96c + 0xae0200 + n * 0x2a00, magic
    0xbeefbace at +0, version 4, 0xbacef00c at +0x28ab.
  - FX record spare words, kit +0x16ac + 0x60..0x97 (56 bytes): verified by Digiwerk as never written or read by
    stock; used by Digiwerk's compressor.
  - Kit padding +0x28af..+0x29ff (337 bytes): inferred unused (the kit serializer and loader skip it; other readers
    not excluded). 16 tracks x 18 parameters = 288 bytes fit unpacked.
  - Read on the unit over the probe: all 129 kit records have the magic, version 4, the tail marker, and both
    areas zero.
  - Stock 1.12 with such a project (Digiwerk's analysis, save paths not run): loads ignore the bytes; an in-place
    project save keeps them; Save Kit, the +Drive kit library and exports drop or garble them (hence a check word).
- Costs of the kit route: hooks on the kit serializer and loader; the pages no longer plain sound slots (own read
  and write path); p-locks of TYPE / EXT need lock ids or are given up; the WAVETONE checks removed.
- Image 14 flashed by the owner (2026-11-13). The probe reports "DG 14"; the message buffer reads "DIGIGLIDE BUILD
  14"; the carried-over counter (`dg_kept`) is 0, no sound load yet. Unit checks owed: a WAVETONE sound load keeps
  DigiGlide on; a pattern change leaves a plain track plain.

## Build 15 (2026-11-13): every synth machine, settings owned by the track

- Image `DN2_1.12_DIGIGLIDE_15.syx`, sha256 `9f712e5643b4779ed45bfb9e3651e54ca0ba92e8d2b778f44f7accb698c09a2c`,
  preflight PASS, built from the owner's stock 1.12. Design: GLIDE_SPEC.md, "Rev 6".
- What changed: the 18 settings are per track, 18 bytes each in the spare bytes of the kit's record in the working
  project ("DGK1" + 16 x 18 at record + 0x28af); FM TONE, WAVETONE, FM DRUM and SWARMER tracks all get the three
  pages after their own SYN pages; no machine menu entry; SETUP's lower row shows which of the 16 tracks are on.
  Locks made with images up to 14 still play on a WAVETONE track; a WAVETONE sound from those images switches its
  track on once when it arrives (its values are taken over into the track).
- Emulator, image 15, all pass (checks): test_every_machine 29, test_rev5 36, test_rev5_record 14, test_rev5_trigs 6,
  test_rev5_ui 8, test_machines_render 27 (WAVETONE, FM TONE, FM DRUM x HOLD off / on, SHARC renders finite, no
  clipping), test_voices_pool 10, test_m55_regression 7 (other tracks bit-identical), test_probe 13,
  test_off_is_stock 6 (OFF = stock's frames byte for byte), make_brickglide_pad 4.
- Two failures on the first pass were the tests, fixed and rerun:
  - test_off_is_stock B: the stock reference session wrote DigiGlide's old sound slots (50..64, 93, 94) into the
    sound while the image 15 session wrote the kit store, so the two sounds differed. The stock side now writes
    nothing (dgkit `set_sound`).
  - make_brickglide_pad: the emulator's first PLAY after [SYN] taps can stay silent on every track (seen in
    test_every_machine C too); the script plays again. It also used the test defaults (VOIC 127, GLID 1/8, the
    owner's defaults) for the pad; the pad's own VOIC 64 and GLID 1 bar are now explicit, and the saved sound is
    byte for byte the committed one.
- Recording on an FM TONE track (`DG_MACH=0 test_rev5_record.py`): with DigiGlide, 3 keys record 3 trigs (steps
  1, 5, 9), play back as chords, HOLD holds and [STOP] releases (11 checks pass). The 3 failing checks compare
  with the stock reference, which in the emulator recorded 1 of 3 keys on FM TONE: the reference is not usable
  there, so "as stock" is unverified on FM TONE.
- Unit, owner's report after flashing 15 (2026-11-13): "other than recording, swarm and fm seem to be working".
  SWARMER and FM TONE chords therefore work on hardware (SWARMER cannot be reached in the emulator). What fails
  about recording is not known yet: not reproduced in the emulator on WAVETONE or FM TONE. Open.
- Known limits of image 15:
  - No new p-locks from the panel for DigiGlide's parameters (the knobs' rows are unlockable). Old locks play on
    WAVETONE only.
  - Save Kit, kit copy, kit clear and the +Drive kit library do not carry, copy or clear the settings (stock
    serialises a kit without the spare bytes). What a kit reload does to them is not known.
  - SWARMER: untested in the emulator (the frame's machine word could not be made SWARMER); hardware report above.
  - Power cycle and project save / load: unverified on hardware (`tools/dgstore.py` lists the store, read-only).
  - FM DRUM: works, not a target (drum tracks). With HOLD on its level rises for about 2 s, then stays near rms
    0.10 (peak 0.36). Observation only.
  - `model/test_model.py` is stale since rev 5 (10 failures on the committed model, before and after): not run as
    a gate; test_equiv and the firmware suites are.

## Repository (2026-11-13)

- Private GitHub repository michaeltietjen/digiglide, started with a fresh history: one first commit of the files
  as they stood after build 15 and the GLID rule. Commit ids quoted above (fa022cb, 6173553 and others) are from
  the earlier local history, kept in `~/glide` as the branch `local-history` and not pushed.
- Audit before the push, over every path of the 45 earlier commits: no .syx, no extracted section, no
  `digiglide_gen/ptable.S`, no project dump. Kept by the owner's decision: `sounds/BRICKGLIDE_PAD.stored.bin` (our
  pad in Elektron's stored-sound format), the emulator and unit screenshots and the rendered WAVs under `renders/`.
  The build scripts hold 7 strings of 2 to 10 bytes, the original instructions at the hook sites, to check the
  stock file before patching.
- Licence AGPL-3.0-or-later (a built image contains dnfw's loader; `mod/probe.S` and `tools/dgprobe.py` derive
  from dnfw). LICENSE, NOTICE and README added.

## GLID is the whole change, and the recording report (2026-11-13, no image to flash yet)

- GLID rule (GLIDE_SPEC.md, "GLID is the whole change"): model and C core changed together. `test_equiv` 6,000
  progressions OK (largest difference 0.034 cent); `test_glid_fit` OK (9,000 cases: the last voice lands within one
  block of GLID, none later; GLID 1 bar at 90 and 120 BPM lands on the bar line; GLID 0 is a hard change; TIME
  Together, ORDR Together, no Move is block for block as before).
- Found on the way: with the new timing one progression in 1,000 differed between model and C. SCRB held a
  Converge on its meeting point, the voices were in unison, and ORDR's ranking (to 1/1024 cent) ordered them
  differently in fixed point. ORDR now ranks to the nearest cent in both.
- Demos: `model/render_glid_fit.py` (Bloom and Cascade up at GLID 1 bar, old and new). Old rule: the last voice
  landed after 5.0 s (Bloom) and 3.25 to 3.6 s (Cascade up); new: 2.0 s. Owner: "love it".
- Test image 94 (`build/proto`, the new core): ColdFire self-test equals the host build on 4 cases, 612
  instructions a block; test_rev5_trigs 6 and test_rev5_record 14 pass. test_rev5, test_every_machine and the
  interrupt cost run were still going when this was written.
- Recording, the owner's report on image 15: keys played during the first pass of a live recording (the first 16
  steps) may be silent; "not a game breaker but it's hard if doing something complex while recording".
  Not reproduced: in the emulator (image 15, WAVETONE, HOLD off and on) each of three keys sounds its 5-voice chord
  1 to 5 blocks after the press while recording, and `DG.last_note` follows the keys. (The pitch words at an attack
  are where the glide starts, the previous chord: that is not a wrong chord.) The recording test never checked
  sound during recording before this. Next: a `tools/dgwatch.py` capture from the unit while it happens.
- Test image 94, the rest: test_rev5 36 and test_every_machine 29 pass. `isr_cost_dg.py` did not run: it is
  stale since rev 5 (it still passes `deg` to the model's Params). The self-test's figures stand in for it: 612
  instructions a block for 6 voices, 5,345 in a trig block.
- Unit capture of a live recording take (`tools/dgwatch.py`, image 15, track 13, HOLD on, 64 steps, about 100 BPM;
  the first two captures were of an idle unit). First pass, 17.3 s to 26.9 s: every key fired a chord event
  (hand-played, `ev_seq` 0), gates open on all six voices (`was_on` 63), the chord names follow the keys (G MAJ,
  E MIN, G MAJ, B MIN, C MAJ, D MAJ, ...). Second pass: the recorded trigs fire the same chords (`ev_seq` 1). The
  records of voices 0 and 1 are the same in both passes but for the pan. So DigiGlide plays in the first pass as
  far as its own state shows; whether this take was silent is the owner's to say. dgwatch now refuses to
  overwrite a capture and records the play flag (0 stopped, 1 playing, 2 seen before a [STOP], probably paused),
  the playheads and the keys held. Captures are not committed (`notes/*.jsonl` ignored).

## Build 16 (2026-11-13): GLID is the whole change

- Image `DN2_1.12_DIGIGLIDE_16.syx`, sha256 `47c85c95f287e6b2bf362cf10351a88e809c1bc32f08d3a3259a44b80e429ae8`,
  preflight PASS, built from the owner's stock 1.12. The core of test image 94 (the GLID fit rule) under its build
  number. The stored format is build 15's. Given to the owner to flash; not flashed by me.
- Build fix: the probe's tag string ("DG 16") sat in `.text`, and the build's instruction check read " 16" as a
  68020 scaled index (`2031 3600`) and refused the image. The tag is now in `.rodata` (`mod/probe.S`). Any label
  whose second digit is 6 or 7 would have failed the same way.
- `build_dg.py` without `-o` takes the lowest free number, not the next one: it wrote image 3 (older images were
  deleted from the workspace). Removed; build 16 was made with `-o`. Pass `-o` for numbered builds.
- Suites on image 16 (emulator, digikit's venv Python): test_probe 13, test_rev5_trigs 6, test_rev5_record 14,
  test_off_is_stock 6, make_brickglide_pad 4, test_rev5 36, test_every_machine 29: all pass.
- Not in this build: p-locks from the panel (17), arp (18), and any fix for the fault below.
- Open fault (owner, image 15, a SWARMER track, HOLD on, 64-step pattern): chords played by hand are silent while
  the sequencer runs. With [PLAY] only they start after a full bar; while recording they stay silent in the first
  pass. With the sequencer stopped the same chords sound, HOLD on or off. One take with HOLD off and another sound
  sounded throughout. What the captures rule out: DigiGlide not firing (every key fires an event, six gates open),
  p-locks (`tools/dglocks.py`: no lanes on panel tracks 13 and 14; the tool is unchecked against a track with
  locks), and any difference in the frame's level, velocity or sampled voice records but pan. Not reproduced in
  the emulator (which cannot run SWARMER). Untested suspect: HOLD on at sequencer start. The owner chose to move
  on.
- `DG.track` counts from zero: the owner's DigiGlide track reads 13, which is panel track 14. Earlier entries
  that say "track 13" mean that value.
- New read-only tools: `tools/dglocks.py TRACK` (the p-lock lanes of a track in the playing pattern) and
  `tools/dgframe.py SECONDS OUT` (the whole 0xC00-byte frame with DG, the play flag and the playheads, about 25
  samples a second).
- Owner, jamming on image 15: "it's awesome using position to make melodies"; noted in GLIDE_SPEC.md with the
  planned Harp and Arp modes.

## Build 17, first measurement (2026-11-13): where p-locks can live

- Slots a machine leaves unused among the sound's 101 (stock parameter table, 320 records, read by group): FM TONE
  uses 25..64 but 34 and 49; WAVETONE 25..49; FM DRUM 25..54; SWARMER 25..32. LFOs 1..24, filter 66..79, amp
  80..92 (FX sends 86..88), portamento 93, 94, FX 95..99. No record on any machine uses slots 0, 65 or 100. So
  per-machine lanes would give 18 locks on SWARMER and 4 on FM TONE: not a design.
- The lock table (`experiments/b17_lanes.py`, image 16, emulator, FM TONE): the stock setter (0x4004F8FE in 1.11
  terms: ctx, step, slot, value) accepts every slot 0..100 on any machine and refuses 101 and up. A lane is 129
  words, -1 = no lock. One pool of 80 lanes per pattern for all 16 tracks; the 81st lock on a new (track, slot)
  is refused. The word at the table's head goes ffff -> 0000 with the first lock.
- What the DSP is sent (`experiments/b17_lanes_frame.py`, 1,504 frames against a run without the lock): a lock on
  slot 0 or slot 100 changes no frame word at all. A lock on slot 65 lands in the voice's record (frame +0x12a),
  as slot 70 (the control) lands at +0x134; whether the DSP reads word 65 is not known.
- So: two lanes that exist on every machine and never reach the DSP, slots 0 and 100, 15 bits each. Plan: pack
  the performance parameters into them, with "not locked" as one value of each field. Lane 0: POS (129) x TYPE (5)
  x EXT (9) = 5,805. Lane 100: VOIC (129) x GLID (14) x MOVE (11) = 19,866. Two lanes a DigiGlide track out of the
  pattern's 80. The locks images <= 14 made on WAVETONE (slots 50..64, 93, 94) stay honoured as now.
- Not measured yet: whether the setter takes any 15-bit value; the stock routine that clears a lock; what a
  machine change, a track copy and a pattern copy do to lanes 0 and 100; the stock "a trig is held" state and the
  held step; the inverted display.
- Owner's choice (2026-11-13): the six lockable parameters are POS, TYPE, EXT (lane 0) and VOIC, GLID, MOVE
  (lane 100).
- CORRECTED (see Build 17 below): an earlier entry here said that with the six rows left lockable stock "writes
  the value (POS 64 -> 100)" with a step held and never calls the lock setter, "so stock does not lock a row whose
  record is in the FX group". That was wrong. In that run (`experiments/b17_lockable_row.py`, test image 95) the
  knob change landed before the hold registered. With a step truly held stock does not write the value: it goes
  to its lock routines with the record's k as the slot.
- Looking for stock's "a step is held" state (`experiments/b17_held_state.py`): not in the app object (451,596
  bytes compared across idle, grid recording, trig 1 held, trig 5 held: nothing follows the keys). A compare of
  all working RAM (0x40300000..0x44700000) gives 680 bytes that follow the held trig, mostly draw buffers, not
  sorted yet, and no byte that follows grid recording on / off (the [RECORD] tap may not have landed in that run).
- Emulator note: a script must import dgkit before cfkit. dgkit's osver sets the 1.12 main image for the
  emulator's symbols; with cfkit first the panel keys go nowhere (no track select, [SYN] does not cycle).


## Build 17 (2026-11-13): p-locks made on the pages

- What it does: in GRID RECORDING, hold a trig and turn POS, TYPE, EXT, VOIC, GLID or MOVE: that step gets its own
  value (a p-lock), the track's value stays. While the step is held the page shows the step's values and a locked
  one is drawn inverted. Push the knob with the step held: a locked parameter is unlocked; an unlocked one is
  locked at the row's value. A lock on a step without a note trig is taken by the chord that is sounding when the
  playhead reaches the step.
- Storage: two stock lock lanes per DigiGlide track, sound slots 0 and 100 (no machine uses them, nothing of them
  reaches the DSP). Field 0 = not locked, else value + 1. Slot 0: POS + 129 * (TYPE + 5 * EXT). Slot 100: VOIC +
  129 * (GLID + 14 * MOVE). The setter takes any 15-bit value; value 0xFFFF writes "no lock".
- How stock locks (read from 1.12 and traced, `experiments/b17_held_knob_trace.py`). The held steps are a 128-bit
  set in an object behind the pointer at 0x446488C8 (+600). The knob handler 0x40067470 gets the knob's delta
  from the accelerator 0x4011364e, in 1/256 steps; with a step held it calls the page's method at vtable +0x9c
  (0x40065022), which runs 0x40064d08 for every held step: no lock yet = "set lock" (0x4004F8FE: ctx, step, slot,
  value) at the row's value; else "get lock" (0x4004EAA4), add the delta, "set lock". A knob push runs 0x40064dc6
  (lock at the row's value where there is none) and, if every held step had the lock, 0x400647d4, which ends in
  "remove lock" (0x4004F944: ctx, step, slot). The slot stock uses is the record's k: 70..87 for DigiGlide's
  records, which are the sound's filter envelope.
- So the six rows stay lockable (`DG_LOCK_ROWS` in `mod/ui/dg_ui.c`; the other rows keep the unlockable flag) and
  the three stock routines are hooked (`mod/ui/hooks_ui.S`, `dg_lock_set_hook`, `dg_lock_get_hook`,
  `dg_lock_clr_hook` in `mod/digiglide.c`). A call is DigiGlide's when the slot is one of the six rows', a
  DigiGlide page is on screen and the context is the active track's; then the lock goes to the packed lanes and
  nothing is filed under 70..87. Every other call is stock's, untouched. A lock holds whole steps, so the part of
  a step the knob has moved is kept for the lock last written and given back by the next "get lock".
- First try, removed: DigiGlide's own "knob pushed = unlock" in `dg_ui_sync`. It cleared the lock stock had just
  made (stock's push makes the lock first), which is why the lock seemed to stay at the starting value.
- Emulator limit: with a step held the emulated panel's knob never produces a delta (the accelerator returns 0,
  knob pushed or not), so the emulator alone never reaches the turn path. The test replaces the accelerator's
  result at 0x400675c8 with 0x100 (and 0x80 for the half-step check); everything after that is stock's code. The
  size of a real detent's delta is not measured: whole steps and half steps both work.
- Test (`mod/tests/test_b17_locks.py`): 20 checks pass. POS locked on step 1 and following
  the knob (67, lane word 68), half steps add up (67 -> 69), the track's POS unchanged, the page shows the lock
  (`renders/b17/chord_pos_locked_held.png`: the POS cell inverted), push removes it, push again locks 64, the page
  shows the track again after the key is let go, no lane under 70..87; locks written directly are read by their
  trigs at playback; the step without a trig is taken while the chord sounds; unlocking the last field of a word
  writes "no lock".
- Not tested: what a machine change, a track copy, a pattern copy and a trig removal do to lanes 0 and 100 (they
  are stock lanes, so stock's own routines are expected to carry and clear them); locks made while another
  track's page is on screen (not possible from the panel); the unit itself.
- Playback does not use the hooked routines (pattern with locks playing, CHORD on screen: 0 calls of "get lock",
  "set lock" and "remove lock"), so a DigiGlide lock is never read as a lock of slots 70..87.
- Image 17: `DN2_1.12_DIGIGLIDE_17.syx`, sha256
  `6acaed6dd94c76b3133627202dedcf13cb6168cb3cd587ff4987bc9fae198b04`, preflight PASS, the same bytes from a
  second build of the committed source. On it: test_b17_locks 20, test_rev5 36, test_every_machine 30 (its check
  "no row can be p-locked" rewritten: only the six rows, no row randomised), test_rev5_record 14, test_probe 13,
  test_rev5_trigs 6, test_off_is_stock 6, make_brickglide_pad 4: all pass. Not flashed by me; not yet on the unit.
- Owner flashed image 17 (2026-11-13): "seems to work". No detail yet on which locks were tried.

## Build 18, first reading (2026-11-13): the stock arpeggiator, to be fed DigiGlide's chord

- Owner: Arp and Harp should be settings of the stock arp, not DigiGlide parameters. DigiGlide decides the notes,
  the arp decides when and in what order.
- The arp page ([ARP]): MODE, SPEED, RANGE, N.LEN, a note OFFSET per arp step (knob E) and ARP LENGTH (knob H).
  MODE has 8 values, names in two tables of 8 pointers at 0x401D4F1C (OFF TRUE UP DOWN CYCL SHUF RAND CHRD) and
  0x401D4F3C (the long names), referenced once each (0x40019240, 0x4001925A); the speed names follow directly, so
  a longer list needs new tables. MODE is sound byte +351 (a copy at +374); these are not parameter-table records.
- Engine (1.12 addresses). Per track: state of 40 bytes at 0x405994A8 + 40 * track (+0 arp step, +4 / +8 / +0x10
  the walk through the note set, +0xC last note, +0x1C octave of RANGE, +0x20 the sound); the held notes as a
  128-bit set at 0x40599728 + 16 * track; for TRUE a linked list in press order (0x40599828); timed note-offs in a
  queue (0x405914A4, head 0x405994A4).
  - "notes in" 0x40029CD4 (track, note record, record base, next index, default length, time base, tick, sound,
    out: arp is on, out: restarted): returns at once with "arp off" when sound +351 is 0; else adds every note of
    the record list to the set (record: 6 bytes, +2 note, +4 length). A newer tick clears the set first
    (0x40029BE8). One caller: 0x40026762, in the sequencer's note event handler.
  - "note out" 0x40029FA6 (track, note): takes one note out of the set.
  - "next note" 0x4002A0BC (track, id): advances the arp step, picks the note by MODE (1 TRUE: the list; 2 UP;
    3 DOWN; the others share one up-and-down walk here), adds 12 per RANGE octave and the step's OFFSET. Called
    from the same handler for arp step events (0x400266E0, 0x4002686E); the note then goes down the ordinary
    note path, so it reaches DigiGlide's frame hook as a plain note-on (as measured on 2026-11-11).
- Design that follows: hook the one "notes in" call. On a DigiGlide track give the arp the chord's notes (TYPE,
  EXT, KEY, VOIC, POS, locks) in place of the root; a key release takes all of them out. While the arp is on,
  DigiGlide lets the arp's note-ons through as single notes; MODE CHRD keeps today's behaviour (the whole chord
  on every step). Stock's modes, SPEED, RANGE, N.LEN, OFFSET and LENGTH then work on DigiGlide's chord with no
  new parameters. Harp as a ninth MODE needs the two name tables moved, the knob's limit raised and a walk of its
  own in "next note": later, after the plain arp works.
- Not known yet: who calls "note out" for a key release; what DigiGlide's frame hook does with the arp's notes on
  a track whose voices are reserved; how SHUF, RAND and CHRD differ (not in "next note").

## Build 18 (2026-11-14): the stock arp plays DigiGlide's chord

- What it does. On a DigiGlide track (VCNT on) with the stock arp's MODE anywhere but OFF and CHRD, the arp is
  given the chord's notes in place of the key's root, and the arp's own note-ons go through DigiGlide as single
  stock notes. MODE OFF and MODE CHRD behave as in image 17 (the whole chord on a note, or on every arp step).
  SPEED, RANGE, N.LEN, OFFSET and LENGTH are stock's and work on the chord. No new parameter.
- Hooks (1.12): the one "notes in" call at 0x40026762 goes to `dg_arp_in`, the one external "note out" call at
  0x40026D3C to `dg_arp_out` (digiglide.c, section "build 18"). `dg_arp_in` calls stock once per chord note with
  a copy of the 6-byte record and returns the first nonzero result (only the call that starts the set returns
  the arp's run id; returning the last one left the arp silent). `dg_arp_out` takes out every note the released
  key added that no other held key still needs. The chord: TYPE, EXT, KEY and POS at the playhead (so locks
  count), close position from the root, seconds as ninths, POS as inversions ((POS - 64) / 8). VOIC is not
  applied to the arp's notes.
- The note-on path: `p_on && nres >= 3 && !dg_arp_single(t)`.
- Tests: `mod/tests/test_b18_arp.py`, 12 checks (UP, DOWN, a POS lock on one step, CHRD, OFF, a non-DigiGlide
  track unchanged, a held key and `dg_arp_out`).
- Not tested: two keys held at once and a key release from the panel (after the first key in KEYB mode the
  emulator registers no further key change, stock track too; `dg_arp_out` is called directly instead), and the
  unit itself. Harp as a ninth MODE is not in this build.

### A regression that was the test harness (cost: most of a day)

- Symptom: with the build 18 source every other suite failed; `select_track` returned False, no key registered.
  Removing only `&& !dg_arp_single(t)` made it pass, so it looked like the new code.
- What it was not: the two builds run the same instructions in the idle frame hook (traced, they differ in
  register names only: m68k objdump at `~/dn2-workspace/m68k/bin`, `-m m68k:cfv4e`; capstone cannot read
  ColdFire); the mod writes nowhere but its own memory and the stack; stock neither reads nor writes the mod's
  memory; a build calling a do-nothing function at the same place failed the same way; shifting BSS by 0x40 did
  not help; forcing single-step emulation did not help.
- What it was: stock's allocator is not re-entrant, and `Kit.call` runs a stock routine on its own stack wherever
  the main thread happens to be stopped. In the failing builds the boot snapshot stopped the main thread inside
  the allocator (pc 0x40120108 or 0x401200E0; image 17 and the passing variant stopped elsewhere). The session's
  first calls allocate, the free list was corrupted, and about 80 frames later free() wrote a free-block header
  into a stock table at the heap's base (0x4464BBF0, key numbers 26..41 read through the vector at 0x4059DDA4).
  The UI then threw std::out_of_range("bitset::set") from 0x4018B1C0 (called at 0x4006A854), nothing caught it,
  and the main thread sat in the abort loop at 0x40139072 while the interrupts went on.
- Fix: `dgkit.settle` steps the main thread until neither its pc nor a return address near the top of its stack
  is in the allocator (1.12: 0x401200E0..0x4012055C), before every `Kit.call`. The failing builds then run 1200
  frames with the table intact. The firmware source did not change for this.
- 1.12 addresses met on the way: malloc 0x401202C8 (takes the mutex 0x445E2E40 through 0x40001608), free
  0x401204CE, operator new / delete 0x40120544 / 0x40120550, heap record 0x4029F0DC (base 0x4464BBF0, bitmap
  0x445A2E40, end 0x4664BBF0, live count at +0x18), __cxa_throw 0x401CFD74, the unwinder's entry 0x4017B370.
- Lesson: when a layout change alone flips a test, look at where the snapshot stopped (`h.pc`) before reading
  compiler output.
- Suites on the prototype (full source, harness fix in): test_b18_arp 12, test_rev5 36, test_every_machine 30,
  test_b17_locks 20, test_rev5_record 14, test_probe 13, test_rev5_trigs 6, test_off_is_stock 6,
  make_brickglide_pad 4: 141 checks, all pass.
- Image: `DN2_1.12_DIGIGLIDE_18.syx`, sha256 51dda574129673e22391090af90793392214c11aa28304499f2c3518ed344f1b,
  preflight 22/22, `__bss_end` 0x46810384. Its code differs from the tested prototype in the build number only
  (10 bytes). Not flashed by me.

## Image 18 on the unit: "the arp is very quiet on quicker progressions" (2026-11-14)

- Report (owner, unit): quiet arp on quicker progressions. Guess: since build 12 every DigiGlide voice has AMP RSET
  forced off, short arp notes are cut before the envelope has risen. Which case (faster SPEED or chords changing
  more often), the sound, AMP ATK, N.LEN and HOLD were not given.
- The guess does not hold. `dg_tx` writes RSET 0 only into voices DigiGlide controls (`DG.ctl`). With the arp on
  (not CHRD) the arp's note-ons are not taken (`!dg_arp_single(t)`), `DG.ctl` stays 0 and nothing in the frame is
  touched. Measured (experiments/arp_level.py, the OS's frames into the SHARC emulator): the record's RSET word
  at every arp note-on is the sound's own (256), and every arp note's 146-byte voice record is byte for byte the
  record of a stock arp playing the same notes (stock OS, the chord's notes put into the arp's set 0x40599728
  from outside), at the same blocks, on the same voices when both reserve 5.
- Arp bytes found on the way (1.12 sound): SPEED +352 (13 = a note every 187 blocks at 120 BPM, 1/16; 10 = 300;
  16 = 125; 19 = 62), N.LEN +354 (14 = 100 blocks, 17 = 118). +357 = 2 leaves 2 notes in 1500 blocks (ARP
  LENGTH, probably). A trig's note end takes its note out of the set; a new trig does not clear it.
- Levels, mean RMS per note, track 1's demo sound, arp UP, N.LEN 14 (100 blocks):

  | AMP ATK | RSET | one chord a bar, SPEED 10 | SPEED 19 | a chord every 4 steps, SPEED 10 | SPEED 19 |
  |---|---|---|---|---|---|
  | 15 (the sound's) | on (the sound's) | -33.5 dB | -30.6 dB | -33.1 dB | -29.4 dB |
  | 90 | on | -52.1 dB | -49.0 dB | -52.2 dB | -48.0 dB |
  | 90 | off | -50.9 dB | -38.0 dB | -51.4 dB | -42.1 dB |

  DigiGlide against stock at ATK 15: within 0.3 dB with 5 against 4 reserved voices, 0.00 dB with 5 against 5.
  (Setting sound slot 81 from the harness does not reach the frame; ATK 90 and RSET were written into the voice
  records of the frames, the same for any image.)
- So: a slow attack and a 60 ms arp note is about 19 dB quieter than a fast attack, on stock just the same; that
  is the quiet arp. Faster SPEED is not quieter in itself. And RSET works the other way round from the guess:
  RSET off lets a reused voice rise from its level, so a fast arp on a slow attack builds up 11 dB (a slow one
  1 dB); RSET on restarts every note from silence. A chord change does nothing to sounding notes: the arp
  restarts on the new trig (first note at the trig), old notes end by their N.LEN, velocity and level words as
  stock.
- No firmware change, no new image. The owner's point 2 (the sound's own RSET for arp notes) is what image 18
  does. Open for the owner: force RSET off on the arp's notes of a DigiGlide track too (louder fast arps on
  pads, but no longer stock's level).
- Test: `mod/tests/test_b18_arp_level.py` (8 checks: SPEED 10 and 19, a chord every 4 steps; same notes and
  blocks as stock, voice records equal, every note within 1 dB).
- Not done: the unit's own case (sound and settings unknown), SPEED above 19, modes other than UP.

## Image 19: PLAY modes Strum and Harp (2026-11-14), sha256 82e7d39a…b192

- Owner: "arp isn't working. it kind of plays. Let's work on harp and strum". Chosen with the owner: Harp is a PLAY
  mode on DigiGlide's own voices (not a ninth arp MODE); Strum is one stroke per chord, the trigs set the rhythm.
- PLAY (CHORD page, knob G, per track in the kit store) now has 4 values: CHRD, STRM, STRU, HARP. `pm_block` in
  `mod/digiglide.c` runs once per block before the output loop; it holds back the attack note-ons it has scheduled
  (`PM.wait`) and fires them when due.
  - **STRM / STRU:** when 2 or more voices attack in one block, they start one after the other ordered by target
    pitch, low to high (STRU high to low), 20 blocks (13 ms) apart.
  - **HARP:** on each new chord (trig or revoice), a run up through the chord's pitch classes from the lowest chord
    voice for 3 octaves, 51 blocks (34 ms) a note, round the chord voices. With BASS on the bass voice is left out
    of the run and struck with its first note. A harp note is the voice's glide pitch moved to the run's note
    (drift and vibrato kept). Notes hold to the trig's end. POS moves the run's start (a POS lock too).
- Arp ("gaps or goes silent"): in the emulator DigiGlide's arp timing equals stock's in every case tried; gaps follow
  the trig length, and finite trigs go quiet on later loops on stock as well (emulator artifact not ruled out). No
  DigiGlide fault found. For the owner: compare with a VCNT OFF track with the same trigs, and try a longer trig LEN.
- Tests: `mod/tests/test_b19_play.py` OK (12 checks: CHRD one block; STRM 20 apart, low to high, second trig too;
  STRU; HARP bass with the first note, 13 notes 51 apart through C MIN7, 3 chord voices, D MIN7 on the second trig,
  no early note-off; POS lock 100 raises the run's start 48 -> 57). Regressions OK: test_off_is_stock, test_b18_arp,
  test_rev5, test_b17_locks, test_every_machine, test_rev5_record, test_rev5_trigs.
- No runtime helpers linked, preflight 22/22. Not flashed.
- Not done: Slop and Pattern; HARP direction, rate and span as settings (fixed at up, 34 ms, 3 octaves); strum and
  harp on the unit.

## Image 20: PLAY knob fix, mode in the header (2026-11-14), sha256 4c8371f4…8d42

- Owner, image 19 on the unit: STRM and HARP did nothing. Cause: `dg_ui_sync` puts back any knob value above
  `PTOP`, and `PTOP[K_PLAY]` was still 0, so knob G always returned to CHRD. Build 19's tests set PLAY in the store
  directly and missed it. Fixed (`PTOP` 3).
- Every DigiGlide page's header names the PLAY mode: "PLAY: CHORD / STRUM DN / STRUM UP / HARP" with no chord
  sounding, "<chord>  <mode>" while one sounds.
- `experiments/b20_play_knob.py`: the knob's edit buffer word 1, 2, 3, 0 reaches the track's PLAY and STRM strums
  (image 19: FAIL, image 20: OK); screenshots in `experiments/out/b20/`.
- Regressions OK: test_b19_play, test_off_is_stock, test_b18_arp, test_b17_locks, test_every_machine, test_rev5,
  test_rev5_record, test_rev5_trigs. (test_m4b_ui predates rev 5: it still uses DEG and SCL and fails on any build.)
- Owner, unit: "VOICES SET TO 6" every loop of a chain whose patterns have different kits, and the sound cuts. Not
  reproduced (one pattern looping: one setter call in 4 loops, `experiments/b20_voices_loop.py`). Likely each kit
  load restores that kit's VOICES and DigiGlide raises it again. Workaround given: VOICES = VCNT in every kit of
  the chain, project saved. Not fixed.
- Not flashed by me.

## Image 21: strums on every trig, SPD (2026-11-14), sha256 5be913e3…e831

- Owner, image 20 on the unit: "strum up and down seem broken"; asked for a speed control for strums and harps.
- Cause, found in the emulator (`experiments/b21_strum_real.py`, trigs C3 F3 G3 D3 on steps 1, 5, 9, 13):
  - trigs that touch or overlap (length 60 or more here) are legato, so the engine glided into each new chord
    unstruck: only a pattern's first chord was strummed;
  - with HOLD on, each restrike strummed the previous chord's notes and then glided to the new one (the note word
    is the voice's glide position).
- Fix: in STRM and STRU every trig strikes, legato or held, at the new chord's notes (the trig takes GLID 0's
  path: gates off, restrike, no glide). A chord setting turned while it sounds still glides (the re-voicing reads
  GLID). A string waiting for its turn keeps ringing at its last note instead of jumping early. HARP unchanged
  (it already ran on every trig).
- SPD, SETUP knob C (`Strum Speed`, record 339, FX word k 88; stock's FX group records stop at slot 40):
  0..127, 64 = the build 19 gaps (13 ms a string, 34 ms a harp note), x 2^((SPD - 64) / 24), so strum 2..82 ms
  and harp 5..210 ms. The cell shows ms for the track's mode (harp gap with PLAY HARP, else strum). Read at each
  trig, not p-lockable. Stored in 16 bytes after the 18 older settings (+0x29d3..+0x29e2 of the kit record, inside
  the padding) as value + 1, so kits saved before image 21 read 64. The 18 older settings keep their place.
- Tests: `mod/tests/test_b21_strum.py` OK (STRM and STRU with gaps, legato, HOLD on, GLID 0: each of 4 trigs gives 4
  note-ons 20 blocks apart in pitch order, in its own chord; HARP legato runs on every trig).
  `mod/tests/test_b21_spd.py` OK (STRM gaps 20, 3, 120 at SPD 64, 0, 127; HARP 144 at SPD 100; an old kit reads 64;
  the SETUP knob's buffer word reaches SPD; screenshots in `experiments/out/b21/`). Regressions OK: test_b19_play,
  test_off_is_stock, test_b18_arp, test_b17_locks, test_every_machine, test_rev5, test_rev5_record, test_rev5_trigs.
- No runtime helpers linked, preflight 22/22. Not flashed by me.

## Image 22: strummed strings are plucked (2026-11-15), sha256 f9053f82…0698

- Owner, image 21 on the unit: STRM and STRU "don't work, they just hold notes over the top", with HOLD on.
- Cause (`experiments/b22_hold_audio.py`, the OS's frames through the SHARC emulator, HOLD on, trigs C3 F3 G3 D3 on
  steps 1, 5, 9, 13): with HOLD on no note-off is ever sent; each string's strum note-on lands on a voice that still
  sounds, and every DigiGlide voice has AMP RSET off (build 12), so the envelope carried on: the strings changed
  pitch one by one with no attack, the chord seemed to hold over the strum. Image 21's tests counted note-ons and
  their pitches only, not the sound. The same holds for legato trigs and for HARP over a sounding voice.
- Fix: a voice's turn in a strum or a harp run has RSET on (256) in its record for that block: the string restarts
  from silence, a pluck. CHRD and the arp are unchanged (RSET off, a held chord's strike rises from its level).
- Measured, AMP ATK 50 in every voice record: the level during a strum falls 11 to 17 dB below the held chord as the
  strings restart (image 21: about 5 dB, the chord's own movement). With the test sound's fast attack the dip is
  only a few ms long.
- Tests: `mod/tests/test_b22_pluck.py` (HOLD on: STRM, STRU, HARP note-ons all RSET 256; CHRD all 0), plus the
  image 21 suite: all OK (test_b22_pluck, test_b21_strum, test_b21_spd, test_b19_play, test_off_is_stock,
  test_b18_arp, test_b17_locks, test_every_machine, test_rev5, test_rev5_record, test_rev5_trigs).
- No runtime helpers linked, preflight 22/22. Not flashed by me.

## Image 23: bass patterns and the drone (2026-11-15), sha256 ee85e2e3…df36

- Owner's specs: bass patterns (BPAT, BRATE) and the drone (TYPE 5TH, TIME DRON, BLOOM, STRK, the drone presets).
- SETUP page: A HOLD, B BASS, C BPAT, D BRAT, E SPD (moved from its old knob), F BLOM, G STRK. The header shows the
  track map ("ON 1.3...").
- Bass: BPAT HOLD PULS OCT WALK R-5 ARP OFFB 332 on the bass voice (BASS FOL or SOLO), grid from the tempo, BRAT
  1/4 1/8 1/16, gates 80 % of a step, odd steps at 80 % level (OFFB all full), each note plucked (RSET 256). WALK's
  fifth and ARP's third are the chord's own. A new root restarts at step 0, the same root goes on. Pattern notes play
  the new root's own pitch, not the root's glide. BPAT HOLD is image 22's held bass. The release is the sound's REL.
- Drone: TYPE 5TH (root and fifth). TIME DRON: voice i takes GLID x (1 + 0.25 i), scaled so the top voice lands at
  GLID. BLOOM (centre 0): below thins the upper voices to the lowest alone, above breathes them between 25 % and
  100 % on each voice's own phase. STRK OFF 1 2 4 beats restrikes a held chord (rises from its level).
- Store: kit padding now "DGK2", 16 bytes a track; a "DGK1" kit reads as it was and is rewritten as DGK2 on its first
  edit, keeping every setting. An older image reads a DGK2 kit as having no settings.
- Locks: lane 0 has a new code (8192 + POS + 129 x (TYPE + 6 x EXT)), old words still read; new lane on sound slot 65
  (BPAT + 9 x BLOOM), safe on every machine (`experiments/b23_slot65.py`).
- Not built: BASS SOLO on a second track, BLOOM as an LFO destination.
- Tests: `mod/tests/test_b23_bass.py`, `mod/tests/test_b23_drone.py`, plus the image 22 suite (lock words, the store
  header and every_machine's knob steps updated for the new code, DGK2 and TYPE's fifth value): all OK.
- No runtime helpers linked, preflight 22/22. Not flashed by me.

## Image 24: bass balance (2026-11-16), sha256 5a53ab4a…9ae2

- Owner's report: "bass is quiet" (one bass voice under four chord voices, and slow attacks were plucked from zero).
- SETUP H BAL (-64..+63, centre 0, per track, not p-lockable). Up raises the bass to double and lowers the chord to
  a quarter at +63; down fades the bass to silence at -64. Measured (`experiments/b24_bal_audio.py`): bass minus
  chord -5.5 dB at 0, +5.2 dB at +32, +20.8 dB at +63.
- Fix: levels were scaled from a voice DigiGlide had already scaled in the same block (double scaling). Each voice
  now scales the source's level read before any voice is touched. This also affected image 23's BLOOM depth.
- The pattern's 80 % accent is applied after the 0x7F00 cap, so it survives a boosted bass.
- Slow attack: with the sound's AMP ATK at 32 or more, pattern notes rise from the bass's current level instead of
  being plucked (no RSET).
- Store: DGK2 grows by a 16-byte BAL row (stored value + 1, so an image 23 kit reads BAL 0).
- Tests: `mod/tests/test_b24_bal.py` (A-F), plus the image 23 suite: all OK.
- No runtime helpers linked, preflight 22/22. Not flashed by me.

## Image 25: HOLD lets go when turned off (2026-11-16), sha256 2b758b5d…bd0c

- Owner's report: "stuck on hold". A chord HOLD had latched kept sounding after HOLD was turned off (CHORD knob H
  or [FUNC] + push H): only [STOP], the sequencer stopping, muting the track or playing the same chord again let it
  go. Present since HOLD existed, not new in image 24.
- Fix: while a chord is held, the track's HOLD is read every block; once it is off the chord is no longer kept and
  releases at once, or when the last key or trig of it comes up.
- Tests: `mod/tests/test_b25_hold.py` (A-D: image 24 fails A and B, image 25 passes all).
- Harness (not firmware): image 25's boot snapshot stopped the main thread switched out inside the RTOS primitives
  (0x400016D2 / 0x40001724 on its stack, the mutex malloc takes through 0x40001608). A `Kit.call` from there left the
  UI at the throw site 0x4018B4A0 and no trig reached the frame, so `test_every_machine` failed A and C on image 25
  only. Shown by a same-layout variant without the release that happened to snapshot elsewhere and passed, and by
  DigiGlide's state (no trig seen, `DG.latched` never set, so the new line never ran). `dgkit.settle` now also
  waits while the pc or a return address is in 0x40001500..0x40001900; image 25 then plays as image 24.
- Full suite on image 25 after that: all pass except `test_every_machine` C, which also is the harness: its session
  stops the UI at `h.frames(3200)`, and on image 25 that point leaves the sequencer playing nothing at all (no stock
  note-on either, which the HOLD line cannot cause). The same part with 3000 frames takes all 4 chords on 5 voices
  (0x1f); with 3400 it fails the same way. Image 24 passes at 3200. Test left as is; worth making its start robust.
- DRONE PULSE (`experiments/b25_drone_pulse.py`): not verified. LFO1's values written to the sound (or through the
  live-record call 0x4003F1AE, now in `port/addr_1.12.json`) do not reach the stock LFO in the emulator, and the
  LFO page's knobs land on wrong values with DEST needing its list confirmed. Found on the way, from the firmware's
  own value text: LFO1 = sound slots 1..8 (entries 75..83) SPD MULT FADE DEST WAVE SPH MODE DEP; SPD 0x6000 = 32.00;
  MULT 1..2k at indexes 0..11 and again at 12..23; DEST is a sound slot (AMP VOL 90); DEP (v - 0x4000) / 128, so a
  positive depth on a VOL at 127 is clipped away.

## Image 26: "CHORD MODE ON?" once a track (2026-11-16), sha256 b16385ab…8cf7

- Owner, image 25 on the unit: "chord mode on? keeps popping up". The message came with every block that brought
  three or more notes (stock chord mode, a multi-note trig, a MIDI chord), again as soon as the last one had gone.
- Fix: `dg_cmwarn` (bit t): shown once a track until power off. Nothing else changes.
- Tests: `mod/tests/test_b26_cmwarn.py` (three keys in one panel message; image 25 fails A and B, image 26 passes).
  The emulated panel drops every second key press here (HOLD on or off), so the test presses, releases and waits.
- Harness, twice more (not firmware), both shown by moving the test's own timing:
  - `test_every_machine` C: the stop at `h.frames(3200)` leaves the sequencer playing nothing on images 25, 26, 27
    (3000 plays, all 4 chords on 5 voices). The test now uses 3000.
  - `test_rev5_record` C: [STOP]'s release came 896 blocks after the key on image 25 and 907 on images 26 and 27;
    the test watched for 900. It now watches for 1500.
- Owner, the same day, image 25 on the unit (build read off [FUNC] + push G): "odd behaviors on glide", "arps on other
  tracks overwhelmed", "notes being stolen from other tracks". One DigiGlide track, three drum tracks, one bass,
  BASS off; the VOICE menu read as "10, 6 above it" (taken as 6 reserved on the DigiGlide track, 10 free: not
  confirmed). Not reproduced, cause not found:
  - `experiments/b26_other_arp.py`: a stock arp beside a DigiGlide track, images 21, 24, 25: the arp's 35 notes all
    play, DigiGlide stays on its 5 voices, the three images alike.
  - `experiments/b26_demo_steals.py`: the demo pattern, every track playing, VCNT OFF / 5 / 6: no note of another
    track cut by a later one, images 21 and 25 alike. (The demo is too light to run 10 voices out.)
  - `experiments/b26_two_dg_tracks.py`: two DigiGlide tracks at once do break it (the second plays single stock
    notes, the others share 6 voices), but the owner has one.
  - Every write of DigiGlide's frame hook stays inside DG.base .. DG.base + DG.nres (read, not measured).
  - Asked for and not yet given: the VOICE menu per track, the two [FUNC] + push G lines while a note hangs.

## Image 27: a strum damps the strings that still sound (2026-11-16), sha256 5f89ba9c…6060

- Owner, image 25, all trigs, HOLD on: "strum down still doesn't work with chord hold on", "there's a ring going on
  that's holding over". Not confirmed by the owner as this; built as its own image so 26 stays the plain one.
- Measured on image 25 (`experiments/b26_strum_seq6.py`, `b26_strum_hold_keys.py`: 6 voices, BASS off, HOLD on):
  every trig and every key strikes all 6 voices in the right order, 20 blocks apart, in its own chord. What is left
  is build 21's rule: a string waiting for its turn keeps ringing at the last chord's note. With HOLD on (or legato
  trigs) nothing is released, so the old chord sounds under the strum until each string's turn: on STRU the low
  strings last (100 blocks at SPD 64 with 6 voices, up to 0.5 s at SPD 127).
- Fix: in a strum (STRM, STRU) a string that still sounds and waits for its turn fades to level 0 in DAMP_BLOCKS
  (6 blocks, 4 ms) and comes back at its note-on (plucked, RSET on, build 22). The first strum, CHRD, HARP, the
  bass voice and the time between strums are unchanged.
- Tests: `mod/tests/test_b27_damp.py` (A STRU and B STRM with HOLD on, C STRU legato: silent from 6 blocks after
  the strum starts until the string's turn, back at its level at the note-on; D CHRD never drops; image 26 fails
  A, B, C). Checked on frames (the level word), not listened to or rendered.
- Found on the way: the level word of every voice rises from 0 over the first ~52 blocks after [PLAY]; image 21
  does the same.

## Dropouts on other tracks with DigiGlide on: measured (2026-11-16, images 21 to 26, no new image)

- Owner (video, image 25, DigiGlide on track 13, VCNT 6, HOLD on): the pattern is complete with DigiGlide off (4:03)
  and loses bass and rhythm with it on (1:25, 2:49). "DigiGlide must not make other tracks drop notes."
- Voice pool, `experiments/b28_dropouts.py` (image 26, DigiGlide on track 13, kick / snare / 16th hats / overlapping
  bass on tracks 1..4, 12,000 blocks): note-ons reaching the DSP are the same off and on (8 / 4 / 32 / 16), no note
  cut by another track, DigiGlide on voices 0..5 only, the others on 6..15. Not the cause in the emulator.
- Audio ISR, `experiments/b28_isr.py` (emulator instructions per audio block, same pattern): VCNT OFF median 55,135,
  p99 55,364. VCNT 6: image 21 and 22 median 58,328, p99 63,235; 23: 59,551 / 68,092; 24: 59,516 / 68,607; 25:
  59,822 / 68,913; 26: 59,861 / 68,951, max 77,624. So DigiGlide adds 4,700 a block (3,200 on image 21, 1,900 at M3)
  and about 14,000 on one block in 38 (every 25 ms; 8,000 on image 21). The jump is image 23 (bass, drone, bloom).
  VCNT 3 saves 1,800; DRFT and VIB at 0 save nothing; HOLD off saves 300.
- Profile, `experiments/b28_profile.py` (mod code bytes run per ISR by function): dg_tx itself 73 %, umul + mulsh
  11 %, dg_block 6 %; the 25 ms blocks add read_ui / par_at / st_get / dg_marked / dg_par / dg_lock_get (the
  parameters read again in the ISR).
- Budget on the unit: not measured. With the earlier estimates (stock ISR 64 % busy, mod code about 4x stock's cycles
  per instruction) image 26 is about 86 % busy on every block and over 100 % on the 25 ms blocks; image 21 about 79 %
  and about 100 %. That leaves the sequencer and arp tasks too little time: late and lost notes on every track.
- Fix planned, not built: the slow work in dg_tx at a lower rate or on change only, the parameter read out of the
  ISR, the hook's worst time from a hardware timer on the [FUNC] + push G lines, a suite test with a cost limit.

## Image 28: DigiGlide's work moved off the frames that carry notes (2026-11-16), sha256 1b02c2a2…10a4

- Cause (see the entry above): hook time on frames that carry note-ons. A late frame is dropped with every track's
  note-ons.
- Chord event deferred: the notes of a trig are noted in the hook and the chord is worked out on the first frame
  with no outgoing note-on (at most DEFER_MAX 6 frames, then forced). In the test pattern the wait is 1 frame
  (0.67 ms), never forced.
- Parameters: one read per block in rotation instead of all 24 every 30 blocks; a full re-read only after a
  change (or at a new step with locks), and never on a note frame. Live knob following is up to about 24 blocks
  (16 ms) slower.
- Cheaper steady path: clone_voice copies longs, bp_block returns early when BLOOM and BAL are at rest, the HOLD-off
  check every 16 blocks.
- Measured in the emulator (`experiments/b28_hook.py`, mod code bytes per frame, DigiGlide on track 13 VCNT 6 with
  kick / snare / hats / bass): frames with note-ons max 66,160 (image 26) to 20,272; median 24,186 to 15,952; p99
  41,568 to 20,292; the 30 block spike is gone. The largest frame, 53,046, is the deferred chord event on a quiet
  frame. Instructions per audio ISR: median 59,861 to 57,910, p99 68,951 to 58,959.
- Status box ([FUNC] + push G): third line "H### N### W## D#". H = longest hook time in microseconds, N = longest
  on a frame with note-ons (a block is 667), W = events forced onto a note frame, D = longest wait in frames. The
  time comes from DTIM3's counter (0xFC07C00C), read only while the box is on. The emulator does not model that
  counter (reads H000 N000): unverified until read on the unit.
- Suite: all 18 earlier tests pass unchanged. New `tests/test_b28_load.py`: cost limits on note frames in CHRD,
  STRM, STRU, HARP (with a bass pattern), no forced event, other tracks 8 / 4 / 32 / 16 note-ons on voices 6..15,
  DigiGlide on 0..5 only, pattern plays with the box on. Image 26 fails the cost limits.
- Not done: dg_block and the voice loop (about 2,800 instructions a block) are not reduced. Not flashed; the real
  load on the unit is unmeasured.
- Preflight PASS (13 checks, integrity 22/22, signed, 1,917,384 bytes of the 2 MiB USB buffer), run again by hand on
  2026-11-17. Full sha256 1b02c2a276194c2481a5d8307bfeb6433978d92a05d934ee20c7bf93f0f110a4.
- Open: the glitch noise at 2:20 in the owner's video. The video's audio from 2:18.0 to 2:19.7 has no drum hits at
  all (the same dropout), then an abrupt chord change at 2:19.7; no separate noise burst or sample jump stands out
  above the drum hits. Not explained. Listen for it on image 28.
- Open: the deferral waits for a frame with no note-ons, not for one with no note-offs. If the deferred chord
  makes that frame late and a late frame is dropped whole, another track's note-off on it could be lost. Decide
  from H on the unit (stock's ISR is estimated at 64 % of the 667 microsecond block, so about 240 is the ceiling).

## Image 29: TUNE and FAN, and the DigiDrone sounds (2026-11-18)

`~/dn2-workspace/build/DN2_1.12_DIGIGLIDE_29.syx`, sha256
26253e12c8a064934cf088cc83c181e1ea934cfbaef37ee6e85f7c5b09afd186, preflight PASS, 1,917,586 bytes. Not flashed.

- TUNE (EQL / PURE), parameter 24. PURE moves each chord note to an exact ratio above the chord root; the root stays
  equal tempered. Table (`PURE16` in core/dg_core.c): 16/15, 9/8, 6/5, 5/4, 4/3, 7/5, 3/2, 8/5, 5/3, 9/5, 15/8;
  octaves are exact. The owner specified the thirds, fourth, fifth, sixths, sevenths; 16/15, 9/8 and 7/5 are
  choices made here. Glides run between the tuned pitches. HARP notes are tuned too.
- FAN (0 to 127), parameter 25. Spreads the chord voices evenly either side of pitch: at 127 the outer voices are
  20 cents out, a four voice chord's inner ones a third of that. Added on top of DRFT. The bass voice is not fanned.
- Page: a fourth DigiGlide page "TUNE" after CHORD, MOTION, SETUP (all full). Knob A TUNE, knob B FAN.
- Store: TUNE at DGK2 +276+t, FAN at +292+t (value + 1); 308 of the 337 spare bytes used.
- Locks: both on lane 65 with BPAT and BLOOM (word = BPAT + 9 BLOOM + 1161 (TUNE + 3 FAN)); words written by
  image 28 read unchanged. The 15 bit word leaves FAN 8 lock levels: 0 18 36 54 73 91 109 127. The unlocked FAN
  has all 128.
- Changing TUNE or FAN on a sounding chord glides to the new pitches at GLID.
- `tests/test_b29_tune.py`: PURE within 0.09 cent of the ratio over 40 chords (5 TYPE x 8 EXT; 8/5 occurs in no
  chord type, so it is in the table but unplayed); EQL note words whole semitones; FAN on 3 to 6 voices; TUNE EQL
  and FAN 0 give frames identical to image 28 over 3,404 blocks; glide between tuned pitches; lock words, old word
  compatibility, a locked step plays PURE and fanned; store bytes; four pages; lockable rows.
- Suite: all 19 earlier tests pass (test_every_machine now accepts 6 or 7 pages).
- Save and reload: only the store bytes are tested. The emulator cannot exercise a real save and reload (as for
  every DGK2 value); check on the unit after a power cycle.
- DigiDrone sounds: five FM TONE sounds (STILL AIR, SLOW CHAIN, DARK RING, IRON BELLS, BEAT FIELD) in
  `~/glide/DIGIDRONE_SOUNDS_29.md`, patches `experiments/b29_patches.py`, renders `renders/b29/*.wav`. FM TONE
  routing, ratio tables and AB LEVEL measured in the SHARC emulator (`experiments/b29_fm_*.py`). COUPLE on all
  five is AB LEVEL (LVAB, slot 53). LFOs in the renders are written into the frames, not the stock LFO: depth and
  SPD x MULT unverified on the unit.

## Image 30: the deferred chord also avoids note-off frames (2026-11-18)

`~/dn2-workspace/build/DN2_1.12_DIGIGLIDE_30.syx`, sha256
cbc9c29d2f45311803da0246a1809c01e8f293f3c6bfa660fa1654ef8fda32ee, preflight PASS. Not flashed. Image 29 plus one
change; supersedes it.

- dg_tx: the deferred chord event now runs on the first frame with neither a note-on nor a note-off (was: no
  note-on). Closes the open point of image 28: a late frame is dropped whole, so a chord event on a note-off frame
  could have lost another track's note-off. W on the status box now also counts events forced onto a note-off frame.
- `tests/test_b28_load.py` gained a check per mode: the hook's cost on frames with note-offs stays under the note
  frame limit. It passes on image 30 (20,736 CHRD, 16,950 STRM / STRU, 21,368 HARP) and also on image 29: in the
  test pattern no chord event happened to fall on a note-off frame, so the test does not tell the two images
  apart. The fix is by reading the code, not by a failing test. Longest wait still 1 frame, none forced.
- test_b29_tune (23 checks) and all 18 other tests pass on image 30.
- Still open: the 2:20 glitch; H N W D on the unit.
- DigiDrone second set (2026-11-18): GLASS ORGAN, UNDERTOW, WIRE CHOIR, HOLLOW FIFTHS, STORM GLASS in
  `experiments/b30_patches.py`, renders `renders/b29/{organ,undertow,wire,hollow,storm}.wav`, sheet appended to
  `DIGIDRONE_SOUNDS_29.md`. Rendered on the first set's captures. STORM GLASS turned down once (brightness
  centroid 3.4 kHz at the swell, now 2.7 kHz). Not heard on hardware.

## Image 31: the ten DigiDrone sounds in the firmware (2026-11-19)

`~/dn2-workspace/build/DN2_1.12_DIGIGLIDE_31.syx`, sha256
cdbd894991e01856c149607f45d75219f37da3d6a710ada60261447dd97e7803, preflight PASS (22/22, signed). Not flashed.
Image 30 plus the sound loader.

- Shortcuts: [FUNC] + push knob A steps to the next of the ten sounds (name shown); [FUNC] + push knob B loads the
  picked sound onto the current track. Synth tracks only. A load replaces the track's whole sound (not saved until
  the owner saves) and sets the sound's DigiGlide settings.
- The sounds are stored as ten 360 byte stock sound records (`tests/make_drones.py` writes `dg_drones.h`).
- Loader: shortcut_tick (audio ISR) only sets dg_drone_req (bit 0 pick, bit 1 load); dg_ui_step does the work.
  drone_load copies the record to RAM, calls stock 0x400DD1EA(sound, buf), clears the per voice sound pointers at
  0x800052A0+8 for the track's voices so the DSP mirror refreshes, then sets the DigiGlide values with dg_par_set.
- LFO encoding found here: SPD word = 0x4000 + speed*256; MULT index 0 = x1; DEST word = slot << 8; the swing is
  2 x (DEP word - 0x4000), so the stored depth is half the sheet's first figure; SPD x MULT = 8 is 16 bars
  (measured on DARK RING's filter only). LFO WAVE is left at the sound default (index 1), not triangle.
- Leftover movement of up to 3 steps on slots 43, 68, 81, 98 after a load, source not found. Emulator only.
- `tests/test_b31_drones.py` passes; test_b29_tune and all 19 earlier tests pass.
- Placement sensitivity (not explained): the first build of image 31 failed test_b17_locks (the emulated panel
  dropped [RECORD] and a trig key's release) and test_every_machine (dropped [PLAY]). Neither test touches the
  drone code (dg_drone_req never changes). Image 30 drops [PLAY] too (5 of 10 in a probe; image 31 3 of 10). A
  variant with two no-ops in drone_pick, code that never runs in the test, passed; the build without them (sha
  43ce5374...4423d5) failed at four timing offsets and from a fresh boot snapshot. So the emulator's dropped key
  events move with where code sits in the image, not with what it does. The two no-ops are kept in drone_pick
  (commented). Why placement matters inside the emulator is not known; it could in principle be a real timing
  effect on the unit, so check [RECORD] and trig key releases there.
- Test changes for the same reason: dgkit.Session.play retries up to three times when no frame has a note-on;
  test_b17_locks sends up to 4 extra key releases; test_every_machine section F retries its second play.
- Not heard on hardware; the loader has never run on the unit.
- Still open: the 2:20 glitch; H N W D on the unit.

## Image 32: two DigiGlide tracks sound at once (2026-11-19)

`~/dn2-workspace/build/DN2_1.12_DIGIGLIDE_32.syx`, sha256
c6ad8d45a57996f14e513861647f52c456a0597578b75cd63417089988a1fbfb, preflight PASS (22/22, signed), 1,919,909 bytes.
Not flashed. Image 31 plus this.

- Owner on image 31: a loaded drone played "just single notes". Cause: another track had DigiGlide on and its
  chord was sounding. Through image 31 there was one chord engine: while one track's chord sounded (held, playing
  or ringing out) every other DigiGlide track got stock's single notes. Every drone sets HOLD on, so it never let go.
- Now two chord slots (NE = 2 in digiglide.c). Everything a chord owns is kept twice: the core state (TS), DGS,
  dg_cur, dg_ui, dg_name, PM, BP, PD, the level and restrike state, damp, nw_last. The old names are macros for "the
  slot in work" (sel); only the hook changes the slot and puts slot 0 back. Fields there is one of (blocks, the UI's,
  the counters) are GL = slot 0's. The symbols DG, T, dg_ui, dg_name, dg_cur, dg_tail_log are slot 0's (aliases).
- dg_tx_body: the frame's note-ons are routed once (RT, route): to the slot that plays the note's track, else the
  one that last did, else a slot with nothing sounding and no event waiting (slot 0 first). Then each slot runs its
  part (slot_block) on the stock words and adds to the outgoing note-on / note-off words. One chord event is worked
  out a frame, the slots in turn.
- A third DigiGlide track that plays while both slots sound gets one stock note (as a second one did before).
- dg_chord_name and the status box's second line look up the slot that plays the track.
- `tests/test_b32_two.py` (12 checks): drone (HOLD, 4 voices) on track 2 and three chords on track 3, each on its
  own voices; no note-off and no pitch change on the drone from the other track; the glide track's chords equal
  the ones it plays alone; chord name; third track gets a stock note; both play again after the stop. The harness
  does not play track 1's trigs in this setup (image 31 neither), so the test uses tracks 2 and 3.
- All 21 earlier tests pass on image 32 (no placement trouble this time).
- Load, mod code bytes a block in the emulator (scratch scripts, not in tests/). One track, 6 voices: median 14,456
  (image 31: 14,430). With kick, snare, 16th hats and bass: one track 6 voices, note frames at most 19,418; glide 6
  + drone 3: median 24,568, note frames 27,812; glide 6 + drone 4: 26,920 / 30,452; 6 + 6 without drums: 31,820 /
  36,148. test_b28_load's limit for note frames is 30,000. Every drum and bass note went out in each case, none on
  a chord voice. The emulator cannot drop a late frame: H on the unit decides.
- Not tested: keys played by hand on two tracks; MIDI in on two tracks; the pages while slot 1 plays the shown
  track; save and reload. Nothing of image 31 or 32 has been checked on the unit except the owner's report above.
- Still open: the 2:20 glitch; H N W D on the unit; the drones' fifth-stack chords may fuse into one tone.

## Image 33: a lighter block, and the deep DigiDrone set (2026-11-20)

- Owner on image 32, one glide track (HARP, no drone) with bass and kick: "I am loosing sounds", then "anyway to make
  this more efficent". Status box: H 1102 (shown 102), N 332, W 00, D 2 (microseconds; a block is 667). And: "the
  digidrones are too shallow sounding".
- The readings are real: DTMR3 = 0x001D (bus clock / 16), DTRR3 = 275000 at 30 Hz, 8.25 counts a microsecond.
  CACR 0xA50CE100 (instruction cache on; data default not cached), ACR0 0x4007E020 (0x40000000 to 0x47FFFFFF data
  cached). The frame at 0x80005E60 is on-chip SRAM.
- Not explained: 332 microseconds for about 14,800 code bytes is about 22 ns a byte, roughly ten times what stock's
  own interrupt code could take. A block touches only about 195 16 byte lines (3 KB), so cold caches do not explain
  it. Either the mod's region runs uniformly slowly or the hook is preempted. The status box now measures it (below).
- Fewer instructions: clone_voice copies four longs a turn; the note loop is skipped with no note-on / note-off;
  nw_last, pan_last, lw_last cache the words written; dg_core: sin_cyc 32 bit path, vib_term, the scrub skip (host
  checked exact).
- The light block: slot_block writes the voices from the last block's result and counts the block as owed (DG.owed)
  instead of working the chord out, (a) on a frame with another track's note-on or note-off, (b) on every second
  block of a steady chord (no event waiting, no strum / harp / bass pattern / restrike / level work running,
  DG.hurry clear). The next full block runs the owed blocks first, so nothing drifts in time; pm_block schedules by
  GL.blocks anyway. DG.hurry (set on a chord's end, a new HARP chord, a preset load, VOICES changed) forces full
  blocks until one has run.
- Emulator, one 6 voice HARP track with drums, mod code bytes a block: image 32 median 13,230, note frames at most
  14,784. Image 33: median 4,478, mean 6,470, 1,089 of 3,004 blocks light, 1,679 under 6,000; most frames with
  another track's note-on cost about 4,400. Not better: the worst block (12,060 on a note frame, 13,282 overall),
  where a chord event and the owed block meet. A steady chord under a kick is where it helps.
- Side effect, measured against image 28 (test_b29_tune D): after a chord change on a note frame a glide runs one
  block early, note words up to 4/256 semitone off for the glide's length; gate, velocity and level words are
  identical. The check now allows 6/256 on note words.
- Status box line 2 now alternates every 2,048 blocks: "H### N### L###" (L = the shortest hook time while a chord
  sounds) and "I## U## F##": the same 200 turn loop timed in the hook (I) and in the UI task (U), and 256 frame reads
  (F), microseconds, shortest seen, at most 99. I much above U says the hook is slow or preempted; F large says frame
  memory is slow. W and D are no longer shown.
- Deep drones: all ten reworked (experiments/b33_patches.py, renders/b33, tests/make_drones_tab.py, dg_drones.h
  regenerated with make_drones.py; the sheet has a new section). An operator an octave down, more FM and feedback
  under a lower filter, wider offsets, chorus / delay / overdrive / more reverb.
- Voicings measured on image 32 from a C3 trig, 4 voices: MAJ EXT 9 or 6+9 gives 36 48 55 62 (no third); MAJ with
  MAJ7, 7, MAJ7+9 or 6 gives 36 48 55 64; MIN gives 36 48 55 63; 5TH at VOIC 127 gives 36 48 60 67. So the old
  STILL AIR, GLASS ORGAN, STORM GLASS and IRON BELLS played no third. New settings: STILL / STORM and ORGAN MAJ7,
  BELLS EXT 6, BEAT FIELD VCNT 4 MIN VOIC 70, HOLLOW FIFTHS VCNT 4 VOIC 127. Every drone but HOLLOW FIFTHS has a third.
- Tests on image 33: the 19 earlier tests, test_b31_drones, test_b32_two and test_b29_tune (D with the tolerance
  above) pass. Preflight PASS, runtime helpers none. sha256 bb26a15a...cb266a2.
- Not tested: anything on the unit. The light block has not been heard; whether every second block is audible on
  fast vibrato or short glides is not known (750 pitch updates a second instead of 1,500).
- Still open: the 2:20 glitch; why a block takes so long on the unit (read L and I U F); the glide track's VCNT.

## Image 34: note-ons off the heavy frame, settings follow a pattern change, drone loads rest STRK (2026-11-21)

`~/dn2-workspace/build/DN2_1.12_DIGIGLIDE_34.syx`, sha256
848625fb2785bdf2b9e3fbd35c002f18c9c01c62c8addd2ab91a08156c0b3ffd, preflight PASS, runtime helpers none.

- Owner on image 33: "better for sure! might be good enough for release", then: "there is delay when first starting
  glide", "sometimes the arp or the chord lags on press", "typically arp starts and then the chord hits after"
  (played by hand, BPAT ARP, chord and bass pattern as one), "switching between patterns ... single notes after",
  "why does the drone keep repeating or restarting after 3 seconds" (STRK was on: "strk did it").
- Emulator, images 32 and 33: a chord sounds 2 blocks after its note, by trig or by key, with or without drums on the
  step; with BPAT 1 all five voices start on one frame. No lag to find there.
- Reading of the lag: on the unit a frame later than its render is dropped with its note-ons (build 28). A chord's
  note-ons rode on the frame that worked them out, the heaviest kind (profile on 33p: 11,400 code bytes with one
  owed block, 13,250 with two; a light frame 4,300). If that frame is lost the chord's voices never start, the bass
  pattern's next note does, and the chord comes at the next strike. Not proven on the unit before the change.
- Change: note-ons and note-offs of a chord are kept (DG.pend_on, DG.pend_off) and sent on the next frame, which is
  made a light one. Until then a voice with a waiting note-on keeps the note and level words it had. A chord sounds
  3 blocks after its note now (one block, 0.67 ms, later). The strum damp counts caught-up blocks.
- Owner on image 34: "34 is great. really responsive btw".
- Pattern change (inherit_tick, UI task): settings live in the pattern's kit, so a pattern whose kit never had them
  played single notes. When the kit changes, a synth track that was on before, has no settings in the new kit and
  holds the same sound (machine and name) takes the old kit's settings, once ("DIGIGLIDE KEPT: TRACK n"). Not run
  in the emulator (no pattern change there); the owner's check on the unit is owed.
- Drone load: also sets PLAY CHRD, BPAT off, BLOM 64, STRK off (make_drones_tab.py; DRONE_DG rows are 30 bytes).
  make_drones.py must be run with image 33 as the converter's host: on image 34's layout the emulated panel loses
  the machine select and the blobs come out wrong (the script says FAIL; dg_drones.h was regenerated with 33).
- Tests changed for the one block: test_b29_tune D (gate words as image 28's or its block before; note words within
  6/256 semitone; blocks at a note edge left out), test_b27_damp E (the next strum damps a block before its first
  note-on). test_rev5 F needed the kept note word.
- Tests on the final image: test_b32_two, test_b31_drones, test_b28_load, test_every_machine, test_rev5,
  test_rev5_ui, test_b24_bal, test_b23_bass, test_b21_strum, test_b21_spd, test_b19_play pass; the build before the
  drone table change passed test_b27_damp, test_b29_tune D and test_rev5 as well. A clean run of all 22 was still
  going when this was written (two runs wrote to the same output files and had to be thrown away).
- MANUAL.md added (how to use it), linked from the README.
- Still open: the 2:20 glitch; why a block takes so long on the unit (L and I U F not read back yet); the status
  box's timing lines are still in the image.
