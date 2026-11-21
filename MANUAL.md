# DigiGlide: how to use it

This describes image 34 on OS 1.12. DigiGlide is in development; what is known not to work yet is at the end.
Design details are in [GLIDE_SPEC.md](GLIDE_SPEC.md), the history in [notes/build_log.md](notes/build_log.md).

## The idea

A synth track with DigiGlide on plays a whole chord from one key or one trig. When the next chord comes, the voices
glide into it instead of jumping. The note you play is the chord's root; TYPE, EXT and KEY decide its notes.

It works on FM TONE, WAVETONE, FM DRUM and SWARMER tracks. It does not work on MIDI tracks.

## Switching it on

1. Select a synth track.
2. Press [SYN] until the DigiGlide pages appear. There are four, after the machine's own pages: CHORD, MOTION, SETUP,
   TUNE.
3. On SETUP, turn knob A (VCNT) from OFF to 3, 4, 5 or 6. That is the switch, and the number of voices the chord
   uses, the bass voice included.

Shortcut: **[FUNC] + push knob E** flips the current track between OFF and its last voice count. The screen shows
"DIGIGLIDE ON (5 VOICES)" or "DIGIGLIDE OFF".

With VCNT OFF a track is exactly stock.

### Voices

The Digitone II has 16 voices. A DigiGlide track reserves its voices for itself (the stock VOICE menu's VOICES
setting; DigiGlide raises it for you and shows "VOICES SET TO 5"). Voices reserved by one track are not available to
the others.

- If the screen shows "VOICES 3 OF 5", other tracks hold the rest. Lower their VOICES in the VOICE menu.
- If it shows "OTHER TRACKS: NO VOICES", every voice is reserved and tracks without a reservation are silent.
- Switching VCNT OFF hands the voices back.

A budget that works: one glide track with 6 voices, one drone with 4, and 6 left for drums and bass.

### Two DigiGlide tracks at once

Two tracks can sound chords at the same time, for example a drone on one and glides on another. A third DigiGlide
track that plays while both are sounding gets a single stock note. A track with HOLD on keeps its place until its
chord is let go.

## Shortcuts

| Keys | What it does |
| --- | --- |
| [FUNC] + push knob E | DigiGlide on / off for the current track |
| [FUNC] + push knob H | HOLD on / off |
| [FUNC] + push knob F | The current track's DigiGlide settings back to the defaults |
| [FUNC] + push knob A | Step to the next DigiDrone sound (shows its name, changes nothing) |
| [FUNC] + push knob B | Load the DigiDrone sound shown onto the current track |
| [FUNC] + push knob G | Status box on / off (for troubleshooting) |
| [STOP] | Lets a held chord go |

## Page 1: CHORD

| Knob | Setting | Values | What it does |
| --- | --- | --- | --- |
| A | TYPE | MAJ, MIN, SUS, DIM, 5TH | The triad. 5TH is root and fifth only, for open drones |
| B | EXT | NONE, 6, 7, MAJ7, 9, 6+9, 7+9, M7+9 | Added notes |
| C | KEY | OFF, C to B, Cm to Bm | With a key set, each root plays the chord that belongs to it in that scale |
| D | VOIC | 0 to 127 | Spacing: 0 a tight cluster, 64 close position, 127 wide |
| E | POS | -64 to +63 | Moves the chord up and down through its inversions |
| F | GLID | 0, 1/16 to 16 bars, 15 s, 30 s, 60 s | Glide time. 0 means no glide: each chord is struck fresh |
| G | PLAY | CHRD, STRM, STRU, HARP | All notes at once, strummed up, strummed down, or a harp run up through three octaves |
| H | HOLD | OFF, ON | The chord stays after the key or trig ends |

With four voices, MAJ with EXT 9 or 6+9 plays root, fifth and ninth with no third. If a chord sounds hollow, try
EXT MAJ7, 7 or 6, or use five voices.

HOLD: a held chord ends when you play the same chord again by hand, press [STOP], mute the track, or turn HOLD off.
A sequenced trig that repeats the chord strikes it again instead.

## Page 2: MOTION

| Setting | Values | What it does |
| --- | --- | --- |
| PATH | SMTH, LIN, EASE, SWEL, BNCE, LATE, SNAP, WOBL, SEMI, SCAL | The curve of the glide. SEMI and SCAL step through semitones or scale notes |
| TIME | TOGR, DIST, BLAG, BLED, LOOS, DRON | How long each voice takes: together, by distance, bass lags, bass leads, loose, or drone (upper voices arrive later) |
| ORDR | TOGR, LOW, HIGH, OUTI, RAND | Which voice starts first |
| STAG | 0 to 8 | The gap between voices for ORDR, in 1/16 steps |
| MOVE | NONE, BLOM, CAS+, CAS-, SPRL, SWOP, SCAT, CONV, FALL, EVOL | A gesture for how the voices travel into the chord. Good as a p-lock on single steps |
| DRFT | 0 to 50 | Slow random detune per voice, in cents |
| VIB | 0 to 50 | Vibrato depth per voice, in cents; each voice has its own slow rate |
| SCRB | 0 to 127 | How far along the glide the voices may go. 127 is all the way. Turn it to play the glide by hand |

## Page 3: SETUP

| Knob | Setting | Values | What it does |
| --- | --- | --- | --- |
| A | VCNT | OFF, 3, 4, 5, 6 | The switch and the voice count |
| B | BASS | OFF, FL-2, FL-1, FOL, SL-2, SL-1, SOLO | The lowest voice as a bass: following the chord or alone, two, one or no octaves under the root |
| C | BPAT | HOLD, PULS, OCT, WALK, R-5, ARP, OFFB, 332 | Bass pattern. HOLD holds the note; the others play a figure on the bass voice in time with the tempo |
| D | BRAT | 1/4, 1/8, 1/16 | The bass pattern's step |
| E | SPD | 0 to 127 | Strum and harp speed. 64 is 13 ms a string, 34 ms a harp note; lower is faster |
| F | BLOM | -64 to +63 | Bloom. Below 0 the upper voices fade out from the top toward the bass alone; above 0 each upper voice breathes slowly in level |
| G | STRK | OFF, 1, 2, 4 | Restrike: with HOLD on, the held chord is struck again every 1, 2 or 4 beats. For plucks and bells that do not sustain |
| H | BAL | -64 to +63 | Bass against chord: up for more bass, down for more chord |

If a held chord or drone keeps striking again every few seconds, STRK is on. Set it to OFF.

## Page 4: TUNE

| Knob | Setting | Values | What it does |
| --- | --- | --- | --- |
| A | TUNE | EQL, PURE | PURE tunes each chord note to an exact ratio above the root (beatless thirds and fifths) |
| B | FAN | 0 to 127 | Spreads the chord voices either side of pitch, up to 20 cents at the outside |

## P-locks

Hold a trig and turn the knob, as for any stock parameter. These can be locked per step: TYPE, EXT, POS, VOIC, GLID,
MOVE, BPAT, BLOM, TUNE, FAN. A lock of VCNT to OFF plays that trig as a normal note.

## The stock arpeggiator

With the stock ARP on, it plays the DigiGlide chord of the key you hold, one note at a time, as ordinary stock notes.
With ARP MODE CHRD the whole chord is struck on every arp step.

## Patterns and kits

DigiGlide's settings are stored with the pattern's kit, per track, and saved with the project.

- From image 34: when you change to a pattern whose track holds the same sound but has no DigiGlide settings yet, the
  settings are carried over and the screen shows "DIGIGLIDE KEPT: TRACK n". From then on they belong to that pattern.
- A track that holds a different sound in the new pattern is left alone. Switch VCNT on there once.
- SAVE KIT, kit copy and paste, the +Drive kit library and exports do not carry DigiGlide's settings.
- Loading a sound onto a track keeps the track's DigiGlide settings.

## DigiDrone sounds

Ten FM TONE drone sounds are built in. **[FUNC] + push knob A** steps through them, **[FUNC] + push knob B** loads the
one shown onto the current track. A load replaces the track's sound (save it first if you want it), sets the chord,
glide and hold settings that suit it, and switches STRK, BPAT, PLAY and BLOM off. Each wants 4 voices.

STILL AIR, SLOW CHAIN, DARK RING, IRON BELLS, BEAT FIELD, GLASS ORGAN, UNDERTOW, WIRE CHOIR, HOLLOW FIFTHS,
STORM GLASS. What each is and what it sets: [DIGIDRONE_SOUNDS_29.md](DIGIDRONE_SOUNDS_29.md).

Play one long trig or one key, then a different root: the chord slides to it. [STOP] lets it go.

## Messages

| Screen | Meaning |
| --- | --- |
| DIGIGLIDE ON (n VOICES) / DIGIGLIDE OFF | The shortcut switched the track |
| VOICES SET TO n | The track's voices were reserved |
| VOICES n OF m | Fewer voices than VCNT asks for; other tracks hold the rest |
| OTHER TRACKS: NO VOICES | All 16 voices are reserved |
| VOICES FREED: TRACK n | A track that is no longer a DigiGlide track gave its voices back |
| DIGIGLIDE KEPT: TRACK n | Settings carried over on a pattern change |
| CHORD MODE ON? | Three notes arrived at once: stock chord mode is on, and the root may be the wrong note. Turn it off |
| DIGIGLIDE: NOT ON MIDI | A drone load was tried on a MIDI track |
| LOADED name | A DigiDrone sound was loaded |

## If something is wrong

- **Single notes instead of chords:** VCNT is OFF on this track in this pattern, the track has fewer than 3 voices
  reserved, or two other DigiGlide tracks are already sounding.
- **Other tracks lose notes:** the unit is out of time. Use fewer DigiGlide voices, or one DigiGlide track instead of
  two. The status box ([FUNC] + push knob G) shows the time used: a block is 667 microseconds, and H is the longest
  one seen.
- **Other tracks are silent:** all voices are reserved. Lower VOICES on the DigiGlide tracks.
- **A chord that will not stop:** [STOP], or turn HOLD off.
- **The unit misbehaves:** send the official OS file with Elektron Transfer. See the recovery section of the
  [README](README.md).

## Known limits

- Tested on one unit. Most checks run in an emulator, not on hardware.
- A heavy pattern can still run out of time when two DigiGlide tracks play many voices.
- A pattern change carries settings only to a track holding the same sound.
- Kit copy, SAVE KIT and exports drop the settings.
- A rare glitch noise after about two minutes of play has been reported and is not explained yet.
