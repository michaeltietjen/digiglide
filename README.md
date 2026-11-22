# DigiGlide

DigiGlide is a modification of the Elektron Digitone II firmware (OS 1.12). A track holds a chord, and on each new
chord its voices glide into the next one along shaped paths. One key or one trig plays a whole chord (type,
extension, key, voicing), and the way the voices travel is set per track: glide time, path, timing, order, Moves
(Bloom, Cascade, Spiral and others), drift, vibrato and scrubbing. It is a port of Brickglide, from
[brickchord](https://github.com/michaeltietjen/brickchord), and it is meant for pads and slow harmonic movement.

It works on FM TONE, WAVETONE, FM DRUM and SWARMER tracks, as four extra pages after the machine's own SYN pages.

**How to use it: [MANUAL.md](MANUAL.md).**

## Warning: recovery

Read this before you install. Installing modified firmware is at your own risk. It can leave the unit unable to
start, and it may affect your warranty. Before you install anything:

- Back up the +Drive (projects and sounds).
- Keep the official OS file at hand.
- Have a DIN MIDI interface (not only USB) at hand.

If the unit starts but misbehaves, send the official OS file with Elektron Transfer over USB, as for any OS
update. If it does not start, hold [FUNC] while powering on, press [TRIG 4] (OS UPGRADE), and send the official OS
file to the MIDI IN socket through the DIN MIDI interface (Transfer's legacy OS upgrade page). That takes about
12 to 15 minutes. The startup menu does not use USB.

Going back to the official OS is the same: send the official file with Transfer.

## Status: beta

Image 35, for OS 1.12 only. It has been played on one unit, the author's; most checks run in an emulator. Expect
faults. Settings and storage formats can still change between builds, so a later build may not read what this one
saved. The known limits are at the end of the [manual](MANUAL.md); [notes/build_log.md](notes/build_log.md) is what
was built, tested and found.

## Install

You need a Digitone II on OS 1.12, a computer with Python 3.10 or newer (nothing else: no compiler, no packages),
and Elektron Transfer.

1. Read the warning above and back up the +Drive.
2. Download `Digitone_II_OS1.12.syx` from Elektron's support pages. DigiGlide does not include it and needs exactly
   that file.
3. Download this repository (Code, Download ZIP) and unzip it.
4. In a terminal, in the unzipped folder, run:

   ```
   python3 install/digiglide_patch.py /path/to/Digitone_II_OS1.12.syx
   ```

   On Windows: `py install\digiglide_patch.py C:\path\to\Digitone_II_OS1.12.syx`

   It checks that your file is the official one, takes one to three minutes, and writes
   `DN2_1.12_DIGIGLIDE_35.syx` beside your file. It writes nothing unless the result is byte for byte the image
   that was tested (SHA-256 `c6c8472f0ce7b7c4950f58e518bf4c38110bfff8fc30be45f333e4e52e90155b`).
5. Send `DN2_1.12_DIGIGLIDE_35.syx` to the unit with Elektron Transfer, as you would an OS update.
6. The unit restarts. After Elektron's intro it shows the DigiGlide splash with "BETA 35".

Then: [MANUAL.md](MANUAL.md).

The image is made from your own OS file on your own computer. Do not share the image: it contains Elektron's
firmware.

## Reporting problems

Use [GitHub Issues](https://github.com/michaeltietjen/digiglide/issues). Please say:

- the build number (the splash shows it),
- what you did and what happened, and whether it happens every time,
- which machine the track uses and the DigiGlide settings on it (VCNT, GLID, HOLD, BPAT),
- if the patcher failed: its last lines and `python3 --version`.

Do not attach firmware files.

## No Elektron firmware here

This repository holds no Elektron firmware and nothing extracted from it. The patch (`install/DigiGlide_35.dgpatch`)
holds DigiGlide's own compiled code and the places it goes; everything of Elektron's comes from your own copy of the
official `Digitone_II_OS1.12.syx`, whose hash is checked. Built images (`*.syx`) are never committed or shared.

DigiGlide is unofficial: not made, endorsed or supported by Elektron.

## Layout

| Path | What |
| --- | --- |
| `model/` | The reference model in Python, and listening demos |
| `mod/core/` | The same engine in C, 32-bit fixed point, with tests against the model |
| `install/` | The patcher and the patch for testers |
| `mod/` | The firmware side: hooks, pages, per-track storage, the build script and its preflight |
| `mod/tests/` | Tests that run a built image in the emulators |
| `port/` | The OS 1.11 to 1.12 address map |
| `tools/` | Read-only USB tools for a unit running DigiGlide |
| `notes/`, `GLIDE_SPEC.md` | Build log and design |

Installing needs only Python (see Install). Building from source needs the m68k cross compiler and the projects
listed under Credits.

## Credits

- **Brickglide** (brickchord, MIT): the glide engine DigiGlide ports.
- **dnfw** by angellinares (AGPL-3.0-or-later): firmware container (included in `install/vendor/`), loader, parameter table relocation, safety
  check, and the USB probe DigiGlide's read-only probe is derived from.
- **digihealth** and **digiemu** by irpina (GPL-2.0-or-later): the origin of the probe, and the emulator.
- **digikit** by m-dwyer (GPL-2.0-or-later): the emulator tooling the tests run in.
- **digitone-2-modding-skill** by complex-ping (MIT): build helpers and the emulator harness.
- **dn2-cfw (Digiwerk)** by naturarum (GPL-2.0-or-later): notes on the kit record and the parameter table.

Which files derive from which project is in [NOTICE](NOTICE).

## Licence

AGPL-3.0-or-later, see [LICENSE](LICENSE). Elektron firmware is not included and is not covered by it.
