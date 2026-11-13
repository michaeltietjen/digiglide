# DigiGlide

DigiGlide is a modification of the Elektron Digitone II firmware (OS 1.12). A track holds a chord, and on each new
chord its voices glide into the next one along shaped paths. One key or one trig plays a whole chord (type,
extension, key, voicing), and the way the voices travel is set per track: glide time, path, timing, order, Moves
(Bloom, Cascade, Spiral and others), drift, vibrato and scrubbing. It is a port of Brickglide, from
[brickchord](https://github.com/michaeltietjen/brickchord), and it is meant for pads and slow harmonic movement.

It works on FM TONE, WAVETONE, FM DRUM and SWARMER tracks, as three extra pages after the machine's own SYN pages.

## Status: in development

This is work in progress, used on one unit, the author's. Features and storage formats change between builds.
[GLIDE_SPEC.md](GLIDE_SPEC.md) is the design, [notes/build_log.md](notes/build_log.md) is what was built, tested and
found, including the known limits of the current build.

## No Elektron firmware here

This repository holds no Elektron firmware, nothing extracted from it and no file generated from it. A DigiGlide
image is built on your own computer from your own copy of the official `Digitone_II_OS1.12.syx`; the build checks
that file's hash and refuses any other. Built images (`*.syx`) are never committed or shared.

DigiGlide is unofficial: not made, endorsed or supported by Elektron.

## Warning: recovery

Installing modified firmware is at your own risk. It can leave the unit unable to start, and it may affect your
warranty. Before you install anything:

- Back up the +Drive (projects and sounds).
- Keep the official OS file at hand.
- Have a DIN MIDI interface (not only USB) at hand.

If the unit starts but misbehaves, send the official OS file with Elektron Transfer over USB, as for any OS
update. If it does not start, hold [FUNC] while powering on, press [TRIG 4] (OS UPGRADE), and send the official OS
file to the MIDI IN socket through the DIN MIDI interface (Transfer's legacy OS upgrade page). That takes about
12 to 15 minutes. The startup menu does not use USB.

## Layout

| Path | What |
| --- | --- |
| `model/` | The reference model in Python, and listening demos |
| `mod/core/` | The same engine in C, 32-bit fixed point, with tests against the model |
| `mod/` | The firmware side: hooks, pages, per-track storage, the build script and its preflight |
| `mod/tests/` | Tests that run a built image in the emulators |
| `port/` | The OS 1.11 to 1.12 address map |
| `tools/` | Read-only USB tools for a unit running DigiGlide |
| `notes/`, `GLIDE_SPEC.md` | Build log and design |

There is no one-step installer yet. Building needs the m68k cross compiler and the projects listed under Credits.

## Credits

- **Brickglide** (brickchord, MIT): the glide engine DigiGlide ports.
- **dnfw** by angellinares (AGPL-3.0-or-later): firmware container, loader, parameter table relocation, safety
  check, and the USB probe DigiGlide's read-only probe is derived from.
- **digihealth** and **digiemu** by irpina (GPL-2.0-or-later): the origin of the probe, and the emulator.
- **digikit** by m-dwyer (GPL-2.0-or-later): the emulator tooling the tests run in.
- **digitone-2-modding-skill** by complex-ping (MIT): build helpers and the emulator harness.
- **dn2-cfw (Digiwerk)** by naturarum (GPL-2.0-or-later): notes on the kit record and the parameter table.

Which files derive from which project is in [NOTICE](NOTICE).

## Licence

AGPL-3.0-or-later, see [LICENSE](LICENSE). Elektron firmware is not included and is not covered by it.
